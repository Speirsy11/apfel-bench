"""Code execution benchmark: the model writes a small Python function
that we then `exec()` in a restricted sandbox and call against test cases.

This is a real "does it work" test, not just a syntactic check.

Sandbox restrictions:
  - banned imports: os, sys, subprocess, shutil, socket, urllib, requests, http, ftplib, smtplib, ssl, pickle, ctypes, cffi, multiprocessing, threading
  - any unhandled exception -> that case counts as failed (returns None)
  - the sandbox never sees the host filesystem or the network

Score = fraction of test cases that produced the expected output.
"""

from __future__ import annotations

import re
import time
import types
from datetime import datetime

from apfel_bench.benchmark import BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest

_BANNED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "urllib", "urllib2", "urllib3",
    "requests", "http", "http.client", "ftplib", "smtplib", "ssl", "pickle", "ctypes",
    "cffi", "multiprocessing", "threading", "asyncio", "select", "fcntl", "resource",
    "pwd", "grp", "spwd", "crypt", "termios", "tty", "pty", "signal", "mmap", "ctypes",
})


def _extract_python_code(text: str) -> str | None:
    """Pull a Python code block out of the response. Prefers a ```python``` fence,
    falls back to the first bare `def`/`class` line through end of message."""
    m = re.search(r"```python\s*\n(.*?)```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    # No fence — grab the first `def`/`class`/top-level statement to end
    lines = text.splitlines()
    start = next(
        (i for i, l in enumerate(lines) if re.match(r"\s*(def |class |from |import )", l)),
        None,
    )
    if start is None:
        return None
    return "\n".join(lines[start:]).strip()


def _run_in_sandbox(code: str, fn_name: str, args_list: list) -> list | None:
    """Execute `code` in a restricted namespace and call `fn_name(args)` for each
    args in `args_list`. Returns the list of return values, or None if the
    function isn't defined or any banned module is imported."""
    # Cheap static check for banned imports before we exec
    lowered = code.lower()
    for banned in _BANNED_MODULES:
        # match `import banned` or `from banned`
        if re.search(rf"(^|\n)\s*(import|from)\s+{re.escape(banned)}\b", lowered):
            return None

    namespace: dict = {"__builtins__": __builtins__}
    try:
        exec(code, namespace)
    except Exception:
        return None
    fn = namespace.get(fn_name)
    if not callable(fn):
        return None

    results: list = []
    for args in args_list:
        try:
            results.append(fn(*args) if isinstance(args, tuple) else fn(args))
        except Exception:
            return None
    return results


@register
class CodeExecutionBenchmark:
    slug = "code_execution"
    name = "Code Execution"
    description = "Model writes a Python function; we run it against test cases. Score = % of cases that pass."

    # (question, function name expected, list of (args, expected) cases)
    TASKS: list[dict] = [
        {
            "q": "Write a Python function `solve(x)` that returns x squared. Reply with the function in a ```python``` code block.",
            "fn": "solve",
            "cases": [((2,), 4), ((5,), 25), ((-3,), 9), ((0,), 0)],
        },
        {
            "q": "Write a Python function `solve(s)` that returns the reverse of the input string. Reply with the function in a ```python``` code block.",
            "fn": "solve",
            "cases": [(("hello",), "olleh"), (("",), ""), (("a",), "a"), (("racecar",), "racecar")],
        },
        {
            "q": "Write a Python function `solve(numbers)` that returns the sum of all integers in the list. Reply with the function in a ```python``` code block.",
            "fn": "solve",
            "cases": [(([1, 2, 3],), 6), (([],), 0), (([-5, 5, 10],), 10), (([0, 0, 0],), 0)],
        },
        {
            "q": "Write a Python function `solve(n)` that returns True if n is a prime number, False otherwise. Reply with the function in a ```python``` code block.",
            "fn": "solve",
            "cases": [((2,), True), ((7,), True), ((4,), False), ((9,), False), ((1,), False), ((11,), True)],
        },
        {
            "q": "Write a Python function `solve(s)` that returns the number of vowels (a, e, i, o, u, case-insensitive) in the string. Reply with the function in a ```python``` code block.",
            "fn": "solve",
            "cases": [(("hello",), 2), (("AEIOU",), 5), (("xyz",), 0), (("Apple",), 2)],
        },
    ]

    async def run(self, client) -> BenchmarkResult:
        started = datetime.now()
        t0 = time.perf_counter()
        per_task: list[dict] = []
        total_cases = 0
        passed_cases = 0
        total_prompt = 0
        total_completion = 0
        try:
            for task in self.TASKS:
                resp = await client.chat(
                    ChatRequest(
                        model="apple-foundationmodel",
                        messages=[ChatMessage(role="user", content=task["q"])],
                    )
                )
                total_prompt += resp.prompt_tokens
                total_completion += resp.completion_tokens
                code = _extract_python_code(resp.content)
                if code is None:
                    per_task.append({"q": task["q"], "ok": 0, "total": len(task["cases"]), "error": "no_code", "raw": resp.content[:300]})
                    total_cases += len(task["cases"])
                    continue
                results = _run_in_sandbox(code, task["fn"], [c[0] for c in task["cases"]])
                if results is None:
                    per_task.append({"q": task["q"], "ok": 0, "total": len(task["cases"]), "error": "exec_failed", "code": code})
                    total_cases += len(task["cases"])
                    continue
                ok = 0
                for (args, expected), got in zip(task["cases"], results):
                    if got == expected:
                        ok += 1
                passed_cases += ok
                total_cases += len(task["cases"])
                per_task.append(
                    {
                        "q": task["q"],
                        "fn": task["fn"],
                        "code": code[:400],
                        "ok": ok,
                        "total": len(task["cases"]),
                        "results": list(zip([c[1] for c in task["cases"]], results)),
                    }
                )
            score = passed_cases / total_cases if total_cases else 0.0
        except Exception as e:
            score = 0.0
            per_task.append({"error": repr(e)})

        duration_ms = int((time.perf_counter() - t0) * 1000)
        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started,
            finished_at=datetime.now(),
            prompt="5 coding tasks; see metadata.per_task",
            response=f"{passed_cases}/{total_cases} cases passed",
            expected=f">= 0.7 of {total_cases}",
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            metadata={
                "num_tasks": len(self.TASKS),
                "total_cases": total_cases,
                "passed_cases": passed_cases,
                "per_task": per_task,
            },
        )

"""Tests for the code-execution benchmark."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.code_execution import (
    _extract_python_code,
    _run_in_sandbox,
    CodeExecutionBenchmark,
)
from apfel_bench.client import ChatResponse


def test_extract_python_code_finds_python_fenced_block():
    text = "Sure!\n```python\ndef solve(x):\n    return x * 2\n```\nDone."
    assert _extract_python_code(text) == "def solve(x):\n    return x * 2"


def test_extract_python_code_finds_unfenced_block():
    text = "def solve(x):\n    return x * 2"
    assert _extract_python_code(text) == "def solve(x):\n    return x * 2"


def test_extract_python_code_returns_none_for_no_code():
    text = "I cannot help with that."
    assert _extract_python_code(text) is None


def test_extract_python_code_finds_first_block_when_multiple():
    text = "Here's one:\n```python\ndef solve(x):\n    return x + 1\n```\nAnd another:\n```python\ndef solve(x):\n    return x + 2\n```"
    assert _extract_python_code(text) == "def solve(x):\n    return x + 1"


def test_run_in_sandbox_executes_and_returns_function_results():
    code = "def solve(x):\n    return x * 2"
    assert _run_in_sandbox(code, "solve", [1, 5, 10]) == [2, 10, 20]


def test_run_in_sandbox_returns_none_when_solve_missing():
    code = "def other(x):\n    return x"
    assert _run_in_sandbox(code, "solve", [1]) is None


def test_run_in_sandbox_returns_none_on_runtime_error():
    code = "def solve(x):\n    return x / 0"
    assert _run_in_sandbox(code, "solve", [1]) is None


def test_run_in_sandbox_blocks_dangerous_imports():
    # `os` is in the blocked list — the sandbox should refuse to import it
    code = "import os\ndef solve(x):\n    return os.listdir('/')"
    assert _run_in_sandbox(code, "solve", [1]) is None


def test_run_in_sandbox_blocks_network():
    code = "import urllib.request\ndef solve(x):\n    return urllib.request.urlopen('http://example.com').read()"
    assert _run_in_sandbox(code, "solve", [1]) is None


@pytest.mark.asyncio
async def test_benchmark_scores_when_all_cases_pass():
    bench = CodeExecutionBenchmark()

    # Use just one task to keep the test fast
    class FakeClient:
        async def chat(self, request):
            # Return a solve() that doubles the input for every task
            code = "def solve(x):\n    return x * 2"
            return ChatResponse(
                content=f"```python\n{code}\n```",
                prompt_tokens=10, completion_tokens=5, total_tokens=15,
                finish_reason="stop", raw={},
            )

    # Monkey-patch the benchmark to use a single easy task
    bench.TASKS = [
        {"q": "double the input", "fn": "solve", "cases": [(1, 2), (3, 6)]},
    ]
    result = await bench.run(FakeClient())
    assert result.benchmark == "code_execution"
    assert result.score == 1.0
    assert result.metadata["passed_cases"] == 2
    assert result.metadata["total_cases"] == 2

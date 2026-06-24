"""Multi-constraint benchmark: short creative-writing tasks with several
constraints that must ALL be satisfied (word count, must include, must
avoid, must end with). Score is the fraction of constraints satisfied
across all tasks — a model that hits 3 of 4 on every task still only
gets 0.75.
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from apfel_bench.benchmark import BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _check_constraints(text: str, item: dict) -> dict[str, bool]:
    out: dict[str, bool] = {}
    if item.get("word_count") is not None:
        lo, hi = item["word_count"]
        n = _word_count(text)
        out["word_count"] = lo <= n <= hi
    if item.get("must_include"):
        lower = text.lower()
        out["must_include"] = all(s.lower() in lower for s in item["must_include"])
    if item.get("must_avoid"):
        lower = text.lower()
        out["must_avoid"] = all(s.lower() not in lower for s in item["must_avoid"])
    if item.get("must_end_with"):
        ending = item["must_end_with"].lower()
        out["must_end_with"] = text.strip().lower().endswith(ending)
    return out


@register
class MultiConstraintBenchmark:
    slug = "multi_constraint"
    name = "Multi-Constraint"
    description = "5 short creative tasks; each has 3-4 constraints. Score = fraction of constraints satisfied."

    TASKS: list[dict] = [
        {
            "q": "Write a story about a wizard. The story must: (a) be exactly 50 words long, (b) mention a cat, (c) NOT use the word 'magic', (d) end with the word 'wizard'.",
            "word_count": (50, 50),
            "must_include": ["cat"],
            "must_avoid": ["magic"],
            "must_end_with": "wizard",
        },
        {
            "q": "Write a haiku about a thunderstorm. A haiku is 3 lines with a 5-7-5 syllable structure. The haiku must mention 'rain'.",
            "word_count": None,  # We approximate with line count + has rain
            "must_include": ["rain"],
            "must_avoid": [],
            "must_end_with": None,
        },
        {
            "q": "Write exactly 3 sentences about a robot learning to cook. The word 'robot' must appear in the first sentence. Do not use the letter 'e' anywhere.",
            "word_count": None,
            "must_include": ["robot"],
            "must_avoid": ["e"],
            "must_end_with": None,
        },
        {
            "q": "Write a story of between 30 and 40 words (inclusive) about a lighthouse keeper. The story must mention 'sea', 'lamp', and end with the word 'keeper'.",
            "word_count": (30, 40),
            "must_include": ["sea", "lamp"],
            "must_avoid": [],
            "must_end_with": "keeper",
        },
        {
            "q": "Write a single sentence of between 20 and 25 words about a secret garden. The sentence must contain the word 'key' and must NOT contain the word 'door'.",
            "word_count": (20, 25),
            "must_include": ["key"],
            "must_avoid": ["door"],
            "must_end_with": None,
        },
    ]

    async def run(self, client) -> BenchmarkResult:
        started = datetime.now()
        t0 = time.perf_counter()
        per_task: list[dict] = []
        total_constraints = 0
        passed_constraints = 0
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
                detail = _check_constraints(resp.content, task)
                # Special-case the haiku: relax word_count to "3 lines" if specified as None
                if task.get("word_count") is None and "haiku" in task["q"].lower():
                    lines = [l for l in resp.content.splitlines() if l.strip()]
                    detail["haiku_3_lines"] = len(lines) == 3
                passed = sum(1 for v in detail.values() if v)
                total = len(detail)
                total_constraints += total
                passed_constraints += passed
                per_task.append(
                    {
                        "q": task["q"][:120] + ("…" if len(task["q"]) > 120 else ""),
                        "detail": detail,
                        "passed": passed,
                        "total": total,
                        "raw": resp.content,
                    }
                )
            score = passed_constraints / total_constraints if total_constraints else 0.0
        except Exception as e:
            score = 0.0
            per_task.append({"error": repr(e)})

        duration_ms = int((time.perf_counter() - t0) * 1000)
        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started,
            finished_at=datetime.now(),
            prompt="5 short creative tasks with multiple constraints",
            response=f"{passed_constraints}/{total_constraints} constraints satisfied",
            expected=f">= 0.7 of {total_constraints}",
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            metadata={
                "num_tasks": len(self.TASKS),
                "total_constraints": total_constraints,
                "passed_constraints": passed_constraints,
                "per_task": per_task,
            },
        )

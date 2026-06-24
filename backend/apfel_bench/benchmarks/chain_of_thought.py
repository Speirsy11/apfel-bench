"""Chain-of-thought benchmark: multi-step word problems with a single
numeric answer. The model is asked to "think step by step" then emit
`Answer: <number>`. Score is exact numeric match (within 0.01).

The problems are GSM8K-style (grade-school level) but hand-curated to
require two or more non-trivial steps. A 3B on-device model typically
gets < 50% on this set.
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from apfel_bench.benchmark import BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


def _extract_final_number(text: str) -> float | None:
    """Pull the model's numeric answer out of the response.

    Preference order:
      1. `Answer: <number>` or `Answer is <number>` line
      2. `= <number>` at the end of a line
      3. The last decimal/integer in the text
    """
    t = text.strip()
    m = re.search(r"(?im)^\s*answer\s*(?:is|:)?\s*\(?\s*(-?\d+(?:\.\d+)?)\s*\)?", t)
    if m:
        return float(m.group(1))
    m = re.findall(r"=\s*(-?\d+(?:\.\d+)?)", t)
    if m:
        return float(m[-1])
    nums = re.findall(r"-?\d+(?:\.\d+)?", t)
    if nums:
        return float(nums[-1])
    return None


@register
class ChainOfThoughtBenchmark:
    slug = "chain_of_thought"
    name = "Chain of Thought"
    description = "8 multi-step word problems. Score = exact numeric match."

    PROBLEMS: list[dict] = [
        {
            "q": "Janet has 16 apples. She gives 1/4 of them to her brother and then buys 6 more. How many apples does she have now?",
            "answer": 18.0,  # 16 - 4 + 6 = 18
        },
        {
            "q": "A train leaves at 9:15 AM and arrives at 1:45 PM. How many minutes was the journey?",
            "answer": 270.0,  # 4h30m = 270 min
        },
        {
            "q": "If 3 workers can paint 9 fences in 2 hours, how many fences can 5 workers paint in 4 hours at the same rate?",
            "answer": 30.0,  # 9/(3*2) = 1.5/hr per worker, *5*4 = 30
        },
        {
            "q": "A book costs $12.40. There is a 15% discount, then a $1.00 sales tax on the discounted price. What is the final cost in dollars?",
            "answer": 11.54,  # 12.40 * 0.85 = 10.54, + 1.00 tax = 11.54
        },
        {
            "q": "A rectangular garden is 12 meters long and 8 meters wide. A 1-meter-wide path is built around the outside of the garden. What is the area, in square meters, of the path alone?",
            "answer": 44.0,  # outer = 14*10=140, inner = 12*8=96, path = 44
        },
        {
            "q": "Tom is twice as old as his son. In 12 years, Tom will be 1.5 times as old as his son. How old is Tom now?",
            "answer": 24.0,  # T=2S, T+12=1.5(S+12) => 2S+12=1.5S+18 => 0.5S=6 => S=12, T=24
        },
        {
            "q": "A snail climbs 3 feet up a well each day and slips back 1 foot each night. If the well is 11 feet deep, how many days does it take the snail to get out?",
            "answer": 5.0,  # Day 1: 3-1=2, Day 2: 5-1=4, Day 3: 7-1=6, Day 4: 9-1=8, Day 5: 11 (out before slipping)
        },
        {
            "q": "A store sells notebooks for $4 each and pens for $2 each. If Sarah buys 3 notebooks and 5 pens, and pays with a $50 bill, how much change does she receive in dollars?",
            "answer": 28.0,  # 3*4 + 5*2 = 12+10 = 22, 50-22 = 28
        },
    ]

    def _format(self, item: dict) -> str:
        return (
            f"Problem: {item['q']}\n\n"
            "Think step by step. When you reach your final answer, write it on its own line as:\n"
            "Answer: <number>"
        )

    async def run(self, client) -> BenchmarkResult:
        started = datetime.now()
        t0 = time.perf_counter()
        per_q: list[dict] = []
        correct = 0
        total_prompt = 0
        total_completion = 0
        try:
            for item in self.PROBLEMS:
                prompt = self._format(item)
                resp = await client.chat(
                    ChatRequest(
                        model="apple-foundationmodel",
                        messages=[ChatMessage(role="user", content=prompt)],
                    )
                )
                got = _extract_final_number(resp.content)
                exp = item["answer"]
                ok = got is not None and abs(got - exp) < 0.01
                if ok:
                    correct += 1
                total_prompt += resp.prompt_tokens
                total_completion += resp.completion_tokens
                per_q.append(
                    {
                        "q": item["q"],
                        "expected": exp,
                        "got": got,
                        "ok": ok,
                        "raw": resp.content[:600],
                    }
                )
            score = correct / len(self.PROBLEMS)
        except Exception as e:
            score = 0.0
            per_q.append({"error": repr(e)})

        duration_ms = int((time.perf_counter() - t0) * 1000)
        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started,
            finished_at=datetime.now(),
            prompt="8 multi-step word problems; think step by step; emit Answer: <number>",
            response=f"{correct}/{len(self.PROBLEMS)} correct",
            expected=f">= 0.6 of {len(self.PROBLEMS)}",
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            metadata={"num_questions": len(self.PROBLEMS), "correct": correct, "per_question": per_q},
        )

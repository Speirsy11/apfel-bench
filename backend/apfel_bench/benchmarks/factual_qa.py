"""Factual QA: small bank of multiple-choice questions with a single known
correct letter. The model gets the question + the 4 options and is asked
to reply with one letter. Score is the fraction correct.

Bank covers a range of difficulties: easy general knowledge, harder
specific recall, and a few to catch overconfident guessing.
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from apfel_bench.benchmark import BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


def _normalize_letter(text: str) -> str | None:
    """Pull a single A-D letter out of the response. Returns None if absent."""
    t = text.strip()
    m = re.search(r"(?im)^\s*answer\s*[:=]?\s*\(?([A-D])\)?\b", t)
    if m:
        return m.group(1).upper()
    m = re.search(r"\b([A-D])\b", t.upper())
    if m:
        return m.group(1)
    return None


@register
class FactualQABenchmark:
    slug = "factual_qa"
    name = "Factual QA"
    description = "10 multiple-choice questions; model picks A/B/C/D. Score = fraction correct."

    QUESTIONS: list[dict] = [
        # Easy
        {"q": "What is the capital of Australia?", "options": ["Sydney", "Melbourne", "Canberra", "Perth"], "answer": "C"},
        {"q": "Which planet has the most moons (as of 2024)?", "options": ["Jupiter", "Saturn", "Uranus", "Neptune"], "answer": "B"},
        {"q": "Who painted 'The Starry Night'?", "options": ["Monet", "Van Gogh", "Cezanne", "Renoir"], "answer": "B"},
        # Medium
        {"q": "In what year did the Berlin Wall fall?", "options": ["1987", "1989", "1991", "1993"], "answer": "B"},
        {"q": "What is the chemical symbol for tungsten?", "options": ["Tu", "Tg", "W", "Tn"], "answer": "C"},
        {"q": "Which element has the highest melting point?", "options": ["Iron", "Platinum", "Tungsten", "Carbon"], "answer": "C"},
        # Hard / specific
        {"q": "Who wrote the novel 'The Master and Margarita'?", "options": ["Tolstoy", "Dostoyevsky", "Bulgakov", "Nabokov"], "answer": "C"},
        {"q": "What is the speed of light in a vacuum, in m/s, to 3 sig figs?", "options": ["3.00e8", "3.00e6", "2.98e8", "3.14e8"], "answer": "A"},
        {"q": "Which programming language was first released in 1995?", "options": ["Python", "Ruby", "Java", "All of the above"], "answer": "D"},
        {"q": "How many bones are in the adult human body?", "options": ["198", "206", "214", "232"], "answer": "B"},
    ]

    def _format(self, item: dict) -> tuple[str, str]:
        letters = ["A", "B", "C", "D"]
        opts = "\n".join(f"({l}) {opt}" for l, opt in zip(letters, item["options"]))
        prompt = (
            f"{item['q']}\n\n{opts}\n\n"
            "Reply with only the letter of the correct answer (A, B, C, or D)."
        )
        return prompt, item["answer"]

    async def run(self, client) -> BenchmarkResult:
        started = datetime.now()
        t0 = time.perf_counter()
        per_q: list[dict] = []
        correct = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        try:
            for item in self.QUESTIONS:
                prompt, expected = self._format(item)
                resp = await client.chat(
                    ChatRequest(
                        model="apple-foundationmodel",
                        messages=[ChatMessage(role="user", content=prompt)],
                    )
                )
                got = _normalize_letter(resp.content)
                ok = got == expected
                if ok:
                    correct += 1
                total_prompt_tokens += resp.prompt_tokens
                total_completion_tokens += resp.completion_tokens
                per_q.append(
                    {
                        "q": item["q"],
                        "options": item["options"],
                        "expected": expected,
                        "got": got,
                        "ok": ok,
                        "raw": resp.content,
                    }
                )
            score = correct / len(self.QUESTIONS)
        except Exception as e:
            score = 0.0
            per_q.append({"error": repr(e)})

        duration_ms = int((time.perf_counter() - t0) * 1000)
        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started,
            finished_at=datetime.now(),
            prompt="10 multiple-choice questions, see metadata.per_question",
            response=f"{correct}/{len(self.QUESTIONS)} correct",
            expected=f">= 0.7 of {len(self.QUESTIONS)}",
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            metadata={
                "num_questions": len(self.QUESTIONS),
                "correct": correct,
                "per_question": per_q,
            },
        )

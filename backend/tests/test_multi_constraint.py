"""Tests for the multi-constraint story-writing benchmark."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.multi_constraint import (
    _check_constraints,
    _word_count,
    MultiConstraintBenchmark,
)


def test_word_count_basic():
    assert _word_count("hello world") == 2
    assert _word_count("  one, two; three.  ") == 3
    assert _word_count("") == 0


def test_check_constraints_word_count_passes():
    item = {
        "word_count": (5, 5),  # exact 5
        "must_include": [],
        "must_avoid": [],
        "must_end_with": None,
    }
    text = "one two three four five"
    detail = _check_constraints(text, item)
    assert detail["word_count"]


def test_check_constraints_handles_word_count_none():
    # word_count key present but value is None → skip the check, don't crash
    item = {"word_count": None, "must_include": ["rain"], "must_avoid": [], "must_end_with": None}
    detail = _check_constraints("rain falls", item)
    assert "word_count" not in detail
    assert detail["must_include"]


def test_check_constraints_word_count_off_by_one_fails():
    item = {"word_count": (5, 5), "must_include": [], "must_avoid": [], "must_end_with": None}
    detail = _check_constraints("one two three four", item)  # 4 words
    assert not detail["word_count"]


def test_check_constraints_must_include_all_present():
    item = {"must_include": ["cat", "moon"], "must_avoid": [], "must_end_with": None}
    assert _check_constraints("the cat saw the moon", item)["must_include"]


def test_check_constraints_must_include_one_missing():
    item = {"must_include": ["cat", "moon"], "must_avoid": [], "must_end_with": None}
    assert not _check_constraints("the cat slept", item)["must_include"]


def test_check_constraints_must_avoid_clean():
    item = {"must_include": [], "must_avoid": ["magic", "spell"], "must_end_with": None}
    assert _check_constraints("just a normal story", item)["must_avoid"]


def test_check_constraints_must_avoid_violated():
    item = {"must_include": [], "must_avoid": ["magic"], "must_end_with": None}
    assert not _check_constraints("it was magic", item)["must_avoid"]


def test_check_constraints_must_end_with_match():
    item = {"must_include": [], "must_avoid": [], "must_end_with": "wizard"}
    assert _check_constraints("a tale about a wizard", item)["must_end_with"]


def test_check_constraints_must_end_with_mismatch():
    item = {"must_include": [], "must_avoid": [], "must_end_with": "wizard"}
    assert not _check_constraints("a tale about a knight", item)["must_end_with"]


def test_check_constraints_combined_score():
    item = {
        "word_count": (10, 10),
        "must_include": ["cat"],
        "must_avoid": ["magic"],
        "must_end_with": "wizard",
    }
    text = "A tale of ten words about a cat and a wizard"  # 12 words actually
    # fails word count, passes include, passes avoid, fails end_with
    detail = _check_constraints(text, item)
    assert not detail["word_count"]
    assert detail["must_include"]
    assert detail["must_avoid"]
    assert detail["must_end_with"]


def test_benchmark_tasks_are_well_formed():
    bench = MultiConstraintBenchmark()
    for t in bench.TASKS:
        assert t["must_include"] or t["must_avoid"] or t["must_end_with"] or t["word_count"]


@pytest.mark.asyncio
async def test_benchmark_scores_full_credit():
    class FakeClient:
        async def chat(self, request):
            # Construct a response that meets every constraint perfectly.
            return _PerfectResponse()

    # Monkey-patch the benchmark to have one trivial task
    bench = MultiConstraintBenchmark()
    bench.TASKS = [
        {"q": "test", "word_count": (5, 5), "must_include": ["cat"], "must_avoid": ["dog"], "must_end_with": "wizard"},
    ]

    class _PerfectResponse:
        prompt_tokens = 5
        completion_tokens = 5
        @property
        def content(self):
            return "a cat and the wizard"

    from apfel_bench.client import ChatResponse

    class PerfectClient:
        async def chat(self, request):
            return ChatResponse(
                content="a cat and the wizard",
                prompt_tokens=5, completion_tokens=5, total_tokens=10,
                finish_reason="stop", raw={},
            )

    result = await bench.run(PerfectClient())
    assert result.score == 1.0
    assert result.metadata["passed_constraints"] == result.metadata["total_constraints"]

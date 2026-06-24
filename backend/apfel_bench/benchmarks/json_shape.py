"""JSON-shape benchmark.

Forces the model to reply with JSON (via `response_format: json_object`)
and validates the parsed object against a simple `{field: type}` schema.
Score is 1.0 if every schema field is present with the right type,
else 0.0. JSON wrapped in a single code fence is also accepted.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any

from apfel_bench.benchmark import Benchmark, BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_FIRST_JSON_RE = re.compile(r"(\{.*\})", re.DOTALL)


def _extract_json(text: str) -> str | None:
    """Return the first JSON object found in text, unwrapping a code fence if present."""
    m = _CODE_FENCE_RE.search(text)
    if m:
        return m.group(1)
    m = _FIRST_JSON_RE.search(text)
    if m:
        return m.group(1)
    return None


def _check_schema(obj: Any, schema: dict[str, type]) -> str | None:
    if not isinstance(obj, dict):
        return f"top-level is {type(obj).__name__}, expected object"
    for key, typ in schema.items():
        if key not in obj:
            return f"missing field {key!r}"
        if not isinstance(obj[key], typ):
            return f"field {key!r} is {type(obj[key]).__name__}, expected {typ.__name__}"
    return None


@register
class JsonShapeBenchmark:
    slug = "json_shape"
    name = "JSON shape"
    description = "Forces a JSON reply and validates it against a simple {field: type} schema."

    DEFAULT_PROMPT = "Reply with a JSON object with two fields: x (integer) and y (string). Nothing else."
    DEFAULT_SCHEMA: dict[str, type] = {"x": int, "y": str}

    def __init__(
        self,
        prompt: str = DEFAULT_PROMPT,
        schema: dict[str, type] | None = None,
    ):
        self.prompt = prompt
        self.schema = schema or self.DEFAULT_SCHEMA

    async def run(self, client) -> BenchmarkResult:
        started_at = datetime.now()
        t0 = time.perf_counter()

        request = ChatRequest(
            model="apple-foundationmodel",
            messages=[ChatMessage(role="user", content=self.prompt)],
            metadata={"response_format": {"type": "json_object"}},
        )
        response = await client.chat(request)
        finished_at = datetime.now()
        duration_ms = int((time.perf_counter() - t0) * 1000)

        parsed: Any = None
        score = 0.0
        error: str | None = None

        candidate = _extract_json(response.content)
        if candidate is None:
            error = "no JSON object found in response"
        else:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as e:
                error = f"json decode error: {e.msg}"
            else:
                schema_error = _check_schema(parsed, self.schema)
                if schema_error:
                    error = schema_error
                else:
                    score = 1.0

        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started_at,
            finished_at=finished_at,
            prompt=self.prompt,
            response=response.content,
            expected=str(self.schema),
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            metadata={
                "parsed": parsed,
                "schema": {k: t.__name__ for k, t in self.schema.items()},
                "error": error,
            },
        )

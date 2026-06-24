"""Built-in benchmarks. Each submodule's @register runs on import.

Add a new benchmark by dropping a `my_bench.py` next to `smoke.py` and
appending its import here.
"""

from apfel_bench.benchmarks import (  # noqa: F401
    smoke,
    latency,
    json_shape,
    instruction_following,
    factual_qa,
    chain_of_thought,
    code_execution,
    multi_constraint,
    adversarial,
    hallucination,
)

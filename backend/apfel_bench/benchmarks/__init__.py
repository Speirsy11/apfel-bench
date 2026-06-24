"""Built-in benchmarks. Each submodule's @register runs on import.

Add a new benchmark by dropping a `my_bench.py` next to `smoke.py` and
appending its import here.
"""

from apfel_bench.benchmarks import smoke  # noqa: F401

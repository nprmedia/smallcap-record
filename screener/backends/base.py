"""Backend contract: what any data source must deliver to the pipeline.

fetch(as_of) returns one row per candidate security with exactly the columns
in schema.BACKEND_COLUMNS. Values a source cannot supply are null — the
pipeline treats null as "unknown", never fabricates, and universe filters
exclude names whose filter inputs are unknown.

benchmark_level(as_of) returns the dividend-adjusted IJR close (the S&P
SmallCap 600 proxy pinned in config `data.benchmark_series`).

All data must be as-known-at-as_of: fundamentals filed on or before as_of,
prices through as_of. Restatements must never leak backward.
"""
from __future__ import annotations

import abc
import datetime as dt

import pandas as pd

from ..schema import BACKEND_COLUMNS


class Backend(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def fetch(self, as_of: dt.date) -> pd.DataFrame: ...

    @abc.abstractmethod
    def benchmark_level(self, as_of: dt.date) -> float | None: ...

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in BACKEND_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{self.name} backend violates contract, missing: {missing}")
        return df[BACKEND_COLUMNS]

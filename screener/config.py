"""Configuration loading.

config/v0.yaml is the pre-registered source of truth for every methodology
parameter — code reads from it, never hardcodes (CLAUDE.md / METHODOLOGY.md §9).
config/backends.yaml is operational plumbing (endpoints, sample tickers) with
no methodology content; it may change freely.

YAML 1.1 quirk: bare scientific notation like `300e6` parses as a *string*
under PyYAML, so every numeric parameter must be read through num().
"""
from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
V0_PATH = ROOT / "config" / "v0.yaml"
BACKENDS_PATH = ROOT / "config" / "backends.yaml"


def load_v0(path: pathlib.Path | None = None) -> dict:
    with open(path or V0_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_backends(path: pathlib.Path | None = None) -> dict:
    with open(path or BACKENDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def num(value) -> float:
    """Coerce a config value to float ('300e6' -> 300000000.0)."""
    return float(value)

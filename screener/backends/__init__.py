"""Interchangeable data backends. Both satisfy the contract in schema.BACKEND_COLUMNS."""
from __future__ import annotations


def get_backend(name: str, v0: dict, backends_cfg: dict):
    if name == "free":
        from .free.backend import FreeBackend
        return FreeBackend(v0, backends_cfg)
    if name == "sharadar":
        from .sharadar import SharadarBackend
        return SharadarBackend(v0, backends_cfg)
    raise ValueError(f"unknown backend: {name!r} (expected 'free' or 'sharadar')")

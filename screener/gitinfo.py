"""config_version = the git SHA of the ruleset that produced the row (METHODOLOGY.md §5).

If tracked files or new code differ from HEAD, the SHA no longer identifies the
ruleset, so a '-dirty' suffix is appended. Run artifacts under runs/ are
outputs, not ruleset, and do not count as dirt.
"""
from __future__ import annotations

import subprocess

from .config import ROOT


def config_version() -> str:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    dirt = [
        line for line in status
        if line[3:] and not line[3:].startswith(("runs/", "data_cache/"))
        and not line[3:].endswith((".ots", ".ots.bak"))
    ]
    return sha + ("-dirty" if dirt else "")

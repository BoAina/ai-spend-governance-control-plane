"""
Audit Logger
============
Writes decision records and ERP writeback files to the outputs/ directory.

Every request produces a decision file.
Only approved requests produce an ERP writeback file.

This gives the system a complete, auditable record of every
procurement decision — which is a hard requirement in public sector
and grant-funded environments.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path("outputs")


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_decision_file(result: dict[str, Any]) -> Path:
    ensure_output_dir()
    path = OUTPUT_DIR / f"decision_{result['request_id']}.json"
    path.write_text(json.dumps(result, indent=2))
    return path


def write_erp_file(request_id: str, payload: dict[str, Any]) -> Path:
    ensure_output_dir()
    path = OUTPUT_DIR / f"erp_writeback_{request_id}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path

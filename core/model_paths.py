# File: core\model_paths.py
import os
from pathlib import Path
import sys


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        # EXE calisirken modeller exe yaninda olur
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]


def resolve_model_path(model_name: str, alias: str) -> str:
    """Yerel models/altinda varsa onu kullan, yoksa online modele don."""
    local_dir = _base_dir() / "models" / alias
    if local_dir.is_dir():
        return str(local_dir)
    return model_name

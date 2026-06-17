from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import importlib
import json
import os
import sys


_REQUIRED_FILES = [
    "db_connection.py",
    "db_alert.py",
]


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve()
    env_path = os.getenv("VERSIONB_PATH")
    candidates: list[Path] = []

    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.extend([
        # Packaged fallback copied with this API module.
        here.parents[1] / "external" / "versionB",

        # Shaoyu0616_B package location: <root>/external/Database/versionB.
        here.parents[3] / "external" / "Database" / "versionB",

        # Project-level official Database/versionB locations.
        here.parents[3] / "Database" / "versionB",
        here.parents[2] / "versionB",
        here.parents[2] / "Database" / "versionB",
        Path.cwd() / "versionB",
        Path.cwd().parent / "versionB",
        Path.cwd() / "external" / "versionB",
        Path.cwd() / "external" / "Database" / "versionB",
    ])

    unique: list[Path] = []
    for path in candidates:
        path = path.resolve()
        if path not in unique:
            unique.append(path)
    return unique


def find_versionb_path() -> Path | None:
    for path in _candidate_paths():
        if all((path / name).exists() for name in _REQUIRED_FILES):
            return path
    return None


def load_versionb_modules() -> Dict[str, Any]:
    """Load versionB DB modules safely.

    The service must keep running even when PostgreSQL or psycopg2 is not
    installed. Therefore this function returns a status dictionary instead of
    raising import errors to the API layer.
    """
    path = find_versionb_path()
    if path is None:
        return {
            "available": False,
            "path": None,
            "error": "versionB folder not found. Set VERSIONB_PATH or keep external/versionB in the package.",
            "modules": {},
        }

    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

    try:
        db_connection = importlib.import_module("db_connection")
        db_alert = importlib.import_module("db_alert")
    except Exception as exc:  # includes missing psycopg2
        return {
            "available": False,
            "path": str(path),
            "error": repr(exc),
            "modules": {},
        }

    return {
        "available": True,
        "path": str(path),
        "error": None,
        "modules": {
            "db_connection": db_connection,
            "db_alert": db_alert,
        },
    }


def load_db_config_file() -> Dict[str, Any]:
    """Load optional src/db_config.json for local DB overrides.

    Environment variables used by versionB still work. This JSON file is only
    a convenience for local testing and should not be committed with a real
    password.
    """
    path = Path(__file__).resolve().parent / "db_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_versionb_status() -> Dict[str, Any]:
    loaded = load_versionb_modules()
    return {
        "versionb_found": loaded.get("path") is not None,
        "versionb_path": loaded.get("path"),
        "db_module_available": loaded.get("available", False),
        "db_module_error": loaded.get("error"),
        "db_config_file_present": (Path(__file__).resolve().parent / "db_config.json").exists(),
        "required_python_package": "psycopg2 or psycopg2-binary",
    }

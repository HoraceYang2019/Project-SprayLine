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
    "db_sensor.py",
    "db_status.py",
]


def _candidate_paths() -> list[Path]:
    """Return versionB search paths in official-DB-first order.

    0617ver_1 rule:
    1. explicit env paths
    2. project official Database/versionB
    3. Shaoyu package external/Database/versionB
    4. packaged time_series_api fallback
    """
    here = Path(__file__).resolve()
    candidates: list[Path] = []

    for env_name in ("VERSIONB_PATH", "SPRAYLINE_DB_FUNCTION_PATH"):
        env_path = os.getenv(env_name)
        if env_path:
            candidates.append(Path(env_path).expanduser())

    project_root = os.getenv("SPRAYLINE_PROJECT_ROOT")
    if project_root:
        candidates.append(Path(project_root).expanduser() / "Database" / "versionB")

    package_root = here.parents[3]  # <shaoyu_root>
    candidates.extend([
        # If this folder is placed under Project-SprayLine-main/SprayLine_3/少榆0617ver_1,
        # parents[1] of package_root is usually Project-SprayLine-main.
        package_root.parents[1] / "Database" / "versionB" if len(package_root.parents) > 1 else package_root / "Database" / "versionB",
        package_root.parent / "Database" / "versionB",
        package_root / "Database" / "versionB",

        # Shaoyu package reference copy.
        package_root / "external" / "Database" / "versionB",

        # Common working-directory based locations.
        Path.cwd() / "Database" / "versionB",
        Path.cwd() / "external" / "Database" / "versionB",
        Path.cwd().parent / "Database" / "versionB",

        # Packaged fallback copied with time_series_api.
        here.parents[1] / "external" / "versionB",
    ])

    unique: list[Path] = []
    for path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved not in unique:
            unique.append(resolved)
    return unique


def find_versionb_path() -> Path | None:
    for path in _candidate_paths():
        if all((path / name).exists() for name in _REQUIRED_FILES):
            return path
    return None


def load_versionb_modules() -> Dict[str, Any]:
    path = find_versionb_path()
    if path is None:
        return {
            "available": False,
            "path": None,
            "error": "versionB folder not found. Set VERSIONB_PATH, SPRAYLINE_DB_FUNCTION_PATH, or SPRAYLINE_PROJECT_ROOT.",
            "modules": {},
        }

    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

    modules: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for module_name in ["db_connection", "db_alert", "db_sensor", "db_status", "db_future", "sprayline_db_queries"]:
        try:
            modules[module_name] = importlib.import_module(module_name)
        except Exception as exc:
            errors[module_name] = repr(exc)

    available = "db_connection" in modules and "db_alert" in modules
    return {
        "available": available,
        "path": str(path),
        "error": None if available else errors,
        "modules": modules,
        "module_errors": errors,
    }


def load_db_config_file() -> Dict[str, Any]:
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
        "module_errors": loaded.get("module_errors", {}),
        "db_config_file_present": (Path(__file__).resolve().parent / "db_config.json").exists(),
        "required_python_package": "psycopg2 or psycopg2-binary",
        "candidate_paths": [str(path) for path in _candidate_paths()],
    }

import json
from pathlib import Path
from typing import Optional


def _key(table: str, station: Optional[str]) -> str:
    return f"{table}:{station or 'ALL'}"


def load_checkpoint(path: str, table: str, station: Optional[str] = None) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get(_key(table, station))


def save_checkpoint(path: str, table: str, timestamp: str, station: Optional[str] = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    data[_key(table, station)] = timestamp
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

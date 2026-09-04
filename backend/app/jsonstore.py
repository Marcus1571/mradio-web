"""Small atomic JSON file helpers shared by userdata.py and cache.py."""

import json
from pathlib import Path


def atomic_write_json(path: Path, data) -> bool:
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        return True
    except OSError:
        return False


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

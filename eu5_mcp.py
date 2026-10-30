"""Read-only EU5 save watcher and MCP stdio server.

Requires Rakaly CLI on PATH. Never modifies game or save files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
from typing import Any

DEFAULT_DIR = Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis V" / "save games"
SAVE_DIR = Path(os.environ.get("EU5_SAVE_DIR", str(DEFAULT_DIR))).expanduser()
DB = Path(os.environ.get("EU5_MCP_DB", str(Path.home() / ".eu5-mcp" / "snapshots.sqlite3"))).expanduser()
RAKALY = os.environ.get("EU5_RAKALY", "rakaly")
POLL = max(2, int(os.environ.get("EU5_POLL_SECONDS", "5")))
MAX_SAVE_BYTES = 512 * 1024 * 1024


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS snapshots
        (id INTEGER PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT UNIQUE NOT NULL,
         observed_at REAL NOT NULL, metadata TEXT NOT NULL, data TEXT NOT NULL)""")
    db.commit()
    return db


def values_at(obj: Any, path: str) -> Any:
    """Traverse a known JSON dotted path (numeric components index lists)."""
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdecimal():
            i = int(part)
            obj = obj[i] if i < len(obj) else None
        else:
            return None
    return obj


def candidates():
    if not SAVE_DIR.is_dir():
        return []
    return sorted((p for p in SAVE_DIR.glob("*.eu5") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)


def stable_read(path: Path) -> bytes | None:
    before = path.stat()
    if before.st_size > MAX_SAVE_BYTES or before.st_size == 0:
        return None
    time.sleep(.25)
    if path.stat().st_size != before.st_size or path.stat().st_mtime_ns != before.st_mtime_ns:
        return None
    raw = path.read_bytes()
    after = path.stat()
    if len(raw) != after.st_size or after.st_mtime_ns != before.st_mtime_ns:
        return None
    return raw


def ingest(path: Path) -> str:
    raw = stable_read(path)
    if raw is None:
        return "not_stable_or_too_large"
    digest = hashlib.sha256(raw).hexdigest()
    with connect() as db:
        if db.execute("SELECT 1 FROM snapshots WHERE sha256=?", (digest,)).fetchone():
            return "unchanged"
    # Command arguments are an array; no shell, no save modification.
    result = subprocess.run([RAKALY, "json", str(path)], capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[:400])
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("Unexpected Rakaly JSON root")
    # Rakaly output schema varies by game patch; record only validated metadata.
    metadata = {"filename": path.name, "bytes": len(raw), "sha256": digest,
                "date_candidates": {key: values_at(data, key) for key in
                                    ("date", "meta_data.date", "meta.date", "metadata.date")}}
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO snapshots(path,sha256,observed_at,metadata,data) VALUES(?,?,?,?,?)",
                   (str(path), digest, time.time(), json.dumps(metadata), json.dumps(data)))
    return "ingested"


def watcher():
    seen: dict[str, tuple[int, int]] = {}
    while True:
        for path in candidates()[:30]:
            try:
                stat = path.stat()
                stamp = (stat.st_size, stat.st_mtime_ns)
                if seen.get(str(path)) == stamp:
                    continue
                outcome = ingest(path)
                if outcome in ("ingested", "unchanged"):
                    seen[str(path)] = stamp
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                print(f"EU5 watcher: {path.name}: {error}", file=sys.stderr)
        time.sleep(POLL)


def latest_rows(limit=2):
    with connect() as db:
        return db.execute("SELECT id,path,observed_at,metadata,data FROM snapshots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def snapshot_info(row):
    return {"id": row[0], "path": row[1], "observed_at": row[2], **json.loads(row[3])}


def main():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("eu5-strategy-readonly")

    @server.tool()
    def get_game_state() -> dict:
        """Last successfully parsed save; reports freshness and candidate in-game dates."""
        rows = latest_rows(1)
        return {"save_directory": str(SAVE_DIR), "status": "ready" if rows else "waiting_for_save",
                "snapshot": snapshot_info(rows[0]) if rows else None}

    @server.tool()
    def get_save_data(path: str, max_chars: int = 12000) -> dict:
        """Get one JSON subtree from the latest parsed save using a dotted path.

        Paths depend on EU5/Rakaly version; inspect keys first. Caps response length.
        """
        rows = latest_rows(1)
        if not rows:
            return {"error": "No parsed save yet"}
        if not path or len(path) > 200 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in path):
            return {"error": "Invalid dotted path"}
        data = values_at(json.loads(rows[0][4]), path)
        output = json.dumps(data, ensure_ascii=False)
        limit = max(100, min(max_chars, 25000))
        return {"path": path, "found": data is not None, "truncated": len(output) > limit,
                "json": output[:limit]}

    @server.tool()
    def list_save_fields(path: str = "") -> dict:
        """List keys at a JSON path so AI can discover supported economy/military fields."""
        rows = latest_rows(1)
        if not rows:
            return {"error": "No parsed save yet"}
        if path and (len(path) > 200 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in path)):
            return {"error": "Invalid dotted path"}
        data = values_at(json.loads(rows[0][4]), path) if path else json.loads(rows[0][4])
        return {"path": path, "type": type(data).__name__,
                "keys": list(data)[:200] if isinstance(data, dict) else None,
                "length": len(data) if isinstance(data, (dict, list)) else None}

    @server.tool()
    def compare_snapshots(path: str) -> dict:
        """Compare a single scalar or object field between the latest two saves."""
        rows = latest_rows(2)
        if len(rows) < 2:
            return {"error": "Two snapshots required"}
        if not path or len(path) > 200 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in path):
            return {"error": "Invalid dotted path"}
        new, old = (values_at(json.loads(row[4]), path) for row in rows)
        if isinstance(new, (dict, list)) or isinstance(old, (dict, list)):
            return {"error": "Use a scalar path"}
        return {"path": path, "previous": old, "latest": new,
                "delta": new - old if type(new) in (int, float) and type(old) in (int, float) else None,
                "snapshot_ids": [rows[1][0], rows[0][0]]}

    thread = threading.Thread(target=watcher, daemon=True)
    thread.start()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

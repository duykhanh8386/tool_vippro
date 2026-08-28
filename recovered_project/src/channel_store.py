# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
SQLite-based channel storage.

Replaces the old file-based (info.json + cookies.pkl) approach with a single
SQLite database stored in the platform-specific application data directory.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from src.paths import get_data_dir


def _default_db_path() -> Path:
    return get_data_dir() / "channels.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _compute_cookies_expires_at(cookies: list) -> Optional[int]:
    """Return the earliest expiration timestamp among all cookies (unix seconds)."""
    expiries = []
    for c in cookies or []:
        if not isinstance(c, dict):
            continue
        raw = c.get("expiry") or c.get("expirationDate")
        if raw is None:
            continue
        expiries.append(int(float(raw)))
    return min(expiries) if expiries else None


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS channels (
    id                    TEXT PRIMARY KEY,
    name                  TEXT,
    img_src               TEXT,
    sapisidhash           TEXT,
    delegated_session_id  TEXT,
    role                  TEXT,
    challenge             TEXT,
    botguardResponse      TEXT,
    cookies_json          TEXT NOT NULL DEFAULT '[]',
    cookies_expires_at    INTEGER,
    created_at            INTEGER NOT NULL,
    updated_at            INTEGER NOT NULL
)
"""


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_TABLE_SQL)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(channels)").fetchall()}
    if "cookies_expires_at" not in cols:
        conn.execute("ALTER TABLE channels ADD COLUMN cookies_expires_at INTEGER")
    if "overlay_png" not in cols:
        conn.execute("ALTER TABLE channels ADD COLUMN overlay_png TEXT")
    conn.commit()


def _row_to_record(row: sqlite3.Row) -> dict:
    cookies = []
    raw = row["cookies_json"]
    if raw:
        try:
            cookies = json.loads(raw)
        except Exception:
            cookies = []
    return {
        "id": row["id"],
        "name": row["name"] or "",
        "img_src": row["img_src"] or "",
        "sapisidhash": row["sapisidhash"] or "",
        "delegated_session_id": row["delegated_session_id"] or "",
        "role": row["role"] or "",
        "challenge": row["challenge"] or "",
        "botguardResponse": row["botguardResponse"] or "",
        "cookies": cookies,
        "cookies_expires_at": row["cookies_expires_at"],
        "overlay_png": (
            row["overlay_png"] if "overlay_png" in row.keys() else ""
        ) or "",
    }


class ChannelStore:
    """Thin wrapper around an SQLite database for channel CRUD."""

    def __init__(self, db_path: Optional[Path] = None):
        # Production always uses this build's isolated AppData namespace.
        # An explicit path remains available only for unit tests.
        self._db_path = Path(db_path) if db_path is not None else _default_db_path()
        self._conn = None
        self._lock = threading.RLock()

    def init_db(self) -> None:
        with self._lock:
            if self._conn is None:
                self._conn = _connect(self._db_path)
                _ensure_schema(self._conn)

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.init_db()
        return self._conn

    def upsert_channel(self, record: dict) -> None:
        channel_id = record.get("id")
        now = int(time.time())
        name = record.get("name", "")
        img_src = record.get("img_src", "")
        sapisidhash = record.get("sapisidhash", "")
        delegated_session_id = record.get("delegated_session_id", "")
        role = record.get("role", "")
        challenge = record.get("challenge", "")
        botguardResponse = record.get("botguardResponse", "")
        cookies = record.get("cookies") or []
        cookies_json = json.dumps(cookies, ensure_ascii=False)
        cookies_expires_at = _compute_cookies_expires_at(cookies)

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO channels (
                    id, name, img_src, sapisidhash, delegated_session_id,
                    role, challenge, botguardResponse, cookies_json, cookies_expires_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    img_src=excluded.img_src,
                    sapisidhash=excluded.sapisidhash,
                    delegated_session_id=excluded.delegated_session_id,
                    role=excluded.role,
                    challenge=excluded.challenge,
                    botguardResponse=excluded.botguardResponse,
                    cookies_json=excluded.cookies_json,
                    cookies_expires_at=excluded.cookies_expires_at,
                    updated_at=excluded.updated_at
                """,
                (
                    channel_id,
                    name,
                    img_src,
                    sapisidhash,
                    delegated_session_id,
                    role,
                    challenge,
                    botguardResponse,
                    cookies_json,
                    cookies_expires_at,
                    now,
                    now,
                ),
            )
            self.conn.commit()

    def list_channels(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM channels ORDER BY updated_at DESC"
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def get_channel(self, channel_id: str) -> Optional[dict]:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM channels WHERE id = ?",
                (channel_id,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def get_overlay_png(self, channel_id: str) -> str:
        """Đọc đường dẫn PNG overlay của kênh; trả chuỗi rỗng nếu chưa có."""
        with self._lock:
            row = self.conn.execute(
                "SELECT overlay_png FROM channels WHERE id = ?",
                (channel_id,),
            ).fetchone()
        if not row:
            return ""
        return row["overlay_png"] or ""

    def set_overlay_png(self, channel_id: str, path: str) -> None:
        """Lưu đường dẫn PNG tên kênh cho một kênh."""
        with self._lock:
            self.conn.execute(
                "UPDATE channels SET overlay_png=?, updated_at=? WHERE id=?",
                (path, int(time.time()), channel_id),
            )
            self.conn.commit()

    def delete_channel(self, channel_id: str) -> bool:
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM channels WHERE id = ?",
                (channel_id,),
            )
            self.conn.commit()
            return (cur.rowcount or 0) > 0


channel_store = ChannelStore()

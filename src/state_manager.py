# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
State Manager for persisting page states to SQLite.
Provides automatic save/load functionality for UI components.
"""

import json
import sqlite3
from typing import Any, Dict, Optional

from loguru import logger

from src.paths import get_data_dir

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_state (
    page_name TEXT PRIMARY KEY,
    state_json TEXT NOT NULL
)
"""


class StateManager:
    """Manages persistent state storage for application pages via SQLite."""

    def __init__(self):
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            db_path = get_data_dir() / "app_state.db"
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._conn.execute(_CREATE_TABLE_SQL)
            self._conn.commit()
        return self._conn

    def save_state(self, page_name: str, state: Dict[str, Any]) -> bool:
        """Save state for a specific page."""
        try:
            self._get_conn().execute(
                "INSERT INTO app_state (page_name, state_json) VALUES (?, ?) "
                "ON CONFLICT(page_name) DO UPDATE SET state_json=excluded.state_json",
                (page_name, json.dumps(state, ensure_ascii=False)),
            )
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save state for {page_name}: {e}")
            return False

    def load_state(self, page_name: str) -> Optional[Dict[str, Any]]:
        """Load state for a specific page."""
        try:
            row = self._get_conn().execute(
                "SELECT state_json FROM app_state WHERE page_name = ?",
                (page_name,),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to load state for {page_name}: {e}")
            return None

    def clear_state(self, page_name: str) -> bool:
        """Clear saved state for a specific page."""
        try:
            self._get_conn().execute(
                "DELETE FROM app_state WHERE page_name = ?",
                (page_name,),
            )
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear state for {page_name}: {e}")
            return False

    def clear_all_states(self) -> bool:
        """Clear all saved states."""
        try:
            self._get_conn().execute("DELETE FROM app_state")
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear all states: {e}")
            return False


state_manager = StateManager()

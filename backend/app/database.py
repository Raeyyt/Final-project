import sqlite3
from typing import Generator
import os

from .config import settings

# Since the user requested saving as school.db in the main directory
# We'll resolve the path relative to this file to point to the root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "school.db")


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Dependency that yields a raw sqlite3 connection with dict-like rows
    and foreign keys enabled.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

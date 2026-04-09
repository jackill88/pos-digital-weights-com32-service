import sqlite3
import os
import sys


def get_app_directory():
    if hasattr(sys, "_MEIPASS"):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def get_database_path():
    return os.path.join(get_app_directory(), "app.db")


class Database:

    def __init__(self):
        self.path = get_database_path()
        self._initialize()

    def _initialize(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT NOT NULL
                )
            """)
            conn.commit()

    def insert_api_key_hash(self, key_hash: str):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO api_keys (key_hash) VALUES (?)",
                (key_hash,)
            )
            conn.commit()
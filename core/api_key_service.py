import secrets
import hashlib
import sqlite3
from .database import Database


class APIKeyService:

    def __init__(self, database: Database):
        self.db = database
        self._cache = set()  # in-memory hash cache
        self.update_cache()

    # --------------------------
    # Public API
    # --------------------------

    def generate_key(self) -> str:
        raw_key = secrets.token_urlsafe(32)

        key_hash = self._hash(raw_key)
        self.db.insert_api_key_hash(key_hash)

        # update cache immediately
        self._cache.add(key_hash)

        return raw_key
    
    def update_cache(self):
        """Load all stored hashes into RAM."""
        with sqlite3.connect(self.db.path) as conn:
            rows = conn.execute("SELECT key_hash FROM api_keys").fetchall()
            self._cache = set(row[0] for row in rows)

    def validate_key(self, raw_key: str) -> bool:
        if not raw_key:
            return False

        key_hash = self._hash(raw_key)
        return key_hash in self._cache

    # --------------------------
    # Internal helpers
    # --------------------------

    def _hash(self, raw_key: str) -> str:
        return hashlib.md5(raw_key.encode()).hexdigest()
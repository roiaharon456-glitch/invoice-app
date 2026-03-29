import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "/tmp/users.db")


class Database:
    def __init__(self):
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    bank_name TEXT NOT NULL,
                    bank_number TEXT NOT NULL,
                    branch_number TEXT NOT NULL,
                    account_number TEXT NOT NULL,
                    account_holder TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_user(self, name: str):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT name, bank_name, bank_number, branch_number, account_number, account_holder FROM users WHERE name = ?",
                (name,)
            ).fetchone()
        if row:
            return {
                "name": row[0],
                "bank_name": row[1],
                "bank_number": row[2],
                "branch_number": row[3],
                "account_number": row[4],
                "account_holder": row[5],
            }
        return None

    def save_user(self, name, bank_name, bank_number, branch_number, account_number, account_holder):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO users (name, bank_name, bank_number, branch_number, account_number, account_holder) VALUES (?, ?, ?, ?, ?, ?)",
                (name, bank_name, bank_number, branch_number, account_number, account_holder)
            )
            conn.commit()

    def update_user(self, name, bank_name, bank_number, branch_number, account_number, account_holder):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET bank_name=?, bank_number=?, branch_number=?, account_number=?, account_holder=? WHERE name=?",
                (bank_name, bank_number, branch_number, account_number, account_holder, name)
            )
            conn.commit()

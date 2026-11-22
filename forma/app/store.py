"""Document store: one table of JSON documents keyed by (kind, key).

kinds: profile/main, weights/main, coach/main, day/<YYYY-MM-DD>, log/<date>_s<idx>, sys/<name>
The web app and the WhatsApp agent read and write the same documents.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

import httpx

from . import config


class SupabaseStore:
    def __init__(self, url: str, key: str):
        self.base = url + "/rest/v1/docs"
        headers = {"apikey": key}
        if key.startswith("eyJ"):  # legacy service_role JWT; new sb_secret_ keys go in the apikey header only
            headers["Authorization"] = f"Bearer {key}"
        self.http = httpx.Client(timeout=15, headers=headers)

    def get(self, kind, key):
        r = self.http.get(self.base, params={"kind": f"eq.{kind}", "key": f"eq.{key}", "select": "data"})
        r.raise_for_status()
        rows = r.json()
        return rows[0]["data"] if rows else None

    def put(self, kind, key, data):
        body = {"kind": kind, "key": key, "data": data, "updated_at": datetime.now(timezone.utc).isoformat()}
        r = self.http.post(self.base, json=body, headers={"Prefer": "resolution=merge-duplicates,return=minimal"})
        r.raise_for_status()

    def delete(self, kind, key):
        self.http.delete(self.base, params={"kind": f"eq.{kind}", "key": f"eq.{key}"}).raise_for_status()

    def list(self, kind, min_key=None):
        params = {"kind": f"eq.{kind}", "select": "key,data", "order": "key.asc", "limit": "1000"}
        if min_key:
            params["key"] = f"gte.{min_key}"
        r = self.http.get(self.base, params=params)
        r.raise_for_status()
        return {row["key"]: row["data"] for row in r.json()}


class SqliteStore:
    def __init__(self, path: str):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.execute("create table if not exists docs (kind text, key text, data text, updated_at text, primary key (kind, key))")
        self.db.commit()

    def get(self, kind, key):
        with self.lock:
            row = self.db.execute("select data from docs where kind=? and key=?", (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, kind, key, data):
        with self.lock:
            self.db.execute("insert or replace into docs values (?,?,?,?)", (kind, key, json.dumps(data, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            self.db.commit()

    def delete(self, kind, key):
        with self.lock:
            self.db.execute("delete from docs where kind=? and key=?", (kind, key))
            self.db.commit()

    def list(self, kind, min_key=None):
        q, args = "select key, data from docs where kind=?", [kind]
        if min_key:
            q += " and key>=?"
            args.append(min_key)
        with self.lock:
            rows = self.db.execute(q + " order by key", args).fetchall()
        return {k: json.loads(d) for k, d in rows}


def make_store():
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        return SupabaseStore(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return SqliteStore(config.DB_PATH)

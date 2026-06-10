"""Shared Postgres connection for the Mnemosyne log/archive migrators.

Decoupled from lib/embeddings.py on purpose (that file is owned by the embeddings
sidecar). Resolves creds the same way — env > ~/.config/mnemosyne/pg-creds.json >
defaults — and FORCES client_encoding=UTF8, because the cluster is SQL_ASCII and
our titles/bodies are full of em-dashes and accented characters.
"""

import json
import os
from pathlib import Path

DEFAULTS = {"host": "10.0.50.14", "port": 5432,
            "dbname": "mnemosyne", "user": "mnemosyne"}
CREDS_FILE = Path.home() / ".config/mnemosyne/pg-creds.json"


def load_params() -> dict:
    params = dict(DEFAULTS)
    if CREDS_FILE.exists():
        params.update(json.loads(CREDS_FILE.read_text()))
    env = {
        "host": os.environ.get("MNEME_PG_HOST"),
        "port": os.environ.get("MNEME_PG_PORT"),
        "dbname": os.environ.get("MNEME_PG_DB"),
        "user": os.environ.get("MNEME_PG_USER"),
        "password": os.environ.get("MNEME_PG_PASSWORD"),
    }
    params.update({k: v for k, v in env.items() if v})
    if "password" not in params:
        raise RuntimeError(
            "no Postgres password — set MNEME_PG_PASSWORD or "
            f"{CREDS_FILE} ({{\"password\": ...}})"
        )
    params["connect_timeout"] = 10
    return params


def connect():
    """Open a UTF-8-forced psycopg2 connection (SQL_ASCII-cluster safe)."""
    import psycopg2
    conn = psycopg2.connect(**load_params())
    conn.set_client_encoding("UTF8")
    return conn

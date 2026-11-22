"""Create or open the shared and personal research indexes."""
import json
import os
import re
import sqlite3
from pathlib import Path

PUBLIC_SOURCES = Path(__file__).resolve().parents[1] / "references" / "public-sources.json"


def personal_index():
    override = os.environ.get("HANWU_CROCODILE_INDEX")
    return Path(override).expanduser().resolve() if override else Path.home() / ".hanwu-crocodile" / "research.sqlite3"


def initialize(db):
    db.executescript("""
        CREATE TABLE documents (
            source TEXT PRIMARY KEY, title TEXT, date TEXT, locator TEXT,
            channels TEXT, kind TEXT, attribution TEXT, status TEXT
        );
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY, source TEXT REFERENCES documents(source),
            location TEXT, body TEXT
        );
        CREATE INDEX chunks_source ON chunks(source);
    """)
    try:
        db.execute("CREATE VIRTUAL TABLE search USING fts5(title, body, tokenize='trigram')")
    except sqlite3.OperationalError as error:
        if not any(message in str(error).lower() for message in ("fts5", "tokenizer")):
            raise


def has_fts(db):
    return bool(db.execute("SELECT 1 FROM sqlite_schema WHERE name='search'").fetchone())


def chunks(body, size=1400, overlap=160):
    body = re.sub(r"\n{3,}", "\n\n", body.replace("\x00", " ")).strip()
    offset = 0
    while offset < len(body):
        end = min(offset + size, len(body))
        if end < len(body):
            split = body.rfind("\n", offset + size // 2, end)
            if split >= 0:
                end = split + 1
        yield body[offset:end]
        if end == len(body):
            break
        offset = end - overlap


def add_document(db, record, sections, use_fts):
    keys = ("source", "title", "date", "locator", "channels", "kind", "attribution", "status")
    db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)", tuple(record.get(key, "") for key in keys))
    for location, body in sections:
        for part, text in enumerate(chunks(body), 1):
            label = location if part == 1 else f"{location} · 片段 {part}"
            row = db.execute("INSERT INTO chunks(source, location, body) VALUES (?,?,?)", (record["source"], label, text))
            if use_fts:
                db.execute("INSERT INTO search(rowid, title, body) VALUES (?,?,?)", (row.lastrowid, record["title"], text))


def add_public_sources(db):
    use_fts = has_fts(db)
    records = json.loads(PUBLIC_SOURCES.read_text(encoding="utf-8"))
    for record in records:
        summary = record.get("summary", "")
        public_notes = [("公开资料摘要（编者归纳）", summary)] if summary else [("公开目录", record["title"])]
        add_document(db, record, public_notes, use_fts)

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "tickets.db"


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = _conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'medium',
                product TEXT DEFAULT '',
                client_name TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                client_question TEXT DEFAULT '',
                research_summary TEXT DEFAULT '',
                reply_draft_path TEXT DEFAULT '',
                reply_sent INTEGER NOT NULL DEFAULT 0,
                related_files TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kb (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL DEFAULT '',
                source TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ── Tickets ─────────────────────────────────────────────


def list_tickets(status=None, product=None, search=None):
    conn = _conn()
    try:
        query = "SELECT * FROM tickets WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if product:
            query += " AND product = ?"
            params.append(product)
        if search:
            query += " AND (summary LIKE ? OR ticket_id LIKE ? OR client_question LIKE ? OR notes LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        query += " ORDER BY updated_at DESC"
        return [_ticket_row(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def get_ticket(ticket_id):
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        return _ticket_row(row) if row else None
    finally:
        conn.close()


def create_ticket(**kw):
    conn = _conn()
    try:
        related = json.dumps(kw.get("related_files") or [])
        conn.execute(
            """
            INSERT INTO tickets
                (ticket_id, status, priority, product, client_name,
                 summary, client_question, research_summary,
                 reply_draft_path, reply_sent, related_files, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kw["ticket_id"],
                kw.get("status", "pending"),
                kw.get("priority", "medium"),
                kw.get("product", ""),
                kw.get("client_name", ""),
                kw.get("summary", ""),
                kw.get("client_question", ""),
                kw.get("research_summary", ""),
                kw.get("reply_draft_path", ""),
                kw.get("reply_sent", 0),
                related,
                kw.get("notes", ""),
            ),
        )
        conn.commit()
        return get_ticket(kw["ticket_id"])
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_ticket(ticket_id, **kw):
    conn = _conn()
    try:
        allowed = {
            "status", "priority", "product", "client_name", "summary",
            "client_question", "research_summary", "reply_draft_path",
            "reply_sent", "related_files", "notes",
        }
        updates = {k: v for k, v in kw.items() if k in allowed and v is not None}
        if not updates:
            return get_ticket(ticket_id)
        if "related_files" in updates and isinstance(updates["related_files"], list):
            updates["related_files"] = json.dumps(updates["related_files"])
        updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [ticket_id]
        conn.execute(f"UPDATE tickets SET {set_clause} WHERE ticket_id = ?", values)
        conn.commit()
        return get_ticket(ticket_id)
    finally:
        conn.close()


def delete_ticket(ticket_id):
    conn = _conn()
    try:
        conn.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


# ── KB ──────────────────────────────────────────────────


def list_kb(category=None, search=None):
    conn = _conn()
    try:
        query = "SELECT * FROM kb WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (value LIKE ? OR key LIKE ? OR source LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        query += " ORDER BY category, key"
        return [_kb_row(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def get_kb(kb_id):
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM kb WHERE id = ?", (kb_id,)).fetchone()
        return _kb_row(row) if row else None
    finally:
        conn.close()


def create_kb(category, key, value="", source="", tags=None):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO kb (category, key, value, source, tags) VALUES (?, ?, ?, ?, ?)",
            (category, key, value, source, json.dumps(tags or [])),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM kb WHERE category = ? AND key = ?", (category, key)
        ).fetchone()
        return _kb_row(row)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_kb(kb_id, **kw):
    conn = _conn()
    try:
        allowed = {"category", "key", "value", "source", "tags"}
        updates = {k: v for k, v in kw.items() if k in allowed and v is not None}
        if not updates:
            return get_kb(kb_id)
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [kb_id]
        conn.execute(f"UPDATE kb SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return get_kb(kb_id)
    finally:
        conn.close()


def delete_kb(kb_id):
    conn = _conn()
    try:
        conn.execute("DELETE FROM kb WHERE id = ?", (kb_id,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def list_kb_categories():
    conn = _conn()
    try:
        rows = conn.execute("SELECT DISTINCT category FROM kb ORDER BY category").fetchall()
        return [r["category"] for r in rows]
    finally:
        conn.close()


# ── Helpers ─────────────────────────────────────────────


def _ticket_row(row):
    d = dict(row)
    d["related_files"] = json.loads(d.get("related_files", "[]"))
    return d


def _kb_row(row):
    d = dict(row)
    d["tags"] = json.loads(d.get("tags", "[]"))
    return d

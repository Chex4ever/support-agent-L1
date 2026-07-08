"""
Migrate old TicketDB KB entries to BookStack.

Usage:
    python -m tools.bookstack.migrate_kb          # show plan (dry-run)
    python -m tools.bookstack.migrate_kb --apply  # actually create pages
"""
import json
import os
import sys

from . import client as api

# Import TicketDB database to get KB entries
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tools.ticketdb import database as db

# Name of the book to create for our internal KB
BOOK_NAME = "Omnigent — знания AI-агента"
BOOK_DESC = "Внутренняя база знаний L2-агента техподдержки iRidi. Мигрировано из TicketDB SQLite."

CATEGORY_MAP = {
    "iridi_script": "iRidi Script",
    "android": "Android / droidVNC-NG",
    "api": "API (Omnidesk, Redmine, домены)",
    "general": "Общее (инструменты, окружение)",
    "integration": "Интеграции (BACnet, Modbus, HDL, Rapix)",
}


def _get_or_create_book():
    """Find or create the target book in BookStack."""
    books = api.list_books()
    for b in books:
        if b["name"] == BOOK_NAME:
            return b
    # Create
    shelf_id = None
    shelves = api.list_shelves()
    if shelves:
        shelf_id = shelves[0]["id"]
    book = api.create_book(BOOK_NAME, BOOK_DESC, shelf_id=shelf_id)
    print(f"Created book: {BOOK_NAME} (id={book['id']})")
    return book


def _format_kb_entry(kb):
    """Format a KB entry as markdown."""
    lines = [
        f"# {kb['key']}",
        "",
        f"**Категория:** {CATEGORY_MAP.get(kb['category'], kb['category'])}",
        f"**Источник:** {kb.get('source', '—')}",
        "",
        "---",
        "",
        kb.get("value", ""),
        "",
    ]
    if kb.get("tags"):
        lines.append(f"\n**Теги:** {', '.join(kb['tags'])}")
    return "\n".join(lines)


def migrate(dry_run=True):
    db.init_db()
    entries = db.list_kb()

    if not entries:
        print("No KB entries found in TicketDB.")
        return

    print(f"Found {len(entries)} KB entries in TicketDB.\n")

    if dry_run:
        print("=== DRY RUN — no changes will be made ===")
        print(f"  Would create book: '{BOOK_NAME}'")
        print(f"  Would create pages:")
        for e in entries:
            name = f"[{CATEGORY_MAP.get(e['category'], e['category'])}] {e['key']}"
            print(f"    - {name}")
        print(f"\n  Run with --apply to execute.")
        return

    # Real run
    book = _get_or_create_book()

    created = 0
    for e in entries:
        name = f"[{CATEGORY_MAP.get(e['category'], e['category'])}] {e['key']}"
        md = _format_kb_entry(e)

        # Check if page already exists
        existing = api.list_pages(book_id=book["id"])
        match = [p for p in existing if p["name"] == name]
        if match:
            api.update_page(match[0]["id"], name=name, markdown=md)
            print(f"  Updated: {name}")
        else:
            api.create_page(book["id"], name, markdown=md)
            print(f"  Created: {name}")
        created += 1

    print(f"\nDone. {created} pages created/updated in BookStack.")
    print(f"  Book: {BOOK_NAME}")
    print(f"  URL: {api.BOOKSTACK_URL}/books/{book['slug']}")


if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv
    migrate(dry_run=dry_run)

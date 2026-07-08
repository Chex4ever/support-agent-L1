"""
CLI for TicketDB.

Usage:
    python -m tools.ticketdb.cli tickets list [--status S] [--product P] [--search Q]
    python -m tools.ticketdb.cli tickets get <ticket_id>
    python -m tools.ticketdb.cli tickets add <ticket_id> [--status S] [--priority P] ...
    python -m tools.ticketdb.cli tickets update <ticket_id> [--status S] ...
    python -m tools.ticketdb.cli tickets delete <ticket_id>

    python -m tools.ticketdb.cli kb list [--category C] [--search Q]
    python -m tools.ticketdb.cli kb get <id>
    python -m tools.ticketdb.cli kb create <category> <key> [--value V] [--source S] [--tags TAGS]
    python -m tools.ticketdb.cli kb update <id> [--value V] [--source S] [--tags TAGS]
    python -m tools.ticketdb.cli kb delete <id>
"""

import argparse
import json
import sys

from . import database as db

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    db.init_db()
    parser = argparse.ArgumentParser(prog="ticketdb")
    sub = parser.add_subparsers(dest="entity", required=True)

    # ── tickets subcommands ──
    tp = sub.add_parser("tickets")
    tsub = tp.add_subparsers(dest="action", required=True)

    p = tsub.add_parser("list")
    p.add_argument("--status")
    p.add_argument("--product")
    p.add_argument("--search")

    p = tsub.add_parser("get")
    p.add_argument("ticket_id")

    p = tsub.add_parser("add")
    p.add_argument("ticket_id")
    p.add_argument("--status", default="pending")
    p.add_argument("--priority", default="medium")
    p.add_argument("--product", default="")
    p.add_argument("--client-name", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--client-question", default="")
    p.add_argument("--research-summary", default="")
    p.add_argument("--reply-draft-path", default="")
    p.add_argument("--reply-sent", type=int, default=0)
    p.add_argument("--notes", default="")

    p = tsub.add_parser("update")
    p.add_argument("ticket_id")
    p.add_argument("--status")
    p.add_argument("--priority")
    p.add_argument("--product")
    p.add_argument("--client-name")
    p.add_argument("--summary")
    p.add_argument("--client-question")
    p.add_argument("--research-summary")
    p.add_argument("--reply-draft-path")
    p.add_argument("--reply-sent", type=int)
    p.add_argument("--notes")

    p = tsub.add_parser("delete")
    p.add_argument("ticket_id")

    # ── kb subcommands ──
    kp = sub.add_parser("kb")
    ksub = kp.add_subparsers(dest="action", required=True)

    p = ksub.add_parser("list")
    p.add_argument("--category")
    p.add_argument("--search")

    p = ksub.add_parser("get")
    p.add_argument("id", type=int)

    p = ksub.add_parser("create")
    p.add_argument("category")
    p.add_argument("key")
    p.add_argument("--value", default="")
    p.add_argument("--source", default="")

    p = ksub.add_parser("update")
    p.add_argument("id", type=int)
    p.add_argument("--category")
    p.add_argument("--key")
    p.add_argument("--value")
    p.add_argument("--source")

    p = ksub.add_parser("delete")
    p.add_argument("id", type=int)

    args = parser.parse_args()

    if args.entity == "tickets":
        _handle_tickets(args)
    elif args.entity == "kb":
        _handle_kb(args)


def _handle_tickets(args):
    if args.action == "list":
        rows = db.list_tickets(
            status=args.status, product=args.product, search=args.search
        )
        if not rows:
            print("No tickets found.")
            return
        _print_ticket_table(rows)

    elif args.action == "get":
        t = db.get_ticket(args.ticket_id)
        if not t:
            print(f"Ticket '{args.ticket_id}' not found.")
            sys.exit(1)
        _print_ticket_detail(t)

    elif args.action == "add":
        kw = {
            "ticket_id": args.ticket_id,
            "status": args.status,
            "priority": args.priority,
            "product": args.product,
            "client_name": args.client_name,
            "summary": args.summary,
            "client_question": args.client_question,
            "research_summary": args.research_summary,
            "reply_draft_path": args.reply_draft_path,
            "reply_sent": args.reply_sent,
            "notes": args.notes,
        }
        t = db.create_ticket(**kw)
        if not t:
            print(f"Ticket '{args.ticket_id}' already exists.")
            sys.exit(1)
        print(f"Ticket '{args.ticket_id}' created.")
        _print_ticket_detail(t)

    elif args.action == "update":
        kw = {}
        for k in (
            "status", "priority", "product", "client_name", "summary",
            "client_question", "research_summary", "reply_draft_path",
            "reply_sent", "notes",
        ):
            v = getattr(args, k, None)
            if v is not None:
                kw[k] = v
        t = db.update_ticket(args.ticket_id, **kw)
        if not t:
            print(f"Ticket '{args.ticket_id}' not found.")
            sys.exit(1)
        print(f"Ticket '{args.ticket_id}' updated.")
        _print_ticket_detail(t)

    elif args.action == "delete":
        if db.delete_ticket(args.ticket_id):
            print(f"Ticket '{args.ticket_id}' deleted.")
        else:
            print(f"Ticket '{args.ticket_id}' not found.")
            sys.exit(1)


def _handle_kb(args):
    if args.action == "list":
        rows = db.list_kb(category=args.category, search=args.search)
        if not rows:
            print("No KB entries found.")
            return
        _print_kb_table(rows)

    elif args.action == "get":
        entry = db.get_kb(args.id)
        if not entry:
            print(f"KB entry #{args.id} not found.")
            sys.exit(1)
        _print_kb_detail(entry)

    elif args.action == "create":
        entry = db.create_kb(
            category=args.category,
            key=args.key,
            value=args.value,
            source=args.source,
        )
        if not entry:
            print(f"KB entry '{args.category}/{args.key}' already exists.")
            sys.exit(1)
        print(f"KB entry '{args.category}/{args.key}' created (#{entry['id']}).")
        _print_kb_detail(entry)

    elif args.action == "update":
        kw = {}
        for k in ("category", "key", "value", "source"):
            v = getattr(args, k, None)
            if v is not None:
                kw[k] = v
        entry = db.update_kb(args.id, **kw)
        if not entry:
            print(f"KB entry #{args.id} not found.")
            sys.exit(1)
        print(f"KB entry #{args.id} updated.")
        _print_kb_detail(entry)

    elif args.action == "delete":
        if db.delete_kb(args.id):
            print(f"KB entry #{args.id} deleted.")
        else:
            print(f"KB entry #{args.id} not found.")
            sys.exit(1)


# ── Formatters ──────────────────────────────────────────


def _print_ticket_table(rows):
    headers = ["ID", "Status", "Priority", "Product", "Summary"]
    data = []
    for r in rows:
        data.append([
            r["ticket_id"],
            r["status"],
            r["priority"],
            r["product"],
            r["summary"][:60],
        ])
    _print_table(headers, data)
    print(f"\n{len(rows)} ticket(s)")


def _print_ticket_detail(t):
    print(f"\nTicket: {t['ticket_id']}")
    print(f"  Status:       {t['status']}")
    print(f"  Priority:     {t['priority']}")
    print(f"  Product:      {t['product']}")
    print(f"  Client:       {t['client_name']}")
    print(f"  Summary:      {t['summary']}")
    print(f"  Question:     {t['client_question'][:200]}")
    print(f"  Research:     {t['research_summary'][:200]}")
    print(f"  Reply draft:  {t['reply_draft_path'] or '—'}")
    print(f"  Reply sent:   {t['reply_sent']}")
    print(f"  Notes:        {t['notes'][:200]}")
    print(f"  Files:        {', '.join(t['related_files']) if t['related_files'] else '—'}")
    print(f"  Created:      {t['created_at']}")
    print(f"  Updated:      {t['updated_at']}")


def _print_kb_table(rows):
    headers = ["#", "Category", "Key", "Value"]
    data = []
    for r in rows:
        data.append([
            str(r["id"]),
            r["category"],
            r["key"],
            r["value"][:70],
        ])
    _print_table(headers, data)
    print(f"\n{len(rows)} entry(ies)")


def _print_kb_detail(entry):
    print(f"\nKB #{entry['id']}: {entry['category']}/{entry['key']}")
    print(f"  Value:    {entry['value']}")
    print(f"  Source:   {entry['source'] or '—'}")
    print(f"  Tags:     {', '.join(entry['tags']) if entry['tags'] else '—'}")
    print(f"  Created:  {entry['created_at']}")
    print(f"  Updated:  {entry['updated_at']}")


def _sanitize(text):
    return str(text).replace("\u2014", "--").replace("\u2192", "->").replace("\u2013", "-")


def _print_table(headers, rows):
    safe_rows = []
    for row in rows:
        safe_rows.append([_sanitize(str(c)) for c in row])
    widths = [len(h) for h in headers]
    for row in safe_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = " | ".join(f"{{:{w}}}" for w in widths)
    sep = "-+-".join("-" * w for w in widths)
    print(fmt.format(*headers))
    print(sep)
    for row in safe_rows:
        print(fmt.format(*row))


if __name__ == "__main__":
    main()

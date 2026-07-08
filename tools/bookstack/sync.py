"""
BookStack ↔ local filesystem sync.

Usage:
    python -m tools.bookstack.sync init        # download all content from BookStack
    python -m tools.bookstack.sync pull        # same as init
    python -m tools.bookstack.sync push        # upload local changes (create/update, never delete)
    python -m tools.bookstack.sync status      # show local vs remote counts

Local structure:
    bookstack_local/
    └── shelves/<shelf_slug>/
        └── books/<book_slug>/
            ├── book.json              # metadata
            └── chapters/<chapter_slug>/
                ├── chapter.json       # metadata
                └── pages/<page_slug>.md  # markdown content
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import client as api

LOCAL_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "bookstack_local"))
MAX_WORKERS = 8  # parallel API calls


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _read_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_md(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")


def _read_md(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def cmd_init():
    """Download ALL content from BookStack to local."""
    print("Pulling from BookStack (parallel)...")

    # --- Shelves ---
    shelves = api.list_shelves()
    shelf_map = {s["id"]: s for s in shelves}
    for s in shelves:
        shelf = api.get_shelf(s["id"])
        _write_json(os.path.join(LOCAL_DIR, "shelves", s["slug"], "shelf.json"), shelf)

    _write_json(os.path.join(LOCAL_DIR, "shelves.json"), [
        {"id": s["id"], "slug": s["slug"], "name": s["name"], "updated_at": s["updated_at"]}
        for s in shelves
    ])

    # --- Books ---
    all_books = api.list_books()
    print(f"  {len(all_books)} books found")

    # Parallel: fetch all book details
    book_details = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fut_map = {pool.submit(api.get_book, b["id"]): b for b in all_books}
        for fut in as_completed(fut_map):
            b = fut_map[fut]
            try:
                book = fut.result()
                book_details[b["id"]] = book
            except Exception as e:
                print(f"  FAIL book {b.get('name', b['id'])}: {e}")

    # Collect all pages & chapters that need fetching
    all_chapter_ids = []
    all_page_ids = []
    book_chapter_pages = {}  # (book_slug, ch_slug) -> [(page_id, page_slug)]
    book_standalone_pages = {}  # book_slug -> [(page_id, page_slug)]

    for b in all_books:
        book = book_details.get(b["id"])
        if not book:
            continue
        shelf_slug = "unsorted"
        shelf_ids = [s["id"] for s in book.get("shelves", [])]
        if shelf_ids and shelf_ids[0] in shelf_map:
            shelf_slug = shelf_map[shelf_ids[0]]["slug"]

        book_dir = os.path.join(LOCAL_DIR, "shelves", shelf_slug, "books", book["slug"])
        book_meta = {k: v for k, v in book.items() if k != "contents"}
        _write_json(os.path.join(book_dir, "book.json"), book_meta)

        for item in book.get("contents", []):
            if item.get("type") == "chapter":
                all_chapter_ids.append(item["id"])
                book_chapter_pages.setdefault((book["slug"], item["slug"]), [])
                for cp in item.get("pages", []):
                    all_page_ids.append(cp["id"])
                    book_chapter_pages[(book["slug"], item["slug"])].append((cp["id"], cp["slug"]))
            elif item.get("type") == "page":
                all_page_ids.append(item["id"])
                book_standalone_pages.setdefault(book["slug"], [])
                book_standalone_pages[book["slug"]].append((item["id"], item["slug"]))

    # Parallel: fetch all chapters
    chapters = {}
    print(f"  Fetching {len(all_chapter_ids)} chapters...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fut_map = {pool.submit(api.get_chapter, ch_id): ch_id for ch_id in all_chapter_ids}
        for fut in as_completed(fut_map):
            ch_id = fut_map[fut]
            try:
                chapters[ch_id] = fut.result()
            except Exception as e:
                print(f"    FAIL chapter {ch_id}: {e}")

    # Parallel: fetch all pages
    pages = {}
    print(f"  Fetching {len(all_page_ids)} pages...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fut_map = {pool.submit(lambda pid: api.get_page(pid, raw=True), pid): pid for pid in list(set(all_page_ids))}
        for fut in as_completed(fut_map):
            pid = fut_map[fut]
            try:
                pages[pid] = fut.result()
            except Exception as e:
                print(f"    FAIL page {pid}: {e}")

    # --- Write everything to disk ---
    for (book_slug, ch_slug), ch_pages in book_chapter_pages.items():
        ch = chapters.get(ch_pages[0][0] if ch_pages else None)
        # Find chapter by slug from contents
        ch_data = None
        for b in book_details.values():
            if b["slug"] == book_slug:
                for item in b.get("contents", []):
                    if item.get("type") == "chapter" and item["slug"] == ch_slug:
                        ch_data = chapters.get(item["id"])
                        break
        if not ch_data:
            continue

        shelf_slug = _find_shelf(book_details, book_slug, shelf_map)
        ch_dir = os.path.join(LOCAL_DIR, "shelves", shelf_slug, "books", book_slug, "chapters", ch_slug)
        _write_json(os.path.join(ch_dir, "chapter.json"), ch_data)

        for pid, pslug in ch_pages:
            page = pages.get(pid)
            if page:
                md = page.get("markdown") or page.get("html", "")
                _write_md(os.path.join(ch_dir, "pages", f"{pslug}.md"), md)

    for book_slug, standalones in book_standalone_pages.items():
        shelf_slug = _find_shelf(book_details, book_slug, shelf_map)
        for pid, pslug in standalones:
            page = pages.get(pid)
            if page:
                md = page.get("markdown") or page.get("html", "")
                _write_md(os.path.join(LOCAL_DIR, "shelves", shelf_slug, "books", book_slug, "pages", f"{pslug}.md"), md)

    c_count = len(all_chapter_ids)
    p_count = len(set(all_page_ids))
    print(f"Done. {c_count} chapters, {p_count} pages synced to {LOCAL_DIR}")


def _find_shelf(book_details, book_slug, shelf_map):
    for b in book_details.values():
        if b["slug"] == book_slug:
            shelf_ids = [s["id"] for s in b.get("shelves", [])]
            if shelf_ids and shelf_ids[0] in shelf_map:
                return shelf_map[shelf_ids[0]]["slug"]
    return "unsorted"


def cmd_pull():
    cmd_init()


def cmd_push():
    """Upload local changes (create/update only, never delete)."""
    print("Pushing local changes to BookStack...")
    shelves_dir = os.path.join(LOCAL_DIR, "shelves")
    if not os.path.isdir(shelves_dir):
        print("No local data. Run 'init' first.")
        return

    for shelf_slug in os.listdir(shelves_dir):
        books_path = os.path.join(shelves_dir, shelf_slug, "books")
        if not os.path.isdir(books_path):
            continue
        for book_slug in os.listdir(books_path):
            book_path = os.path.join(books_path, book_slug)
            if not os.path.isdir(book_path):
                continue
            book_json = _read_json(os.path.join(book_path, "book.json"))
            if not book_json:
                continue

            try:
                remote_book = api.get_book(book_json["id"])
                if book_json.get("description", "") != remote_book.get("description", ""):
                    api.update_book(book_json["id"], description=book_json.get("description", ""))
                    print(f"  Updated book: {book_json['name']}")
            except Exception as e:
                print(f"  SKIP book {book_slug}: {e}")
                continue

            ch_dir_path = os.path.join(book_path, "chapters")
            if os.path.isdir(ch_dir_path):
                for ch_slug in os.listdir(ch_dir_path):
                    ch_path = os.path.join(ch_dir_path, ch_slug)
                    if not os.path.isdir(ch_path):
                        continue
                    ch_json = _read_json(os.path.join(ch_path, "chapter.json"))
                    if not ch_json:
                        continue
                    try:
                        remote_ch = api.get_chapter(ch_json["id"])
                        if ch_json.get("description", "") != remote_ch.get("description", ""):
                            api.update_chapter(ch_json["id"], description=ch_json.get("description", ""))
                            print(f"  Updated chapter: {ch_json['name']}")
                    except Exception:
                        pass
                    _sync_pages_dir(os.path.join(ch_path, "pages"), book_json, ch_json)
            _sync_pages_dir(os.path.join(book_path, "pages"), book_json, None)

    print("Push complete.")


def _sync_pages_dir(pages_dir, book_json, ch_json):
    if not os.path.isdir(pages_dir):
        return
    for fname in os.listdir(pages_dir):
        if not fname.endswith(".md"):
            continue
        page_slug = fname[:-3]
        local_md = _read_md(os.path.join(pages_dir, fname))
        if local_md is None:
            continue
        try:
            remote_pages = api.list_pages(book_id=book_json["id"])
        except Exception:
            continue
        matching = [p for p in remote_pages if p["slug"] == page_slug]
        if matching:
            try:
                remote_page = api.get_page(matching[0]["id"])
                remote_md = remote_page.get("markdown") or remote_page.get("html", "")
                if remote_md != local_md:
                    api.update_page(matching[0]["id"], markdown=local_md)
                    print(f"  Updated page: {matching[0]['name']}")
            except Exception:
                pass
        else:
            name = _guess_name(local_md, page_slug)
            kw = {"book_id": book_json["id"], "name": name, "markdown": local_md}
            if ch_json:
                kw["chapter_id"] = ch_json["id"]
            try:
                api.create_page(**kw)
                print(f"  Created page: {name}")
            except Exception as e:
                print(f"  Failed to create page '{name}': {e}")


def _guess_name(md, fallback):
    lines = md.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").title()


def cmd_status():
    shelves_dir = os.path.join(LOCAL_DIR, "shelves")
    if not os.path.isdir(shelves_dir):
        print("No local data.")
        return
    local_pages = 0
    remote_pages = 0
    for shelf_slug in os.listdir(shelves_dir):
        books_path = os.path.join(shelves_dir, shelf_slug, "books")
        if not os.path.isdir(books_path):
            continue
        for book_slug in os.listdir(books_path):
            book_json = _read_json(os.path.join(books_path, book_slug, "book.json"))
            if not book_json:
                continue
            remote_pages += len(api.list_pages(book_id=book_json["id"]))
            for root, dirs, files in os.walk(os.path.join(books_path, book_slug)):
                for f in files:
                    if f.endswith(".md"):
                        local_pages += 1
    print(f"  Local:  {local_pages} pages")
    print(f"  Remote: {remote_pages} pages")
    diff = local_pages - remote_pages
    if diff == 0:
        print("  Status: SYNCED")
    elif diff > 0:
        print(f"  Status: {diff} local only (run 'push')")
    else:
        print(f"  Status: {-diff} remote only (run 'pull')")


if __name__ == "__main__":
    cmds = {"init": cmd_init, "pull": cmd_pull, "push": cmd_push, "status": cmd_status}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(f"Usage: python -m tools.bookstack.sync <{'|'.join(cmds)}>")
        sys.exit(1)
    cmds[sys.argv[1]]()

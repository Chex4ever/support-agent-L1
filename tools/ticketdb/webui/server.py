import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import database as db

HERE = Path(__file__).parent
BOOKSTACK_LOCAL = HERE.parent.parent.parent / "bookstack_local"
PROJECT_ROOT = HERE.parent.parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Omnigent WebUI", lifespan=lifespan)
templates = Jinja2Templates(directory=str(HERE / "templates"))
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


def _redirect(url: str, msg: str = None):
    if msg:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}msg={quote(msg)}"
    return RedirectResponse(url, status_code=303)


# ── Dashboard ───────────────────────────────────────────

@app.get("/")
def index(request: Request):
    tickets = db.list_tickets()
    kb_entries = db.list_kb()
    stats = {
        "total": len(tickets),
        "in_progress": sum(1 for t in tickets if t["status"] == "in_progress"),
        "completed": sum(1 for t in tickets if t["status"] == "completed"),
        "pending": sum(1 for t in tickets if t["status"] == "pending"),
        "blocked": sum(1 for t in tickets if t["status"] == "blocked"),
        "cancelled": sum(1 for t in tickets if t["status"] == "cancelled"),
        "kb": len(kb_entries),
        "products": len(set(t["product"] for t in tickets if t["product"])),
    }
    recent = tickets[:10]
    return templates.TemplateResponse(request, "index.html", {
        "stats": stats, "recent": recent, "page": "dashboard",
    })


# ── Tickets ─────────────────────────────────────────────

@app.get("/tickets")
def tickets_list(
    request: Request,
    status: str = None,
    product: str = None,
    search: str = None,
    msg: str = None,
):
    rows = db.list_tickets(status=status, product=product, search=search)
    categories = _get_ticket_statuses()
    products = _get_ticket_products()
    return templates.TemplateResponse(request, "tickets_list.html", {
        "tickets": rows, "current_status": status, "current_product": product,
        "current_search": search, "categories": categories, "products": products,
        "msg": msg, "page": "tickets",
    })


@app.get("/tickets/new")
def ticket_new_form(request: Request):
    return templates.TemplateResponse(request, "ticket_form.html", {
        "ticket": None, "page": "tickets",
    })


@app.post("/tickets/new")
def ticket_new_create(
    request: Request,
    ticket_id: str = Form(...),
    status: str = Form("pending"),
    priority: str = Form("medium"),
    product: str = Form(""),
    client_name: str = Form(""),
    summary: str = Form(""),
    client_question: str = Form(""),
    research_summary: str = Form(""),
    notes: str = Form(""),
):
    existing = db.get_ticket(ticket_id)
    if existing:
        return templates.TemplateResponse(request, "ticket_form.html", {
            "ticket": None, "error": f"Ticket '{ticket_id}' already exists.", "page": "tickets",
        })
    db.create_ticket(
        ticket_id=ticket_id, status=status, priority=priority, product=product,
        client_name=client_name, summary=summary, client_question=client_question,
        research_summary=research_summary, notes=notes,
    )
    return _redirect(f"/tickets/{quote(ticket_id)}", msg="Ticket created")


@app.get("/tickets/{ticket_id}")
def ticket_detail(request: Request, ticket_id: str, msg: str = None):
    t = db.get_ticket(ticket_id)
    if not t:
        return templates.TemplateResponse(request, "404.html", {
            "message": f"Ticket '{ticket_id}' not found.",
        }, status_code=404)
    return templates.TemplateResponse(request, "ticket_detail.html", {
        "t": t, "msg": msg, "page": "tickets",
    })


@app.get("/tickets/{ticket_id}/edit")
def ticket_edit_form(request: Request, ticket_id: str):
    t = db.get_ticket(ticket_id)
    if not t:
        return templates.TemplateResponse(request, "404.html", {
            "message": f"Ticket '{ticket_id}' not found.",
        }, status_code=404)
    return templates.TemplateResponse(request, "ticket_form.html", {
        "ticket": t, "page": "tickets",
    })


@app.post("/tickets/{ticket_id}/edit")
def ticket_edit_update(
    request: Request,
    ticket_id: str,
    status: str = Form(...),
    priority: str = Form(...),
    product: str = Form(""),
    client_name: str = Form(""),
    summary: str = Form(""),
    client_question: str = Form(""),
    research_summary: str = Form(""),
    reply_draft_path: str = Form(""),
    reply_sent: int = Form(0),
    notes: str = Form(""),
):
    db.update_ticket(
        ticket_id, status=status, priority=priority, product=product,
        client_name=client_name, summary=summary, client_question=client_question,
        research_summary=research_summary, reply_draft_path=reply_draft_path,
        reply_sent=reply_sent, notes=notes,
    )
    return _redirect(f"/tickets/{quote(ticket_id)}", msg="Ticket updated")


@app.post("/tickets/{ticket_id}/delete")
def ticket_delete(ticket_id: str):
    db.delete_ticket(ticket_id)
    return _redirect("/tickets", msg=f"Ticket '{ticket_id}' deleted")


# ── KB (old TicketDB KB) ────────────────────────────────

@app.get("/kb")
def kb_list(
    request: Request,
    category: str = None,
    search: str = None,
    msg: str = None,
):
    rows = db.list_kb(category=category, search=search)
    categories = db.list_kb_categories()
    return templates.TemplateResponse(request, "kb_list.html", {
        "entries": rows, "current_category": category, "current_search": search,
        "categories": categories, "msg": msg, "page": "kb",
    })


@app.get("/kb/new")
def kb_new_form(request: Request):
    categories = db.list_kb_categories()
    return templates.TemplateResponse(request, "kb_form.html", {
        "entry": None, "all_categories": categories, "page": "kb",
    })


@app.post("/kb/new")
def kb_new_create(
    request: Request,
    category: str = Form(...),
    key: str = Form(...),
    value: str = Form(""),
    source: str = Form(""),
):
    existing = db.create_kb(category=category, key=key, value=value, source=source)
    if not existing:
        categories = db.list_kb_categories()
        return templates.TemplateResponse(request, "kb_form.html", {
            "entry": None, "error": f"KB entry '{category}/{key}' already exists.",
            "all_categories": categories, "page": "kb",
        })
    return _redirect(f"/kb/{existing['id']}", msg="KB entry created")


@app.get("/kb/{kb_id}")
def kb_detail(request: Request, kb_id: int, msg: str = None):
    entry = db.get_kb(kb_id)
    if not entry:
        return templates.TemplateResponse(request, "404.html", {
            "message": f"KB entry #{kb_id} not found.",
        }, status_code=404)
    return templates.TemplateResponse(request, "kb_detail.html", {
        "entry": entry, "msg": msg, "page": "kb",
    })


@app.get("/kb/{kb_id}/edit")
def kb_edit_form(request: Request, kb_id: int):
    entry = db.get_kb(kb_id)
    if not entry:
        return templates.TemplateResponse(request, "404.html", {
            "message": f"KB entry #{kb_id} not found.",
        }, status_code=404)
    categories = db.list_kb_categories()
    return templates.TemplateResponse(request, "kb_form.html", {
        "entry": entry, "all_categories": categories, "page": "kb",
    })


@app.post("/kb/{kb_id}/edit")
def kb_edit_update(
    request: Request,
    kb_id: int,
    category: str = Form(...),
    key: str = Form(...),
    value: str = Form(""),
    source: str = Form(""),
):
    db.update_kb(kb_id, category=category, key=key, value=value, source=source)
    return _redirect(f"/kb/{kb_id}", msg="KB entry updated")


@app.post("/kb/{kb_id}/delete")
def kb_delete(kb_id: int):
    db.delete_kb(kb_id)
    return _redirect("/kb", msg=f"KB entry #{kb_id} deleted")


# ── BookStack KB Viewer ─────────────────────────────────

_BSL = Path(BOOKSTACK_LOCAL)


def _read_json_rel(path):
    p = _BSL / path
    if not p.is_file():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _read_md_rel(path):
    p = _BSL / path
    if not p.is_file():
        return None
    with open(p, encoding="utf-8") as f:
        return f.read()


def _build_tree():
    """Build full tree of shelves -> books -> chapters -> pages with sync status."""
    tree = []
    shelves_dir = _BSL / "shelves"
    if not shelves_dir.is_dir():
        return tree
    for shelf_slug in sorted(os.listdir(str(shelves_dir))):
        sd = shelves_dir / shelf_slug
        if not sd.is_dir():
            continue
        shelf_json = _read_json_rel(f"shelves/{shelf_slug}/shelf.json")
        shelf_name = shelf_json["name"] if shelf_json else shelf_slug

        books_path = sd / "books"
        books = []
        if books_path.is_dir():
            for book_slug in sorted(os.listdir(str(books_path))):
                bd = books_path / book_slug
                if not bd.is_dir():
                    continue
                book_json = _read_json_rel(f"shelves/{shelf_slug}/books/{book_slug}/book.json")
                book_name = book_json["name"] if book_json else book_slug

                # Pre-fetch remote pages for this book (cached)
                remote_pages = _get_remote_pages_for_book(book_slug)

                chapters = []
                ch_dir = bd / "chapters"
                if ch_dir.is_dir():
                    for ch_slug in sorted(os.listdir(str(ch_dir))):
                        ch_path = ch_dir / ch_slug
                        if not ch_path.is_dir():
                            continue
                        ch_json = _read_json_rel(
                            f"shelves/{shelf_slug}/books/{book_slug}/chapters/{ch_slug}/chapter.json"
                        )
                        ch_name = ch_json["name"] if ch_json else ch_slug

                        pages = []
                        p_dir = ch_path / "pages"
                        if p_dir.is_dir():
                            for md_file in sorted(os.listdir(str(p_dir))):
                                if md_file.endswith(".md"):
                                    page_slug = md_file[:-3]
                                    remote_info = remote_pages.get(page_slug)
                                    if remote_info:
                                        pages.append({
                                            "name": _page_title(
                                                _read_md_rel(
                                                    f"shelves/{shelf_slug}/books/{book_slug}/"
                                                    f"chapters/{ch_slug}/pages/{md_file}"
                                                ), page_slug
                                            ),
                                            "slug": page_slug,
                                            "path": f"shelves/{shelf_slug}/books/{book_slug}/"
                                                    f"chapters/{ch_slug}/pages/{md_file}",
                                            "sync_status": "remote_exists",
                                        })
                                    else:
                                        pages.append({
                                            "name": _page_title(
                                                _read_md_rel(
                                                    f"shelves/{shelf_slug}/books/{book_slug}/"
                                                    f"chapters/{ch_slug}/pages/{md_file}"
                                                ), page_slug
                                            ),
                                            "slug": page_slug,
                                            "path": f"shelves/{shelf_slug}/books/{book_slug}/"
                                                    f"chapters/{ch_slug}/pages/{md_file}",
                                            "sync_status": "local_only",
                                        })
                        chapters.append({"slug": ch_slug, "name": ch_name, "pages": pages})

                standalone_pages = []
                p_dir = bd / "pages"
                if p_dir.is_dir():
                    for md_file in sorted(os.listdir(str(p_dir))):
                        if md_file.endswith(".md"):
                            page_slug = md_file[:-3]
                            remote_info = remote_pages.get(page_slug)
                            if remote_info:
                                standalone_pages.append({
                                    "name": _page_title(
                                        _read_md_rel(f"shelves/{shelf_slug}/books/{book_slug}/pages/{md_file}"),
                                        page_slug,
                                    ),
                                    "slug": page_slug,
                                    "path": f"shelves/{shelf_slug}/books/{book_slug}/pages/{md_file}",
                                    "sync_status": "remote_exists",
                                })
                            else:
                                standalone_pages.append({
                                    "name": _page_title(
                                        _read_md_rel(f"shelves/{shelf_slug}/books/{book_slug}/pages/{md_file}"),
                                        page_slug,
                                    ),
                                    "slug": page_slug,
                                    "path": f"shelves/{shelf_slug}/books/{book_slug}/pages/{md_file}",
                                    "sync_status": "local_only",
                                })

                books.append({
                    "slug": book_slug, "name": book_name,
                    "chapters": chapters, "pages": standalone_pages,
                })

        tree.append({"slug": shelf_slug, "name": shelf_name, "books": books})
    return tree


def _page_title(md_content, fallback_slug):
    if not md_content:
        return fallback_slug.replace("-", " ").title()
    for line in md_content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback_slug.replace("-", " ").title()


def _md_to_html(md):
    """Minimal markdown → HTML for safe display."""
    html = ""
    for line in md.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("# "):
            html += f"<h3>{_escape(line_stripped[2:])}</h3>\n"
        elif line_stripped.startswith("## "):
            html += f"<h4>{_escape(line_stripped[3:])}</h4>\n"
        elif line_stripped.startswith("### "):
            html += f"<h5>{_escape(line_stripped[4:])}</h5>\n"
        elif line_stripped.startswith("---"):
            html += "<hr>\n"
        elif line_stripped.startswith("**") and line_stripped.endswith("**"):
            html += f"<p><strong>{_escape(line_stripped[2:-2])}</strong></p>\n"
        elif line_stripped.startswith("> "):
            html += f"<blockquote>{_escape(line_stripped[2:])}</blockquote>\n"
        elif line_stripped == "":
            html += "<br>\n"
        else:
            # inline bold/italic/code
            text = _escape(line)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            html += f"<p>{text}</p>\n"
    return html


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _run_sync(command):
    """Run a bookstack sync command and return output."""
    cmd = [sys.executable, "-m", "tools.bookstack.sync", command]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired as e:
        return f"Error: command timed out after 120s"
    except Exception as e:
        return f"Error: {e}"


@app.get("/bookstack")
def bookstack_viewer(request: Request, msg: str = None):
    tree = _build_tree()
    return templates.TemplateResponse(request, "bookstack_viewer.html", {
        "shelves": tree, "msg": msg, "page": "bookstack",
    })


@app.get("/bookstack/page")
def bookstack_page(path: str = Query(...)):
    md = _read_md_rel(path)
    if md is None:
        return HTMLResponse("Page not found", status_code=404)

    # Try to find BookStack URL from book.json
    parts = path.split("/")
    bookstack_url = None
    try:
        if parts[0] == "shelves" and parts[2] == "books":
            book_slug = parts[3]
            book_json = _read_json_rel(f"shelves/{parts[1]}/books/{book_slug}/book.json")
            if book_json:
                page_slug = parts[-1][:-3]  # remove .md
                bookstack_url = f"http://bookstack.mytunnel.org/books/{book_slug}/page/{page_slug}"
    except Exception:
        pass

    return {
        "html": _md_to_html(md),
        "bookstack_url": bookstack_url,
        "raw": md,
    }


@app.post("/bookstack/pull")
def bookstack_pull():
    output = _run_sync("pull")
    return HTMLResponse(output.replace("\n", "<br>"))


@app.post("/bookstack/push")
def bookstack_push():
    output = _run_sync("push")
    return HTMLResponse(output.replace("\n", "<br>"))


@app.post("/bookstack/status")
def bookstack_status():
    output = _run_sync("status")
    return HTMLResponse(output.replace("\n", "<br>"))


# ── BookStack Per-Page Sync ─────────────────────────────

_SYNC_CACHE = {}  # (book_slug, page_slug) -> {"hash": str, "remote_updated": str, "exists": bool}


def _reset_sync_cache():
    _SYNC_CACHE.clear()


def _md5_content(text):
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()


def _get_remote_pages_for_book(book_slug):
    """Get all pages from BookStack for a book. Returns dict slug -> {id, updated_at, md5}."""
    cache_key = f"remote_pages_{book_slug}"
    if cache_key in _SYNC_CACHE:
        return _SYNC_CACHE[cache_key]
    try:
        from tools.bookstack import client as bs
        # Find book id from local data
        for shelf_dir in os.listdir(str(_BSL / "shelves")):
            books_path = _BSL / "shelves" / shelf_dir / "books"
            if not books_path.is_dir():
                continue
            for b_slug in os.listdir(str(books_path)):
                if b_slug == book_slug:
                    bj = _read_json_rel(f"shelves/{shelf_dir}/books/{book_slug}/book.json")
                    if bj and bj.get("id"):
                        raw_pages = bs.list_pages(book_id=bj["id"], count=500)
                        result = {}
                        for p in raw_pages:
                            slug = p.get("slug", "")
                            result[slug] = {
                                "id": p["id"],
                                "updated_at": p.get("updated_at", ""),
                                "book_id": bj["id"],
                            }
                        _SYNC_CACHE[cache_key] = result
                        return result
        _SYNC_CACHE[cache_key] = {}
        return {}
    except Exception as e:
        print(f"  Error fetching remote pages for {book_slug}: {e}")
        _SYNC_CACHE[cache_key] = {}
        return {}


def _get_page_sync_status(local_path):
    """Compute sync status for a single page.
    Returns dict: {status, local_hash, remote_exists, remote_hash, bookstack_url}
    """
    parts = local_path.replace("\\", "/").split("/")
    # Expected: shelves/<shelf>/books/<book>/chapters/<chapter>/pages/<page>.md
    # or: shelves/<shelf>/books/<book>/pages/<page>.md
    page_slug = parts[-1][:-3] if parts[-1].endswith(".md") else parts[-1]
    try:
        shelf_idx = parts.index("shelves")
        shelf_slug = parts[shelf_idx + 1]
        book_slug = parts[shelf_idx + 3]  # shelves/{shelf}/books/{book}
    except (ValueError, IndexError):
        return {"status": "unknown", "local_hash": "", "remote_exists": False}

    local_md = _read_md_rel(local_path)
    local_hash = _md5_content(local_md) if local_md else ""

    remote_pages = _get_remote_pages_for_book(book_slug)
    remote_info = remote_pages.get(page_slug)

    if not remote_info:
        return {
            "status": "local_only",
            "local_hash": local_hash,
            "remote_exists": False,
            "page_slug": page_slug,
            "book_slug": book_slug,
        }

    # Fetch remote content to compare hash
    try:
        from tools.bookstack import client as bs
        remote_page = bs.get_page(remote_info["id"], raw=True)
        remote_md = remote_page.get("markdown") or remote_page.get("html", "")
        remote_hash = _md5_content(remote_md)

        if local_hash == remote_hash:
            status = "synced"
        else:
            status = "local_newer"  # optimistic; we could check updated_at for reverse

        return {
            "status": status,
            "local_hash": local_hash,
            "remote_exists": True,
            "remote_hash": remote_hash,
            "remote_id": remote_info["id"],
            "page_slug": page_slug,
            "book_slug": book_slug,
            "remote_updated": remote_info.get("updated_at", ""),
            "bookstack_url": f"http://bookstack.mytunnel.org/books/{book_slug}/page/{page_slug}",
        }
    except Exception as e:
        return {
            "status": "remote_unreachable",
            "local_hash": local_hash,
            "remote_exists": True,
            "page_slug": page_slug,
            "book_slug": book_slug,
            "error": str(e),
        }


@app.get("/bookstack/page/status")
def bookstack_page_status(path: str = Query(...)):
    """Check sync status for a single page."""
    status = _get_page_sync_status(path)
    return JSONResponse(status)


@app.post("/bookstack/page/push")
def bookstack_page_push(path: str = Query(...)):
    """Push a single page to BookStack (create chapter if needed)."""
    parts = path.replace("\\", "/").split("/")
    try:
        shelf_idx = parts.index("shelves")
        shelf_slug = parts[shelf_idx + 1]
        book_slug = parts[shelf_idx + 3]
        page_slug = parts[-1][:-3]
    except (ValueError, IndexError):
        return HTMLResponse("Invalid path", status_code=400)

    local_md = _read_md_rel(path)
    if local_md is None:
        return HTMLResponse("Local page not found", status_code=404)

    try:
        from tools.bookstack import client as bs

        # Find book id from local data
        book_id = None
        chapter_id = None
        for sd in os.listdir(str(_BSL / "shelves")):
            bp = _BSL / "shelves" / sd / "books" / book_slug
            if bp.is_dir():
                bj = _read_json_rel(f"shelves/{sd}/books/{book_slug}/book.json")
                if bj and bj.get("id"):
                    book_id = bj["id"]
                    break

        if not book_id:
            return HTMLResponse("Book not found locally. Run Pull first.", status_code=400)

        # Check if page is in a chapter
        is_in_chapter = "chapters" in parts
        if is_in_chapter:
            ch_slug = parts[parts.index("chapters") + 1]
            # Check if chapter exists on remote
            remote_chapters = bs.list_chapters(book_id)
            for rc in remote_chapters:
                if rc["slug"] == ch_slug:
                    chapter_id = rc["id"]
                    break
            # Create chapter if not exists
            if not chapter_id:
                ch_path = _BSL / "shelves" / shelf_slug / "books" / book_slug / "chapters" / ch_slug
                ch_json_path = ch_path / "chapter.json"
                if ch_json_path.is_file():
                    with open(ch_json_path, encoding="utf-8") as f:
                        ch_data = json.load(f)
                    new_ch = bs.create_chapter(book_id, name=ch_data.get("name", ch_slug),
                                                description=ch_data.get("description", ""))
                    chapter_id = new_ch["id"]
                    # Update local chapter.json with real id
                    ch_data["id"] = chapter_id
                    ch_data["book_id"] = book_id
                    with open(ch_json_path, "w", encoding="utf-8") as f:
                        json.dump(ch_data, f, ensure_ascii=False, indent=2)
                else:
                    return HTMLResponse("Chapter metadata not found locally", status_code=400)

        # Check if page exists on remote
        remote_pages = _get_remote_pages_for_book(book_slug)
        if page_slug in remote_pages:
            bs.update_page(remote_pages[page_slug]["id"], markdown=local_md)
            msg = f"Page '{page_slug}' updated on BookStack"
        else:
            name = _guess_page_name(local_md, page_slug)
            kwargs = {"book_id": book_id, "name": name, "markdown": local_md}
            if chapter_id:
                kwargs["chapter_id"] = chapter_id
            bs.create_page(**kwargs)
            msg = f"Page '{page_slug}' created on BookStack"

        _reset_sync_cache()
        return HTMLResponse(msg)

    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)


@app.post("/bookstack/page/pull")
def bookstack_page_pull(path: str = Query(...)):
    """Pull a single page from BookStack (overwrite local)."""
    parts = path.replace("\\", "/").split("/")
    try:
        shelf_idx = parts.index("shelves")
        book_slug = parts[shelf_idx + 3]
        page_slug = parts[-1][:-3]
    except (ValueError, IndexError):
        return HTMLResponse("Invalid path", status_code=400)

    remote_pages = _get_remote_pages_for_book(book_slug)
    remote_info = remote_pages.get(page_slug)
    if not remote_info:
        return HTMLResponse("Page not found on BookStack", status_code=404)

    try:
        from tools.bookstack import client as bs
        remote_page = bs.get_page(remote_info["id"], raw=True)
        remote_md = remote_page.get("markdown") or remote_page.get("html", "")

        # Write to local file
        local_file = _BSL / path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(remote_md or "")

        _reset_sync_cache()
        return HTMLResponse(f"Page '{page_slug}' pulled from BookStack")
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)


def _guess_page_name(md, fallback):
    lines = md.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").title()


# ── Helpers ─────────────────────────────────────────────

def _get_ticket_statuses():
    tickets = db.list_tickets()
    seen = set()
    result = []
    for t in tickets:
        s = t["status"]
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def _get_ticket_products():
    tickets = db.list_tickets()
    seen = set()
    result = []
    for t in tickets:
        p = t["product"]
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return sorted(result)

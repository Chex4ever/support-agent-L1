"""
BookStack REST API client.

Endpoints: shelves, books, chapters, pages, search.
Auth: Token <TOKEN_ID>:<TOKEN_SECRET>
"""
import json
import os
import urllib.parse
import urllib.request
import urllib.error

# Try to load .env if env vars not set
if not os.environ.get("BOOKSTACK_BASE_URL"):
    _env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    _env_path = os.path.normpath(_env_path)
    if os.path.isfile(_env_path):
        with open(_env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

BOOKSTACK_URL = os.environ.get("BOOKSTACK_BASE_URL", "")
BOOKSTACK_TOKEN_ID = os.environ.get("BOOKSTACK_TOKEN_ID", "")
BOOKSTACK_TOKEN_SECRET = os.environ.get("BOOKSTACK_TOKEN_SECRET", "")


def _auth_headers():
    return {
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}",
        "Content-Type": "application/json",
    }


def _request(method, path, data=None):
    url = f"{BOOKSTACK_URL}/api/{path.lstrip('/')}"
    headers = _auth_headers()
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {url}: {err}")


# ── Shelves ──

def list_shelves():
    return _request("GET", "shelves")["data"]


def get_shelf(shelf_id):
    return _request("GET", f"shelves/{shelf_id}")


# ── Books ──

def list_books(params=None):
    qs = ""
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return _request("GET", f"books{qs}")["data"]


def get_book(book_id):
    return _request("GET", f"books/{book_id}")


def create_book(name, description="", shelf_id=None):
    data = {"name": name, "description": description}
    if shelf_id:
        data["bookshelf_id"] = shelf_id
    return _request("POST", "books", data)


def update_book(book_id, **kw):
    return _request("PUT", f"books/{book_id}", kw)


# ── Chapters ──

def list_chapters(book_id):
    return _request("GET", f"chapters?book_id={book_id}")["data"]


def get_chapter(chapter_id):
    return _request("GET", f"chapters/{chapter_id}")


def create_chapter(book_id, name, description=""):
    return _request("POST", "chapters", {
        "book_id": book_id, "name": name, "description": description,
    })


def update_chapter(chapter_id, **kw):
    return _request("PUT", f"chapters/{chapter_id}", kw)


# ── Pages ──

def list_pages(book_id=None, chapter_id=None, count=500):
    params = {}
    if book_id:
        params["book_id"] = book_id
    if chapter_id:
        params["chapter_id"] = chapter_id
    params["count"] = count
    qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return _request("GET", f"pages{qs}")["data"]


def get_page(page_id, raw=False):
    path = f"pages/{page_id}"
    if raw:
        path += "?raw=true"
    return _request("GET", path)


def create_page(book_id, name, html="", markdown="", chapter_id=None):
    data = {"book_id": book_id, "name": name}
    if markdown:
        data["markdown"] = markdown
    else:
        data["html"] = html
    if chapter_id:
        data["chapter_id"] = chapter_id
    return _request("POST", "pages", data)


def update_page(page_id, **kw):
    return _request("PUT", f"pages/{page_id}", kw)


# ── Search ──

def search(query, count=20):
    return _request("GET", f"search?query={urllib.parse.quote(query)}&count={count}")

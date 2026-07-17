# Search local wiki copy (synced from dev.iridi.com via wiki-crawler)
# Usage: python -m tools.wiki.search "<query>" [--top N] [--full]
# Example: python -m tools.wiki.search "Server Tags"

import argparse
import json
import os
import re
import sys
from pathlib import Path

WIKI_DATA_DIR = Path(r"C:\iridi\wiki-crawler\iridi-wiki-agent\data")
PAGES_FILE = WIKI_DATA_DIR / "pages.json"
RAW_DIR = WIKI_DATA_DIR / "raw"


def load_pages() -> list[dict]:
    if not PAGES_FILE.exists():
        print(f"Error: {PAGES_FILE} not found. Run wiki sync first.", file=sys.stderr)
        sys.exit(1)
    with open(PAGES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("pages", [])


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", text.lower())


def search(query: str, pages: list[dict], top: int = 10) -> list[tuple[dict, int, str]]:
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return []

    results = []
    for page in pages:
        text = page.get("content", "")
        text_lower = text.lower()
        score = 0
        for token in query_tokens:
            score += text_lower.count(token)
        if score > 0:
            snippet = _make_snippet(text, query_tokens, 300)
            results.append((page, score, snippet))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top]


def _make_snippet(text: str, query_tokens: set[str], max_len: int = 300) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    best_pos = 0
    best_score = 0
    for i in range(0, len(text) - 50, 50):
        window = text_lower[i : i + max_len]
        score = sum(window.count(t) for t in query_tokens)
        if score > best_score:
            best_score = score
            best_pos = i

    start = max(0, best_pos - 30)
    end = min(len(text), best_pos + max_len)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def main():
    parser = argparse.ArgumentParser(description="Search local iRidi wiki")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("--top", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--full", action="store_true", help="Show full page content instead of snippet")
    args = parser.parse_args()

    query = " ".join(args.query)
    pages = load_pages()
    results = search(query, pages, top=args.top)

    if not results:
        print(f"No results found for: {query}")
        return

    print(f"Search: \"{query}\"\n")
    for i, (page, score, snippet) in enumerate(results, 1):
        title = page.get("title", "?")
        url = page.get("url", "")
        cats = page.get("categories", [])

        print(f"--- {i}. {title} (score: {score}) ---")
        if url:
            print(f"URL: {url}")
        if cats:
            print(f"Categories: {', '.join(cats)}")
        print()
        if args.full:
            print(page.get("content", ""))
        else:
            print(snippet)
        print()


if __name__ == "__main__":
    main()

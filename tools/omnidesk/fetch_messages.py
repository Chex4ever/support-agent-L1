# Fetch all messages from an Omnidesk ticket by internal case ID
# Usage: python tools/omnidesk/fetch_messages.py <case_id> [--save path/to/output.json]
# Example: python tools/omnidesk/fetch_messages.py 411928080 --save tickets/422-279121/files/messages.json

import requests, json, sys, os
from requests.auth import HTTPBasicAuth

API_BASE = "https://iridi.omnidesk.ru"
EMAIL = os.getenv("OMNIDESK_STAFF_EMAIL", "")
API_KEY = os.getenv("OMNIDESK_API_KEY", "")

if not EMAIL or not API_KEY:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        EMAIL = os.getenv("OMNIDESK_STAFF_EMAIL", "")
        API_KEY = os.getenv("OMNIDESK_API_KEY", "")
    except ImportError:
        pass

if not EMAIL or not API_KEY:
    sys.exit("Error: Set OMNIDESK_STAFF_EMAIL and OMNIDESK_API_KEY environment variables, or install python-dotenv")

def fetch_messages(case_id, limit=100):
    url = f"{API_BASE}/api/cases/{case_id}/messages.json"
    auth = HTTPBasicAuth(EMAIL, API_KEY)
    r = requests.get(url, auth=auth, params={"limit": limit, "order": "asc"})
    r.raise_for_status()
    return r.json()

def print_summary(data):
    for k, v in data.items():
        if k == "total_count":
            print(f"Total messages: {v}")
            continue
        msg = v.get("message", v) if isinstance(v, dict) else v
        staff_id = msg.get("staff_id", "?")
        user_id = msg.get("user_id", "?")
        created = msg.get("created_at", "?")
        note = msg.get("note", False)
        content = (msg.get("content") or msg.get("content_html", ""))[:300]
        print(f"\n--- Message {k} ---")
        print(f"  staff_id={staff_id} user_id={user_id} note={note}")
        print(f"  created_at: {created}")
        print(f"  content: {content[:200]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/omnidesk/fetch_messages.py <case_id> [--save file.json]")
        sys.exit(1)

    case_id = sys.argv[1]
    data = fetch_messages(case_id)
    print_summary(data)

    if "--save" in sys.argv:
        idx = sys.argv.index("--save")
        if idx + 1 < len(sys.argv):
            path = sys.argv[idx + 1]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\nSaved to {path}")

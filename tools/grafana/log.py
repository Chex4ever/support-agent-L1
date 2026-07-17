"""
Grafana Loki log query tool.

Usage:
  python -m tools.grafana.log <query> [options]

Examples:
  python -m tools.grafana.log --hwid 6953580395ecb8dca7ab6c6f1f4b2c0c487db8 --date 2026-07-02
  python -m tools.grafana.log "{service=\"hub_service\"}" --date 2026-07-02
  python -m tools.grafana.log --hwid 6ad188444f3f4bc8a3ae2a442630a99f --service mauth_backend
  python -m tools.grafana.log --list-services
  python -m tools.grafana.log --list-labels
"""

import argparse, json, os, sys, time, urllib.parse
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    sys.exit("Missing 'requests' library. Run: pip install requests")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_BASE = os.getenv("GRAFANA_URL", "https://grafana.iridi.cloud")
USER = os.getenv("GRAFANA_USER", "")
PASSWORD = os.getenv("GRAFANA_PASSWORD", "")
UID = os.getenv("GRAFANA_LOKI_UID", "lmtix6vMk")

AUTH = (USER, PASSWORD) if USER and PASSWORD else None
SESSION = requests.Session()
if AUTH:
    SESSION.auth = AUTH

LOKI_PROXY = f"{API_BASE}/api/datasources/proxy/uid/{UID}/loki/api/v1"

KNOWN_SERVICES = [
    "apple_mfi", "auth_service", "bus77home_service", "bus77lite_service",
    "byod_backend", "co_backend", "co_backend_1-2", "co_backend_1-2-shields",
    "co_backend_testing", "cws_legrand", "cws_old", "hosts", "hub_service",
    "i3knx_service", "i3pro_service", "iridi_com", "lk_service_back",
    "mauth_backend", "mkd_api", "mkd_bknd", "project_tool_backend", "rdb",
    "supply_service", "uid_storage_service",
]

def ns(dt):
    return int(dt.timestamp() * 1_000_000_000)

def parse_date(s):
    if s == "now":
        return datetime.now(timezone.utc)
    if s.endswith("h"):
        return datetime.now(timezone.utc) - timedelta(hours=int(s[:-1]))
    if s.endswith("d"):
        return datetime.now(timezone.utc) - timedelta(days=int(s[:-1]))
    if "T" in s:
        return datetime.fromisoformat(s)
    return datetime.fromisoformat(f"{s}T00:00:00+03:00")

def fetch_labels():
    r = SESSION.get(f"{LOKI_PROXY}/labels")
    r.raise_for_status()
    return r.json().get("data", [])

def fetch_label_values(label):
    r = SESSION.get(f"{LOKI_PROXY}/label/{label}/values")
    r.raise_for_status()
    return r.json().get("data", [])

def query_range(query, start, end, limit=50, direction="backward"):
    params = {
        "query": query,
        "start": ns(start),
        "end": ns(end),
        "limit": limit,
        "direction": direction,
    }
    r = SESSION.get(f"{LOKI_PROXY}/query_range", params=params)
    r.raise_for_status()
    return r.json()

def print_results(data, show_full=False):
    result = data.get("data", {}).get("result", [])
    if not result:
        print("No results found.")
        return 0

    total = 0
    for stream in result:
        labels = stream.get("stream", {})
        values = stream.get("values", [])
        svc = labels.get("service", "?")
        reg = labels.get("region", "?")
        print(f"\n-- {svc} / {reg} ({len(values)} lines) --")
        for ts, line in values:
            total += 1
            dt = datetime.fromtimestamp(int(ts) / 1_000_000_000, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            if show_full:
                try:
                    parsed = json.loads(line)
                    print(f"\n[{time_str}] {json.dumps(parsed, indent=2, ensure_ascii=False)}")
                except json.JSONDecodeError:
                    print(f"\n[{time_str}] {line}")
            else:
                snippet = line[:300]
                print(f"  [{time_str}] {snippet}")
    print(f"\nTotal: {total} lines")
    return total


def main():
    parser = argparse.ArgumentParser(description="Grafana Loki log query tool")
    parser.add_argument("query", nargs="?", help="LogQL query (e.g. '{service=\"mauth_backend\"}')")
    parser.add_argument("--hwid", help="Search by HWID (builds query automatically)")
    parser.add_argument("--service", help="Filter by service name")
    parser.add_argument("--region", help="Filter by region")
    parser.add_argument("--contains", help="Text search (|= operator)")
    parser.add_argument("--date", help="Date (2026-07-02, 'now', '3h', '7d')")
    parser.add_argument("--start", help="Start datetime (ISO format)")
    parser.add_argument("--end", help="End datetime (ISO format)")
    parser.add_argument("--window", default="1d", help="Time window (e.g. '6h', '2d', '7d')")
    parser.add_argument("--limit", type=int, default=50, help="Max log lines")
    parser.add_argument("--show-full", action="store_true", help="Pretty-print JSON logs")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON")
    parser.add_argument("--list-services", action="store_true", help="List known service names")
    parser.add_argument("--list-labels", action="store_true", help="List available labels")
    parser.add_argument("--list-regions", action="store_true", help="List available region values")

    args = parser.parse_args()

    if not AUTH:
        sys.exit("Error: Set GRAFANA_USER and GRAFANA_PASSWORD in .env")

    if args.list_services:
        print("Known services:")
        for s in KNOWN_SERVICES:
            print(f"  {s}")
        print("\nTo fetch live values, use --list-labels")

        if args.list_labels:
            print("Available labels:")
            for label in sorted(fetch_labels()):
                print(f"  {label}")
        if args.list_regions:
            print("Available region values:")
            for v in fetch_label_values("region"):
                print(f"  {v}")
        return

    if args.list_labels:
        print("Available labels:")
        for label in sorted(fetch_labels()):
            print(f"  {label}")
        return

    if args.list_regions:
        print("Available region values:")
        for v in fetch_label_values("region"):
            print(f"  {v}")
        return

    query = args.query

    if not query and not args.hwid:
        if args.service or args.contains:
            parts = []
            if args.service:
                parts.append(f"{{service=\"{args.service}\"}}")
            else:
                parts.append("{service=~\".+\"}")
            if args.contains:
                parts.append(f"|= \"{args.contains}\"")
            query = " ".join(parts)

    if args.hwid:
        parts = []
        if args.service:
            parts.append(f"{{service=\"{args.service}\"}}")
        else:
            svcs = "|".join(KNOWN_SERVICES)
            parts.append(f"{{service=~\"{svcs}\"}}")
        parts.append(f'|= "{args.hwid}"')
        if args.contains:
            parts.append(f'|= "{args.contains}"')
        query = " ".join(parts)

    if not query:
        parser.print_help()
        sys.exit(1)

    if args.date:
        dt = parse_date(args.date)
        start = dt
        end = dt + timedelta(days=1)
    elif args.start and args.end:
        start = parse_date(args.start)
        end = parse_date(args.end)
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=1) if args.window == "1d" else end - parse_window(args.window)

    print(f"Query: {query}")
    print(f"Range: {start.isoformat()} -> {end.isoformat()}")
    print(f"Limit: {args.limit}\n")

    try:
        data = query_range(query, start, end, args.limit)
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)

    if args.raw:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_results(data, show_full=args.show_full)


def parse_window(s):
    unit = s[-1]
    val = int(s[:-1])
    if unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    else:
        return timedelta(days=1)


if __name__ == "__main__":
    main()

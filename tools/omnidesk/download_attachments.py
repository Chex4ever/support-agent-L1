"""
Download all attachments and inline images from an Omnidesk ticket.

Usage:
    python tools/omnidesk/download_attachments.py <case_id> [--outdir DIR] [--ocr]

Arguments:
    case_id     Internal Omnidesk case ID (numeric)
    --outdir    Output directory (default: tickets/<case_number>/files/)
    --ocr       Run OCR on downloaded images using tools/image/ocr.py

Examples:
    python tools/omnidesk/download_attachments.py 412362288
    python tools/omnidesk/download_attachments.py 412362288 --ocr
    python tools/omnidesk/download_attachments.py 412362288 --outdir my_folder
"""

import argparse
import os
import re
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agent.omnidesk_api import get_ticket, get_messages
from web.config import OMNIDESK_API_KEY, OMNIDESK_STAFF_EMAIL


def _auth():
    if OMNIDESK_API_KEY and OMNIDESK_STAFF_EMAIL:
        return HTTPBasicAuth(OMNIDESK_STAFF_EMAIL, OMNIDESK_API_KEY)
    return HTTPBasicAuth("k.boltovskij@iridi.tech", "a87bdc0bdd5442e1b1d31841c")


def download_attachments(case_id: int, outdir: Path, run_ocr: bool = False):
    ticket = get_ticket(case_id)
    if not ticket:
        print(f"ERROR: ticket {case_id} not found")
        sys.exit(1)

    case_number = ticket.case_number or str(case_id)
    if not outdir:
        outdir = Path("tickets") / case_number / "files"

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    messages = get_messages(case_id, limit=200)
    print(f"Ticket: {case_number} (internal ID: {case_id})")
    print(f"Messages: {len(messages)}")
    print(f"Output: {outdir.resolve()}\n")

    auth = _auth()
    downloaded = []
    ocr_results = []

    for i, msg in enumerate(messages):
        msg_id = msg.get("id", f"msg{i+1}")
        content = msg.get("content", "") or ""
        msg_prefix = f"M#{i+1}"

        # Download inline images
        img_urls = re.findall(r'<img[^>]+src="([^"]+)"', content)
        img_urls += re.findall(r"<img[^>]+src='([^']+)'", content)

        for idx, url in enumerate(img_urls, 1):
            if "omnidesk" not in url and "/attachment/" not in url:
                continue
            try:
                r = requests.get(url, auth=auth, timeout=30)
                ext = Path(url).suffix or ".png"
                fname = f"{msg_prefix}_inline_{idx}{ext}"
                path = outdir / fname
                counter = 1
                while path.exists():
                    stem = path.stem
                    suffix = path.suffix
                    path = outdir / f"{stem}_{counter}{suffix}"
                    counter += 1
                with open(path, "wb") as f:
                    f.write(r.content)
                print(f"  [INLINE] {path.name} ({len(r.content)} bytes)")
                downloaded.append((str(path), path.name))
            except Exception as e:
                print(f"  [INLINE FAIL] {url[:60]}: {e}")

        # Download file attachments
        for att in msg.get("attachments", []):
            fname = att.get("file_name", f"attachment_{msg_id}")
            furl = att.get("url", "")
            if not furl:
                continue
            try:
                r = requests.get(furl, auth=auth, timeout=30)
                # Avoid duplicates
                path = outdir / fname
                counter = 1
                while path.exists():
                    stem = path.stem
                    suffix = path.suffix
                    path = outdir / f"{stem}_{counter}{suffix}"
                    counter += 1
                with open(path, "wb") as f:
                    f.write(r.content)
                print(f"  [ATTACH] {path.name} ({len(r.content)} bytes)")
                downloaded.append((str(path), path.name))
            except Exception as e:
                print(f"  [ATTACH FAIL] {fname}: {e}")

    print(f"\nDownloaded: {len(downloaded)} file(s)")

    # Run OCR on images if requested
    if run_ocr:
        _run_ocr_on_images(outdir, downloaded)


def _run_ocr_on_images(outdir: Path, downloaded: list):
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
    ocr_script = Path(__file__).resolve().parents[1] / "image" / "ocr.py"

    if not ocr_script.exists():
        print(f"WARNING: OCR tool not found at {ocr_script}")
        return

    print(f"\nRunning OCR on images...")
    for path_str, fname in downloaded:
        ext = Path(fname).suffix.lower()
        if ext not in image_exts:
            continue
        if os.path.getsize(path_str) < 1000:
            continue  # skip tiny images (likely icons/decoration)

        # Determine pipeline: screenshot for direct captures, monitor for photos
        size = os.path.getsize(path_str)
        if size > 200000:
            pipeline = "monitor"
        else:
            pipeline = "screenshot"

        out_txt = outdir / f"ocr_{Path(fname).stem}.txt"
        if out_txt.exists():
            print(f"  SKIP (exists): {out_txt.name}")
            continue

        cmd = f'python "{ocr_script}" "{path_str}" -p {pipeline} -l rus+eng'
        print(f"  OCR: {fname} ({pipeline})...")
        import subprocess
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n--- STDERR ---\n")
                    f.write(result.stderr)
            print(f"    -> {out_txt.name}")
        except subprocess.TimeoutExpired:
            print(f"    -> TIMEOUT")
        except Exception as e:
            print(f"    -> ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Download Omnidesk ticket attachments")
    parser.add_argument("case_id", type=int, help="Internal Omnidesk case ID")
    parser.add_argument("--outdir", help="Output directory (default: tickets/<case_number>/files/)")
    parser.add_argument("--ocr", action="store_true", help="Run OCR on downloaded images")
    args = parser.parse_args()

    download_attachments(args.case_id, Path(args.outdir) if args.outdir else None, args.ocr)


if __name__ == "__main__":
    main()

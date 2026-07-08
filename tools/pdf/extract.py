#!/usr/bin/env python3
"""
Extract text from PDF files.
Falls back to OCR via tools/image/ocr.py if the PDF has no extractable text.

Usage:
    python tools/pdf/extract.py path/to/file.pdf
    python tools/pdf/extract.py path/to/file.pdf -o output.txt
    python tools/pdf/extract.py path/to/file.pdf --ocr-only
    python tools/pdf/extract.py path/to/file.pdf --debug
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_text_via_fitz(pdf_path: str) -> tuple[str, bool]:
    """Extract text using PyMuPDF (fitz). Returns (text, has_any_text)."""
    import fitz

    doc = fitz.open(pdf_path)
    parts: list[str] = []
    total_chars = 0
    for i, page in enumerate(doc):
        text = page.get_text() or ""
        parts.append(f"--- Page {i + 1} ---\n{text}")
        total_chars += len(text.strip())
    doc.close()
    result = "\n\n".join(parts)
    return result, total_chars > 20


def extract_text_via_ocr(pdf_path: str, pipeline: str = "screenshot", languages: str = "rus+eng", debug: bool = False) -> str:
    """Convert PDF pages to images and run OCR on each page."""
    ocr_script = Path(__file__).resolve().parents[1] / "image" / "ocr.py"
    if not ocr_script.exists():
        return f"ERROR: OCR tool not found at {ocr_script}"

    import fitz
    doc = fitz.open(pdf_path)

    out_dir = Path(pdf_path).parent
    parts: list[str] = []
    page_images: list[str] = []

    for i, page in enumerate(doc):
        # Render page to image at 300 DPI
        pix = page.get_pixmap(dpi=300)
        img_path = os.path.join(tempfile.gettempdir(), f"_pdf_page_{i}_{os.getpid()}.png")
        pix.save(img_path)
        page_images.append(img_path)
    doc.close()

    for i, img_path in enumerate(page_images):
        cmd = [
            sys.executable, str(ocr_script), img_path,
            "-p", pipeline,
            "-l", languages,
        ]
        if debug:
            print(f"  OCR page {i + 1}/{len(page_images)} ...", file=sys.stderr)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            text = result.stdout or ""
            # If stdout is empty but there's stderr with OCR result, try extracting
            if not text.strip() and result.stderr:
                text = result.stderr
            parts.append(f"--- Page {i + 1} (OCR) ---\n{text.strip()}")
        except subprocess.TimeoutExpired:
            parts.append(f"--- Page {i + 1} (OCR) ---\n[OCR TIMEOUT]")
        except Exception as e:
            parts.append(f"--- Page {i + 1} (OCR) ---\n[OCR ERROR: {e}]")
        finally:
            # Cleanup temp file
            try:
                os.unlink(img_path)
            except OSError:
                pass

    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF files")
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("-o", "--output", help="Save output to file instead of stdout")
    parser.add_argument("--ocr-only", action="store_true", help="Skip text extraction, force OCR")
    parser.add_argument("--ocr-fallback", action="store_true", default=True, help="Fall back to OCR if text extraction yields little content (default: True)")
    parser.add_argument("--no-ocr-fallback", action="store_true", help="Disable OCR fallback")
    parser.add_argument("-p", "--pipeline", choices=["monitor", "screenshot", "document", "auto"], default="document", help="OCR pipeline (default: document)")
    parser.add_argument("-l", "--languages", default="rus+eng", help="OCR languages (default: rus+eng)")
    parser.add_argument("--debug", action="store_true", help="Print debug info to stderr")
    args = parser.parse_args()

    pdf_path = args.pdf
    if not os.path.isfile(pdf_path):
        print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output: str | None = None

    # Step 1: Try text extraction
    if not args.ocr_only:
        if args.debug:
            print(f"Extracting text from {pdf_path} ...", file=sys.stderr)
        text, has_text = extract_text_via_fitz(pdf_path)
        if has_text:
            if args.debug:
                text_len = len(text.strip())
                print(f"  Text extracted: {text_len} chars", file=sys.stderr)
            output = text
        elif args.debug:
            print("  No extractable text found.", file=sys.stderr)

    # Step 2: OCR fallback
    if output is None and not args.no_ocr_fallback:
        if args.debug:
            print(f"Falling back to OCR (pipeline={args.pipeline}, lang={args.languages}) ...", file=sys.stderr)
        output = extract_text_via_ocr(pdf_path, args.pipeline, args.languages, args.debug)

    if output is None:
        output = "ERROR: No text could be extracted from the PDF."

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        if args.debug:
            print(f"Saved to {args.output}", file=sys.stderr)
    else:
        # Print to stdout — wrap in try/except for encoding issues
        try:
            print(output)
        except UnicodeEncodeError:
            safe = output.encode("utf-8", errors="replace").decode("cp1251", errors="replace")
            print(safe)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
OCR tool for extracting text from images — especially photos of monitors
attached to support tickets. Supports Tesseract and EasyOCR with multiple
preprocessing pipelines optimised for different image types.

Usage:
    python tools/image/ocr.py path/to/image.jpg -p monitor -l rus+eng --debug
    python tools/image/ocr.py path/to/screenshot.png -p screenshot -o output.txt
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Optional dependency imports  (graceful degradation throughout)
# ---------------------------------------------------------------------------

try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import numpy as np

    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ---- OCR engines ---------------------------------------------------------

TESSERACT_AVAILABLE = False
try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    pass

EASYOCR_AVAILABLE = False
try:
    import easyocr

    EASYOCR_AVAILABLE = True
except ImportError:
    pass

REQUESTS_AVAILABLE = False
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TESSERACT_COMMON_PATHS: list[str] = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]

SUPPORTED_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff",
    ".bmp", ".webp", ".pnm", ".ppm",
}

DEFAULT_LANG = "rus+eng"
DEFAULT_UPSCALE = 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eprint(*args, **kwargs) -> None:
    """Print to stderr (progress / diagnostics, never text output)."""
    print(*args, file=sys.stderr, **kwargs)


def _check_image(path: str) -> Path:
    """Validate that *path* exists, is a file, and has a supported extension.

    Returns a :class:`Path` on success, exits on failure.
    """
    p = Path(path)
    if not p.exists():
        sys.exit(f"Error: file not found — {path}")
    if not p.is_file():
        sys.exit(f"Error: not a file — {path}")
    suff = p.suffix.lower()
    if suff not in SUPPORTED_EXTENSIONS:
        _eprint(f"Warning: unsupported extension '{suff}' — attempting anyway")
    return p


def _configure_tesseract() -> None:
    """Locate the tesseract binary and set ``pytesseract.pytesseract.tesseract_cmd``."""
    import pytesseract as pt

    if pt.pytesseract.tesseract_cmd != "tesseract":
        tesseract_cmd = pt.pytesseract.tesseract_cmd
        if os.path.exists(tesseract_cmd):
            return
    for candidate in map(Path, TESSERACT_COMMON_PATHS):
        if candidate.exists():
            pt.pytesseract.tesseract_cmd = str(candidate)
            _eprint(f"Tesseract found at: {candidate}")
            return
    _eprint("Tesseract binary not found at any common location; falling back to EasyOCR.")


def _detect_auto_mode(img) -> str:
    """Heuristic: large uniform coloured areas -> 'monitor', else 'screenshot'."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    total = h * w

    # Edge density
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = cv2.countNonZero(edges) / total

    # Uniform region ratio  (pixels with std-dev in 32x32 block < 10)
    uniform = 0
    blocks = 0
    for y in range(0, h - 32, 32):
        for x in range(0, w - 32, 32):
            block = gray[y : y + 32, x : x + 32]
            if np.std(block) < 10:
                uniform += 1
            blocks += 1
    uniform_ratio = uniform / max(blocks, 1)

    # Photos of monitors typically have large uniform regions + edges from bezel
    if uniform_ratio > 0.15 and edge_ratio > 0.05:
        return "monitor"
    if edge_ratio < 0.02:
        return "screenshot"
    return "document"


# ---------------------------------------------------------------------------
# Preprocessing pipelines
# ---------------------------------------------------------------------------


def _upscale(img, factor: float, interpolation=None):
    """Resize image by *factor* using INTER_CUBIC (default) or provided interpolation."""
    if interpolation is None:
        interpolation = cv2.INTER_CUBIC
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * factor), int(h * factor)), interpolation=interpolation)


def _sharpening_kernel() -> np.ndarray:
    """Return a 3x3 sharpening kernel."""
    return np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)


def _save_debug(prefix: str, stage: str, img, debug_dir: str) -> None:
    """Write *img* to ``debug_dir/prefix_stage.png`` for visual debugging."""
    os.makedirs(debug_dir, exist_ok=True)
    safe = stage.replace(" ", "_").lower()
    path = os.path.join(debug_dir, f"{prefix}_{safe}.png")
    cv2.imwrite(path, img)
    _eprint(f"  [debug] saved {path}")


# ...........................................................................


def preprocess_monitor(
    img, upscale_factor: float = DEFAULT_UPSCALE, debug_dir: str | None = None
) -> np.ndarray:
    """Pipeline for photos of monitors:

    1. Grayscale  2. CLAHE  3. Gaussian blur  4. Adaptive threshold (Gaussian)
    5. Morphological close  6. Bilateral filter  7. Upscale  8. Sharpen.
    """
    prefix = "monitor"

    # 1 — Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if debug_dir:
        _save_debug(prefix, "1_grayscale", gray, debug_dir)

    # 2 — CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    if debug_dir:
        _save_debug(prefix, "2_clahe", enhanced, debug_dir)

    # 3 — Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    if debug_dir:
        _save_debug(prefix, "3_gaussian_blur", blurred, debug_dir)

    # 4 — Adaptive thresholding (Gaussian method)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    if debug_dir:
        _save_debug(prefix, "4_adaptive_thresh", thresh, debug_dir)

    # 5 — Morphological close to connect broken text fragments
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    if debug_dir:
        _save_debug(prefix, "5_morph_close", closed, debug_dir)

    # 6 — Bilateral filter (smooths, preserves edges)
    bilateral = cv2.bilateralFilter(closed, 9, 75, 75)
    if debug_dir:
        _save_debug(prefix, "6_bilateral", bilateral, debug_dir)

    # 7 — Upscale
    upscaled = _upscale(bilateral, upscale_factor)
    if debug_dir:
        _save_debug(prefix, "7_upscaled", upscaled, debug_dir)

    # 8 — Sharpen
    sharpened = cv2.filter2D(upscaled, -1, _sharpening_kernel())
    if debug_dir:
        _save_debug(prefix, "8_sharpened", sharpened, debug_dir)

    return sharpened


def preprocess_screenshot(
    img, upscale_factor: float = DEFAULT_UPSCALE, debug_dir: str | None = None
) -> np.ndarray:
    """Simple pipeline for clean screenshots: grayscale + threshold + denoise."""
    prefix = "screenshot"
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if debug_dir:
        _save_debug(prefix, "1_grayscale", gray, debug_dir)

    # Threshold (binary inverse works well for light-on-dark; Otsu picks the
    # threshold automatically)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if debug_dir:
        _save_debug(prefix, "2_threshold", thresh, debug_dir)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh, h=30)
    if debug_dir:
        _save_debug(prefix, "3_denoised", denoised, debug_dir)

    upscaled = _upscale(denoised, upscale_factor)
    if debug_dir:
        _save_debug(prefix, "4_upscaled", upscaled, debug_dir)

    return upscaled


def preprocess_document(
    img, upscale_factor: float = DEFAULT_UPSCALE, debug_dir: str | None = None
) -> np.ndarray:
    """Aggressive pipeline for scanned documents: grayscale, deskew, threshold, etc."""
    prefix = "document"
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if debug_dir:
        _save_debug(prefix, "1_grayscale", gray, debug_dir)

    # Deskew
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) > 0.5:
        h, w = gray.shape
        center = (w // 2, h // 2)
        rot = cv2.getRotationMatrix2D(center, angle, 1.0)
        gray = cv2.warpAffine(
            gray, rot, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        if debug_dir:
            _save_debug(prefix, "2_deskewed", gray, debug_dir)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    if debug_dir:
        _save_debug(prefix, "3_clahe", enhanced, debug_dir)

    # Binarize with Otsu
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if debug_dir:
        _save_debug(prefix, "4_otsu", thresh, debug_dir)

    # Morph close to fill small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    if debug_dir:
        _save_debug(prefix, "5_morph_close", cleaned, debug_dir)

    upscaled = _upscale(cleaned, upscale_factor)
    if debug_dir:
        _save_debug(prefix, "6_upscaled", upscaled, debug_dir)

    return upscaled


# ---------------------------------------------------------------------------
# Screen region detection  (bonus: perspective correction for monitor photos)
# ---------------------------------------------------------------------------


def detect_screen_region(img, debug_dir: str | None = None):
    """Find the largest rectangular contour (≈ monitor bezel) and return the
    perspective-warped sub-image.  Returns the warped image or the original."""
    prefix = "screen_region"
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    # Dilate to close gaps
    dilated = cv2.dilate(edges, None, iterations=2)
    if debug_dir:
        _save_debug(prefix, "edges", dilated, debug_dir)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img

    # Find the contour with the largest area that looks roughly rectangular
    best = None
    best_area = 0
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > best_area and area > (img.shape[0] * img.shape[1]) * 0.05:
                best = approx
                best_area = area

    if best is None:
        _eprint("  No suitable rectangular screen region found; using whole image")
        return img

    if debug_dir:
        debug_vis = img.copy()
        cv2.drawContours(debug_vis, [best], -1, (0, 255, 0), 3)
        _save_debug(prefix, "contour", debug_vis, debug_dir)

    # Order points: top-left, top-right, bottom-right, bottom-left
    pts = best.reshape(4, 2).astype(np.float32)
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left (smallest x+y)
    rect[2] = pts[np.argmax(s)]   # bottom-right (largest x+y)
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right (smallest x-y ...)
    rect[3] = pts[np.argmax(diff)]  # bottom-left  (largest x-y ...)

    # Compute width and height of the destination rectangle
    (tl, tr, br, bl) = rect
    w_top = np.linalg.norm(tr - tl)
    w_bot = np.linalg.norm(br - bl)
    max_w = int(max(w_top, w_bot))
    h_left = np.linalg.norm(bl - tl)
    h_right = np.linalg.norm(br - tr)
    max_h = int(max(h_left, h_right))

    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype=np.float32,
    )
    mat = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, mat, (max_w, max_h))
    _eprint(f"  Screen region detected: {max_w}x{max_h}")

    if debug_dir:
        _save_debug(prefix, "warped", warped, debug_dir)

    return warped


# ---------------------------------------------------------------------------
# OCR engines
# ---------------------------------------------------------------------------


def _ocr_tesseract(img, lang: str) -> Tuple[bool, Optional[str]]:
    """Run Tesseract on the preprocessed image.

    Returns ``(success, text)``.
    """
    if not TESSERACT_AVAILABLE:
        return False, None
    try:
        _configure_tesseract()
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
        return True, text.strip()
    except Exception as exc:
        _eprint(f"Tesseract failed: {exc}")
        return False, None


def _ocr_web(img, lang: str) -> Tuple[bool, Optional[str]]:
    """Fallback OCR via OCR.space web API (free tier). Used when Tesseract/
    EasyOCR models are not available or fail."""
    if not REQUESTS_AVAILABLE:
        return False, None
    try:
        import io
        from PIL import Image as PILImage

        # Encode image to JPEG bytes (smaller than PNG for API calls)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        pil_img = PILImage.fromarray(rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=90)
        buf.seek(0)

        # Map lang for OCR.space (uses 3-letter codes like 'Rus', 'Eng')
        ocr_lang = {"rus": "Rus", "eng": "Eng", "ukr": "Ukr", "kaz": "Kaz"}
        langs = [l for l in lang.replace("+", " ").split() if l]
        mapped = "+".join(ocr_lang.get(l, l) for l in langs) if langs else "Rus+Eng"
        # Take only the first language for OCR.space (single lang per request)
        first_lang = mapped.split("+")[0]

        resp = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", buf, "image/jpeg")},
            data={"apikey": "helloworld", "language": first_lang,
                  "scale": True, "OCREngine": 2},
            timeout=60,
        )
        if resp.status_code != 200:
            _eprint(f"Web OCR HTTP {resp.status_code}")
            return False, None

        result = resp.json()
        if result.get("IsErroredOnProcessing"):
            err = result.get("ErrorMessage", ["unknown error"])[0]
            _eprint(f"Web OCR error: {err}")
            return False, None

        texts = []
        for parsed in result.get("ParsedResults", []):
            txt = parsed.get("ParsedText", "").strip()
            if txt:
                texts.append(txt)
        if texts:
            return True, "\n".join(texts)
        return False, None
    except Exception as exc:
        _eprint(f"Web OCR failed: {exc}")
        return False, None


def _ocr_easyocr(img, lang: str) -> Tuple[bool, Optional[str]]:
    """Run EasyOCR on the preprocessed image.

    Returns ``(success, text)``.
    """
    if not EASYOCR_AVAILABLE:
        return False, None
    try:
        # Convert BGR (OpenCV) to RGB (EasyOCR/PIL convention)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        langs = [l for l in lang.replace("+", " ").split() if l]
        # Map 'rus' -> 'ru', 'eng' -> 'en' for EasyOCR
        easy_langs = []
        for l in langs:
            mapped = {"rus": "ru", "eng": "en", "ukr": "uk", "kaz": "kk"}.get(l, l)
            easy_langs.append(mapped)
        if not easy_langs:
            easy_langs = ["ru", "en"]

        reader = easyocr.Reader(easy_langs, gpu=False, verbose=False)
        results = reader.readtext(rgb, paragraph=True)

        lines = []
        for res in results:
            text = res[1].strip()
            if text:
                lines.append(text)
        return True, "\n".join(lines)
    except Exception as exc:
        _eprint(f"EasyOCR failed: {exc}")
        return False, None


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def ocr_image(
    input_path: str,
    lang: str = DEFAULT_LANG,
    mode: str = "auto",
    debug: bool = False,
    upscale_factor: float = DEFAULT_UPSCALE,
    engine: str = "auto",
    save_previews: bool = False,
) -> Optional[str]:
    """Load *input_path*, preprocess, OCR, and return recognised text."""
    path = _check_image(input_path)

    if not CV2_AVAILABLE or not NP_AVAILABLE:
        sys.exit("Error: opencv-python and numpy are required.  Install with:\n"
                 f"  pip install opencv-python numpy")

    # --- Load image -----------------------------------------------------------
    img = cv2.imread(str(path))
    if img is None:
        sys.exit(f"Error: unable to read image — {path} (unsupported or corrupted format)")

    _eprint(f"Image: {path.name}  ({img.shape[1]}x{img.shape[0]})")
    debug_dir: str | None = None
    if debug:
        debug_dir = tempfile.mkdtemp(prefix="ocr_debug_")
        _eprint(f"Debug directory: {debug_dir}")

    # --- Resolve mode ---------------------------------------------------------
    if mode == "auto":
        mode = _detect_auto_mode(img)
        _eprint(f"Auto-detected mode: {mode}")

    # --- Screen-region detection (monitor mode only) -------------------------
    if mode == "monitor":
        _eprint("Attempting screen region detection ...")
        img = detect_screen_region(img, debug_dir)

    # --- Preprocessing --------------------------------------------------------
    _eprint(f"Preprocessing ({mode} mode, upscale={upscale_factor}) ...")
    pipelines = {
        "monitor": preprocess_monitor,
        "screenshot": preprocess_screenshot,
        "document": preprocess_document,
    }
    preprocessor = pipelines.get(mode, preprocess_monitor)
    processed = preprocessor(img, upscale_factor, debug_dir)

    # --- OCR engine selection -------------------------------------------------
    engines = []
    if engine == "auto":
        if TESSERACT_AVAILABLE:
            engines.append(("tesseract", _ocr_tesseract))
        if EASYOCR_AVAILABLE:
            engines.append(("easyocr", _ocr_easyocr))
        if REQUESTS_AVAILABLE:
            engines.append(("web", _ocr_web))
        if not engines:
            _eprint("Error: no OCR engine available. Install pytesseract, easyocr, or requests.")
            if not TESSERACT_AVAILABLE:
                _eprint("  Tesseract: pip install pytesseract")
            if not EASYOCR_AVAILABLE:
                _eprint("  EasyOCR:   pip install easyocr")
            if not REQUESTS_AVAILABLE:
                _eprint("  Web:       pip install requests")
            return None
    elif engine == "tesseract":
        if not TESSERACT_AVAILABLE:
            _eprint("Error: tesseract requested but pytesseract is not installed.")
            return None
        engines = [("tesseract", _ocr_tesseract)]
    elif engine == "easyocr":
        if not EASYOCR_AVAILABLE:
            _eprint("Error: easyocr requested but easyocr is not installed.")
            return None
        engines = [("easyocr", _ocr_easyocr)]
    elif engine == "web":
        if not REQUESTS_AVAILABLE:
            _eprint("Error: web requested but requests is not installed.")
            return None
        engines = [("web", _ocr_web)]

    # --- Run OCR --------------------------------------------------------------
    final_text = ""
    for name, ocr_fn in engines:
        _eprint(f"Running {name} ...")
        success, text = ocr_fn(processed, lang)
        if success:
            _eprint(f"{name} succeeded ({len(text)} chars)")
            final_text = text
            break
        _eprint(f"{name} returned no result; trying next engine ...")

    # --- Preview image --------------------------------------------------------
    if save_previews and final_text:
        try:
            preview_path = str(path.parent / f"{path.stem}_ocr_preview{path.suffix}")
            _save_preview(img, processed, final_text, preview_path)
            _eprint(f"Preview saved: {preview_path}")
        except Exception as e:
            _eprint(f"Could not save preview: {e}")

    return final_text


def _save_preview(original, processed, text: str, output_path: str) -> None:
    """Create a side-by-side comparison image with recognised text overlay."""
    # Convert processed back to BGR if grayscale
    if len(processed.shape) == 2:
        processed_bgr = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
    else:
        processed_bgr = processed

    # Resize processed to match original height if needed
    h_orig, w_orig = original.shape[:2]
    ph, pw = processed_bgr.shape[:2]
    sf = h_orig / ph
    pw2 = int(pw * sf)
    processed_resized = cv2.resize(processed_bgr, (pw2, h_orig))

    # Stack side by side
    combined = np.hstack((original, processed_resized))

    # Overlay text
    line_height = 20
    for i, line in enumerate(text.split("\n")[:30]):
        y = (i + 1) * line_height
        if y > combined.shape[0] - 10:
            break
        cv2.putText(
            combined, line[:80], (10, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
        )
    cv2.imwrite(output_path, combined)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract text from images (photos of monitors, screenshots, documents).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s screen.jpg -p monitor -l rus+eng --debug\n"
            "  %(prog)s error.png -p screenshot -o output.txt\n"
            "  %(prog)s scan.tiff -p document --engine easyocr\n"
        ),
    )
    parser.add_argument("input", type=str, help="Path to input image file")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Save recognised text to file")
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANG,
                        help=f"OCR language(s) (default: {DEFAULT_LANG})")
    parser.add_argument("-p", "--preprocess", type=str,
                        choices=["auto", "monitor", "document", "screenshot"],
                        default="auto",
                        help="Preprocessing pipeline (default: auto)")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Save intermediate preprocessing images to debug folder")
    parser.add_argument("-e", "--engine", type=str,
                        choices=["auto", "tesseract", "easyocr", "web"],
                        default="auto",
                        help="OCR engine (default: auto-detect based on availability)")
    parser.add_argument("-u", "--upscale", type=float, default=DEFAULT_UPSCALE,
                        help=f"Upscale factor for small text (default: {DEFAULT_UPSCALE})")
    parser.add_argument("--save-previews", action="store_true",
                        help="Save comparison preview image with recognised text overlay")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    text = ocr_image(
        input_path=args.input,
        lang=args.lang,
        mode=args.preprocess,
        debug=args.debug,
        upscale_factor=args.upscale,
        engine=args.engine,
        save_previews=args.save_previews,
    )

    if text:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            _eprint(f"Text written to {args.output}")
        else:
            print(text)
    else:
        _eprint("No text was extracted.")
        sys.exit(1)


if __name__ == "__main__":
    main()

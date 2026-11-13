#!/usr/bin/env python3
"""Capture the showcase as high-resolution section screenshots and a PDF carousel.

    python scripts/build_showcase.py          # first, so the page has today's data
    python scripts/capture_screenshots.py     # then this

Writes showcase/screenshots/NN-<section>.png (2x resolution) and
showcase/screenshots/quant-spillover-atlas.pdf, one section per page, all pages the same
size: the format LinkedIn shows as a swipeable document carousel.

Needs Microsoft Edge or Google Chrome (headless) and Pillow (pip install pillow).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "showcase" / "index.html"
OUT = ROOT / "showcase" / "screenshots"
BACKGROUND = (17, 17, 16)          # --page in the showcase
SECTIONS = ("hero", "relay", "network", "score", "robust", "heat", "brief", "method")
CAROUSEL = ("hero", "relay", "network", "score", "robust", "heat", "method")   # the brief is optional: it changes daily

BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser", "msedge",
)


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    sys.exit("No Edge or Chrome found for headless screenshots")


def shoot(exe: str, section: str, target: Path, width: int = 1440, height: int = 2400, scale: int = 2, attempts: int = 3) -> None:
    """Headless screenshot of one section; a hung browser is killed and the shot retried."""
    url = PAGE.resolve().as_uri() + f"?still&shot={section}"
    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            try:
                subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                                "--disable-extensions", f"--user-data-dir={profile}",
                                f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
                                "--virtual-time-budget=5000", f"--screenshot={target}", url],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
                if target.exists() and target.stat().st_size > 0:
                    return
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                print(f"  {section}: browser did not finish (attempt {attempt}/{attempts})", file=sys.stderr)
    raise SystemExit(f"could not capture section {section!r}")


def trim(path: Path, pad: int = 48) -> "Image.Image":
    from PIL import Image, ImageChops
    img = Image.open(path).convert("RGB")
    bg = Image.new("RGB", img.size, BACKGROUND)
    diff = ImageChops.difference(img, bg).convert("L").point(lambda v: 255 if v > 14 else 0)
    box = diff.getbbox()
    if not box:
        return img
    bottom = min(img.height, box[3] + pad)
    top = max(0, box[1] - pad)
    return img.crop((0, top, img.width, bottom))


def carousel(images: list, target: Path) -> None:
    from PIL import Image
    width = max(i.width for i in images)
    height = max(max(i.height for i in images), int(width * 9 / 16))
    pages = []
    for img in images:
        page = Image.new("RGB", (width, height), BACKGROUND)
        page.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
        pages.append(page)
    pages[0].save(target, save_all=True, append_images=pages[1:], resolution=144)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--with-brief", action="store_true", help="include today's morning brief in the PDF")
    a = p.parse_args()
    if not PAGE.exists():
        sys.exit("showcase/index.html not found: run scripts/build_showcase.py first")
    OUT.mkdir(parents=True, exist_ok=True)
    exe = browser()
    trimmed = {}
    for n, section in enumerate(SECTIONS, 1):
        raw = OUT / f"_raw_{section}.png"
        shoot(exe, section, raw)
        img = trim(raw)
        raw.unlink()
        final = OUT / f"{n:02d}-{section}.png"
        img.save(final, optimize=True)
        trimmed[section] = img
        print(f"{final.relative_to(ROOT)}  {img.width}x{img.height}")
    order = CAROUSEL + (("brief",) if a.with_brief else ())
    pdf = OUT / "quant-spillover-atlas.pdf"
    carousel([trimmed[s] for s in order], pdf)
    print(f"{pdf.relative_to(ROOT)}  {len(order)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())

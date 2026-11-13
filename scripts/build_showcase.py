#!/usr/bin/env python3
"""Build the interactive showcase page from the live study.

    python scripts/build_showcase.py            # writes showcase/index.html
    python scripts/build_showcase.py --open     # and opens it in the browser

Every number on the page comes from ``atlas.study.run()`` and ``atlas.brief.brief()``
at build time. The page is a single self-contained file.
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas import brief, study, tradable  # noqa: E402
from atlas import universe as U  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(ROOT / "showcase" / "index.html"))
    p.add_argument("--open", action="store_true")
    a = p.parse_args()
    results = study.run(deep=True)
    panel, _ = study.load_panel()
    try:
        constituents = tradable.constituent_check(panel)
    except Exception as exc:  # the page still renders without it
        print(f"constituent check unavailable: {exc}", file=sys.stderr)
        constituents = []
    try:
        today = brief.brief(study_forecasts=results["forecasts"], panel=panel)
    except Exception as exc:  # the page still renders without the brief
        print(f"brief unavailable: {exc}", file=sys.stderr)
        today = None
    results["constituents"] = constituents
    payload = {"study": results, "brief": today, "names": {m.key: m.name for m in U.ALL}}
    template = (ROOT / "showcase" / "template.html").read_text(encoding="utf-8")
    page = template.replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":"), default=str).replace("</", "<\\/"))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    if a.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Robustness audit of one forecast: statistical tests, placebos, challengers and regimes.

    python scripts/audit.py --sector nifty --target gap
    python scripts/audit.py --sector metal --target intraday --permutations 100
"""
import argparse
import json
import pathlib
import sys

_here = pathlib.Path(__file__).resolve()
for _candidate in (_here.parent / "_vendor", *_here.parents):
    if (_candidate / "atlas" / "__init__.py").exists():
        sys.path.insert(0, str(_candidate))
        break
else:
    sys.exit("atlas not found: run from the repository, or install the skill with scripts/install_skills.py")

from atlas import robustness, study  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sector", default="nifty", help="nifty, it, bank, metal, pharma, auto, energy, fmcg")
    p.add_argument("--target", default="gap", choices=["gap", "intraday"])
    p.add_argument("--permutations", type=int, default=50, help="shuffled-data placebo draws (default 50)")
    a = p.parse_args()
    try:
        panel, failed = study.load_panel()
        if f"{a.sector}:{a.target}" not in panel.cols:
            p.error(f"unknown sector {a.sector!r}")
        out = robustness.audit(panel, a.sector, a.target, a.permutations)
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    out["india_source"] = dict(study.SOURCE_NOTE)
    out["unavailable"] = failed
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

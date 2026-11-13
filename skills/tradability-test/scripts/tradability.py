#!/usr/bin/env python3
"""Do any global-cue strategies make money after costs? Pre-registered intraday tests.

    python scripts/tradability.py
    python scripts/tradability.py --constituents      # copper rule stock by stock, with a control stock
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

from atlas import study, tradable  # noqa: E402
from atlas.data import DataUnavailable  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--constituents", action="store_true", help="also test the copper rule on each metal stock and a control")
    a = p.parse_args()
    try:
        panel, failed = study.load_panel()
        out = tradable.run(panel)
        if a.constituents:
            out["constituent_check"] = tradable.constituent_check(panel)
    except (DataUnavailable, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    out["india_source"] = dict(study.SOURCE_NOTE)
    out["unavailable"] = failed
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

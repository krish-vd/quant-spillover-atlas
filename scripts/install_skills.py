#!/usr/bin/env python3
"""Install skills into a Claude Code skills directory.

Each installed skill is self-contained: it carries its own copy of the shared
``atlas`` library, so it keeps working if this repository is moved or deleted.

    python scripts/install_skills.py                         # every skill -> ~/.claude/skills
    python scripts/install_skills.py global-cues-brief spillover-network
    python scripts/install_skills.py --target .claude/skills # one project only
    python scripts/install_skills.py --list
    python scripts/install_skills.py --uninstall             # remove everything this script installed
    python scripts/install_skills.py --uninstall global-cues-brief

Run it again after ``git pull`` to update the installed copies.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
CORE = ROOT / "atlas"
MARKER = ".installed-by-quant-spillover-atlas"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "_vendor", "tests")


def available() -> list[str]:
    return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())


def install(name: str, target: Path, force: bool) -> str:
    source, dest = SKILLS / name, target / name
    if dest.exists():
        if not (dest / MARKER).exists() and not force:
            return f"skipped {name}: {dest} exists and was not installed by this script (use --force to replace it)"
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=IGNORE)
    shutil.copytree(CORE, dest / "scripts" / "_vendor" / "atlas", ignore=IGNORE)
    (dest / MARKER).write_text(f"Installed from {ROOT}\n", encoding="utf-8")
    return f"installed {name}"


def uninstall(name: str, target: Path) -> str:
    dest = target / name
    if not dest.exists():
        return f"not installed: {name}"
    if not (dest / MARKER).exists():
        return f"left alone: {dest} was not installed by this script"
    shutil.rmtree(dest)
    return f"removed {name}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("skills", nargs="*", help="skill names (default: all)")
    p.add_argument("--target", default=str(Path.home() / ".claude" / "skills"),
                   help="skills directory (default ~/.claude/skills; use .claude/skills inside a project for that project only)")
    p.add_argument("--list", action="store_true", help="list the skills in this repository and exit")
    p.add_argument("--uninstall", action="store_true", help="remove skills this script installed")
    p.add_argument("--force", action="store_true", help="replace a folder of the same name that this script did not install")
    a = p.parse_args()

    names = available()
    if a.list:
        print("\n".join(names))
        return 0
    unknown = [s for s in a.skills if s not in names]
    if unknown:
        print(f"unknown skill(s): {', '.join(unknown)}\navailable: {', '.join(names)}", file=sys.stderr)
        return 2
    chosen = a.skills or names
    target = Path(a.target).expanduser()
    if a.uninstall:
        if not a.skills:  # only what we installed, including skills since removed from the repo
            chosen = sorted(d.name for d in target.iterdir() if (d / MARKER).exists()) if target.exists() else []
        for name in chosen:
            print(uninstall(name, target))
        return 0
    target.mkdir(parents=True, exist_ok=True)
    results = [install(name, target, a.force) for name in chosen]
    print("\n".join(results))
    done = sum(1 for r in results if r.startswith("installed"))
    print(f"\n{done} skill(s) installed in {target}")
    print("Start a new Claude Code session (or run /skills) to see them. Then just ask, for example:")
    print('  "What do the global cues from last night mean for Nifty IT this morning?"')
    return 0 if done == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

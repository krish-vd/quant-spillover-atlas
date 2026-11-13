#!/usr/bin/env python3
"""Build a self-contained zip for each skill, ready to upload to claude.ai.

Each zip holds the skill folder plus a copy of ``atlas`` under
``scripts/_vendor/``, so the skill runs without this repository.

    python scripts/package_skills.py                 # all skills
    python scripts/package_skills.py global-cues-brief  # one skill
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
CORE = ROOT / "atlas"
DIST = ROOT / "dist"
SKIP_DIRS = {"__pycache__", "tests", "_vendor"}


def _files(base: Path):
    for path in sorted(base.rglob("*")):
        if path.is_file() and not (set(path.relative_to(base).parts) & SKIP_DIRS) and path.suffix != ".pyc":
            yield path


def package(skill_dir: Path) -> Path:
    if not (skill_dir / "SKILL.md").exists():
        raise SystemExit(f"{skill_dir.name}: no SKILL.md")
    DIST.mkdir(exist_ok=True)
    target = DIST / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in _files(skill_dir):
            archive.write(path, Path(skill_dir.name) / path.relative_to(skill_dir))
        for path in _files(CORE):
            archive.write(path, Path(skill_dir.name) / "scripts" / "_vendor" / "atlas" / path.relative_to(CORE))
    return target


def main() -> int:
    wanted = sys.argv[1:] or sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    lines = []
    for name in wanted:
        target = package(SKILLS / name)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        lines.append(f"{digest}  {target.name}")
        print(f"built {target.relative_to(ROOT)}  ({target.stat().st_size:,} bytes)")
    (DIST / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

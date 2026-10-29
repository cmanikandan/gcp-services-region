#!/usr/bin/env python3
"""
Copies the compact offline snapshot (`dist/data/mobile_catalog.json`) into the
Universal SwiftUI iOS/iPadOS app bundle Resources folder so the app launches
with 0ms offline access even in Airplane Mode.

Uses 100% Python 3.10+ standard library only.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_CATALOG = REPO_ROOT / "dist" / "data" / "mobile_catalog.json"
DST_DIR = (
    REPO_ROOT
    / "ios"
    / "GoogleCloudExplorer"
    / "GoogleCloudExplorer"
    / "Resources"
)
DST_CATALOG = DST_DIR / "mobile_catalog.json"


def main() -> int:
    if not SRC_CATALOG.exists():
        print(f"[Error] {SRC_CATALOG} not found. Run `python3 generator.py` first.", file=sys.stderr)
        return 1
    DST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_CATALOG, DST_CATALOG)
    size_kb = DST_CATALOG.stat().st_size / 1024.0
    print(f"[iOS Sync] Bundled {DST_CATALOG.relative_to(REPO_ROOT)} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

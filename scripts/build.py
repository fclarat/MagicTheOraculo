#!/usr/bin/env python3
"""Build every published asset in the order its dependencies require.

Run this before deploying the static site:

    python scripts/build.py

The Scryfall bulk file is reused when it already exists. The only network work
on a normal repeat build is checking first-print data that is still missing.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

# games.json is generated once before years are fetched, then again to merge
# the first-print metadata into its final and famous subsets.
STEPS = (
    "build_data.py",
    "build_all.py",
    "build_games_data.py",
    "build_years.py",
    "build_games_data.py",
    "build_reveal.py",
    "build_site.py",
    "add_og.py",
)


def main():
    for script in STEPS:
        print(f"\n==> {script}", flush=True)
        subprocess.run([sys.executable, str(ROOT / script)], check=True)
    print("\nBuild complete.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# --------------------------------------------------------------------------
#
# extra_content.py - copy the game sections of docs/ExtraContent.md into the
#                    game pages
#
# docs/ExtraContent.md lists everything the core adds: a core-wide section
# and one section per game. Each game's page carries its own section as an
# "Extra content" overview, between two marker comments. This script writes
# those sections, so the file and the pages cannot drift apart: edit
# ExtraContent.md when a feature is added or removed, then run
#
#   python3 tools/extra_content.py          write the pages
#   python3 tools/extra_content.py --check  report pages that are out of date
#                                           (exit 1 if any)
#
# A page without the markers gets its section inserted after "## Controls"
# (and a line in its table of contents, if it has one).
#
# --------------------------------------------------------------------------

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SOURCE = DOCS / "ExtraContent.md"

# section heading in ExtraContent.md -> game page
PAGES = {
    "Mortal Kombat": "MortalKombat.md",
    "Mortal Kombat II": "MortalKombatII.md",
    "NBA Jam": "NBAJam.md",
    "NBA Jam Tournament Edition": "NBAJamTE.md",
    "Judge Dredd": "JudgeDredd.md",
}

START = "<!-- extra-content:start (from ExtraContent.md by tools/extra_content.py) -->"
END = "<!-- extra-content:end -->"
TOC_LINE = "- [Extra content](#extra-content)"


def sections(text):
    """Heading -> body for every '## ' section of ExtraContent.md."""
    out = {}
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        heading, _, body = part.partition("\n")
        out[heading.strip()] = body.strip("\n")
    return out


def block(body):
    return f"{START}\n## Extra content\n\n{body}\n\n{END}\n"


def update(page, body):
    text = page.read_text()
    new_block = block(body)
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n",
                      lambda m: new_block, text, count=1, flags=re.S)
    else:
        m = re.search(r"^## Controls\n.*?(?=^## )", text, flags=re.M | re.S)
        if not m:
            raise SystemExit(f"{page.name}: no '## Controls' section")
        text = text[:m.end()] + new_block + "\n" + text[m.end():]
    if "- [Controls](#controls)" in text and TOC_LINE not in text:
        text = text.replace("- [Controls](#controls)\n",
                            "- [Controls](#controls)\n" + TOC_LINE + "\n", 1)
    return text


def main():
    check = "--check" in sys.argv[1:]
    secs = sections(SOURCE.read_text())
    stale = []
    for heading, name in PAGES.items():
        if heading not in secs:
            raise SystemExit(f"ExtraContent.md has no section '{heading}'")
        page = DOCS / name
        new = update(page, secs[heading])
        if new != page.read_text():
            stale.append(name)
            if not check:
                page.write_text(new)
    if check:
        for name in stale:
            print(f"out of date: docs/{name}")
        sys.exit(1 if stale else 0)
    print("updated: " + (", ".join(stale) if stale else "nothing to do"))


if __name__ == "__main__":
    main()

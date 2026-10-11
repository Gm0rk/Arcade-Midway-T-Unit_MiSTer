#!/usr/bin/env python3
# ============================================================================
#  check.py - the Secret Player List window's frames against tunit_splist.py
#
#  Runs obj_dir/Vtunit_splist for each page (and once with the window off)
#  and compares every dot of the picture with the page drawn here from
#  tools/tunit_splist.py's pages, font and background images: the game's
#  background (2 x 2 dots per image pixel), the characters in their colours
#  on the 7 x 8 grid at dot 4, line 7. Each frame is also saved as
#  out/page<N>.png (2x) to look at.
#
#  Usage: check.py [PAGE ...]      (default: every page)
#
#  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
# ============================================================================

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import tunit_splist as sl  # noqa: E402

W, H, X0, Y0, CW, CH = 400, 254, 4, 7, 7, 8
INK = {0: (0xFF, 0xFF, 0xFF), 1: (0xFF, 0xE0, 0x40), 2: (0x60, 0xE0, 0xFF), 3: (0xA0, 0xA0, 0xA0)}
SIM = os.path.join(HERE, "obj_dir", "Vtunit_splist")


def expected(rows, game, font, bg, pal):
    img = bytearray()
    base = game * sl.BG_W * sl.BG_H
    for y in range(H):
        for x in range(W):
            c = pal[game * 256 + bg[base + (y // 2) * sl.BG_W + x // 2]]
            img += bytes([c >> 16, (c >> 8) & 0xFF, c & 0xFF])
    for r, row in enumerate(rows):
        if not row:
            continue
        col = row[0]
        for t, colour in row[1]:
            for ch in t:
                glyph = font[ord(ch) - 32]
                for ly in range(CH):
                    for px in range(CW):
                        if glyph[ly] >> px & 1:
                            i = ((Y0 + r * CH + ly) * W + X0 + col * CW + px) * 3
                            img[i:i + 3] = bytes(INK[colour])
                col += 1
    return bytes(img)


def frame(page, game, off=False):
    with tempfile.NamedTemporaryFile(suffix=".ppm") as f:
        r = subprocess.run([SIM, str(page), str(game), f.name] + (["-off"] if off else []),
                           capture_output=True, text=True)
        data = open(f.name, "rb").read()
    return r, data[data.index(b"255\n") + 4:]


def save(data, path):
    from PIL import Image
    im = Image.frombytes("RGB", (W, H), data)
    im.resize((W * 2, H * 2), Image.NEAREST).save(path)


def main():
    pages = sl.pages()
    font = sl.font_rows()
    bg = [int(l, 16) for l in open(sl.OUT["bg"])]
    pal = [int(l, 16) for l in open(sl.OUT["pal"])]
    which = [int(a) for a in sys.argv[1:]] or range(len(pages))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    bad = 0
    for p in which:
        label, rows = pages[p]
        game = 0 if label.startswith("nbajam ") else 1
        r, got = frame(p, game)
        want = expected(rows, game, font, bg, pal)
        diff = sum(1 for i in range(0, len(want), 3) if got[i:i + 3] != want[i:i + 3])
        save(got, os.path.join(HERE, "out", "page%d.png" % p))
        print("page %d (%s): %s" % (p, label, "OK" if not diff else "%d dots differ" % diff))
        bad += diff != 0
    r, _ = frame(0, 0, off=True)
    print(r.stdout.strip())
    bad += r.returncode != 0
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

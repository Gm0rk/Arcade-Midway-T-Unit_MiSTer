#!/usr/bin/env python3
"""
rgbtool.py - convert and compare frame files (MAME frames.lua, simulator)

    rgbtool.py png  f00100.rgb [out.png]        RGB1 frame to PNG
    rgbtool.py diff a.rgb b.rgb [diff.png]      count differing pixels
    rgbtool.py sheet out.png f1.rgb f2.rgb ...  side by side contact sheet
    rgbtool.py seq simdir mamedir A B [--dx N] [--off K]
                                                sim frames A..B (those that
                                                exist) against MAME frame
                                                n + K (default 0: frames.lua
                                                and the simulator number the
                                                same pictures alike); frames
                                                that differ are listed with
                                                the MAME frame they match best
                                                within n + K - 3 .. n + K + 3
    rgbtool.py cmp sim.rgb mame.rgb [diff.png] [--dx N]
                                                simulator frame against MAME's:
                                                the sim raster cropped to
                                                MAME's visible area, which
                                                starts at HEBLNK x 2 (90 for
                                                MK and MK2, 100 for NBA Jam,
                                                NBA Jam TE and Judge Dredd;
                                                tools/mame/ioregs.lua)

Frame file: "RGB1", width, height, frame (little-endian 32-bit), then
width x height x 3 bytes of RGB.

Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
"""

import struct
import sys

from PIL import Image


def load(path):
    d = open(path, 'rb').read()
    if d[:4] != b'RGB1':
        raise ValueError('%s: not an RGB1 frame' % path)
    w, h, n = struct.unpack('<III', d[4:16])
    return w, h, n, d[16:16 + w * h * 3]


# MAME's visible area inside the simulator's raster, which starts counting
# at the rise of HSync / VSync. MAME sets the visible area from the 34010's
# blanking registers: x from HEBLNK x 2 to HSBLNK x 2 - 1, y from VEBLNK to
# VSBLNK - 1. MK and MK2 program HEBLNK 0x2D (x 90), NBA Jam, NBA Jam TE and
# Judge Dredd 0x32 (x 100); VEBLNK is 0x14 (y 20) for all of them.
SIM_DX, SIM_DY = 90, 20


def crop(w, h, px, cw, ch, dx, dy):
    out = bytearray()
    for y in range(ch):
        out += px[((y + dy) * w + dx) * 3:((y + dy) * w + dx + cw) * 3]
    return bytes(out)


def to_image(path):
    w, h, n, px = load(path)
    return Image.frombytes('RGB', (w, h), px)


def main():
    global SIM_DX
    if '--dx' in sys.argv:
        i = sys.argv.index('--dx')
        SIM_DX = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    cmd = sys.argv[1]
    if cmd == 'png':
        out = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2].rsplit('.', 1)[0] + '.png'
        to_image(sys.argv[2]).save(out)
    elif cmd == 'diff':
        wa, ha, na, a = load(sys.argv[2])
        wb, hb, nb, b = load(sys.argv[3])
        if (wa, ha) != (wb, hb):
            print('size differs: %dx%d vs %dx%d' % (wa, ha, wb, hb))
            sys.exit(2)
        diff = [i for i in range(wa * ha) if a[3 * i:3 * i + 3] != b[3 * i:3 * i + 3]]
        print('%d of %d pixels differ' % (len(diff), wa * ha))
        if diff:
            ys = [i // wa for i in diff]
            xs = [i % wa for i in diff]
            print('box x %d-%d y %d-%d' % (min(xs), max(xs), min(ys), max(ys)))
        if len(sys.argv) > 4:
            img = Image.new('RGB', (wa, ha))
            m = bytearray(a)
            for i in diff:
                m[3 * i:3 * i + 3] = b'\xff\x00\xff'
            Image.frombytes('RGB', (wa, ha), bytes(m)).save(sys.argv[4])
        sys.exit(1 if diff else 0)
    elif cmd == 'cmp':
        ws, hs, ns, s_px = load(sys.argv[2])
        wm, hm, nm, m_px = load(sys.argv[3])
        c = crop(ws, hs, s_px, wm, hm, SIM_DX, SIM_DY)
        diff = [i for i in range(wm * hm) if c[3 * i:3 * i + 3] != m_px[3 * i:3 * i + 3]]
        print('%s vs %s: %d of %d pixels differ' % (sys.argv[2], sys.argv[3], len(diff), wm * hm))
        if diff:
            ys = [i // wm for i in diff]
            xs = [i % wm for i in diff]
            print('box x %d-%d y %d-%d' % (min(xs), max(xs), min(ys), max(ys)))
            if len(sys.argv) > 4:
                a = Image.frombytes('RGB', (wm, hm), c)
                b = Image.frombytes('RGB', (wm, hm), m_px)
                m = bytearray(c)
                for i in diff:
                    m[3 * i:3 * i + 3] = b'\xff\x00\xff'
                d = Image.frombytes('RGB', (wm, hm), bytes(m))
                sheet = Image.new('RGB', (3 * wm + 8, hm), (40, 40, 40))
                sheet.paste(a, (0, 0)); sheet.paste(b, (wm + 4, 0)); sheet.paste(d, (2 * wm + 8, 0))
                sheet.save(sys.argv[4])
        sys.exit(1 if diff else 0)
    elif cmd == 'seq':
        off = 0
        if '--off' in sys.argv:
            i = sys.argv.index('--off')
            off = int(sys.argv[i + 1])
            del sys.argv[i:i + 2]
        sdir, mdir, a, b = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
        mcache = {}

        def mframe(n):
            if n not in mcache:
                try:
                    mcache[n] = load('%s/f%05d.rgb' % (mdir, n))[3]
                except FileNotFoundError:
                    mcache[n] = None
            return mcache[n]

        def ndiff(x, y):
            return sum(1 for i in range(0, len(x), 3) if x[i:i + 3] != y[i:i + 3])

        same = bad = 0
        for n in range(a, b + 1):
            try:
                ws, hs, ns, s_px = load('%s/f%05d.rgb' % (sdir, n))
            except FileNotFoundError:
                continue
            m = mframe(n + off)
            if m is None:
                continue
            c = crop(ws, hs, s_px, 400, 254, SIM_DX, SIM_DY)
            d = ndiff(c, m)
            if d == 0:
                same += 1
                continue
            bad += 1
            best = min(((ndiff(c, mframe(k)), k) for k in range(n + off - 3, n + off + 4)
                        if mframe(k) is not None), default=None)
            print('sim %5d: %6d pixels differ from MAME %5d; best MAME %5d (%d)' % (n, d, n + off, best[1], best[0]))
        print('%d frames match, %d differ' % (same, bad))
    elif cmd == 'sheet':
        imgs = [to_image(p) for p in sys.argv[3:]]
        w = sum(i.width for i in imgs) + 4 * (len(imgs) - 1)
        h = max(i.height for i in imgs)
        sheet = Image.new('RGB', (w, h), (40, 40, 40))
        x = 0
        for i in imgs:
            sheet.paste(i, (x, 0))
            x += i.width + 4
        sheet.save(sys.argv[2])


if __name__ == '__main__':
    main()

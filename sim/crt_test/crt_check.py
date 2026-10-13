#!/usr/bin/env python3
# crt_check.py — checks of the analog CRT stage (tunit_crt: centred sync,
# CRT V-Size, CRT Adjust) on the T-Unit raster, through obj_dir/crt_tb.
#
# Copyright (C) 2026 Gm0rk. Distributed under GNU GPL v3 or later.
#
# Each case runs 35 board frames (CRT V-Size ramps one line per frame, up to
# 21) and looks at the last full frame of output: lines per frame, frame
# length in clocks, line length, which picture lines appear on which output
# lines (R = picture line), and the visible dots per line.
#   PVM:     lines = 289 - 3 x step, the frame as long as the board's, every
#            picture line once and in order, on lines 11-264 after VSync.
#   Cabinet: 289 lines of 6072 clocks (the board's timing), 254 + 3 x step
#            rows, the source line rising from 0 to the last.
#   V-Shift: +5 / -5 moves the picture 5 lines up / down in every mode.
#   V-Size 0: the picture as without CRT V-Size (lines 11-264, 400 dots).
#   Video Timing 57 / 60 Hz (the testbench drops the board's blank lines as
#            the 34010 does): 277 / 263 lines, every picture line once; with
#            a V-Shift that puts VSync on the picture, the lines shown are
#            still in order and nothing is sent during VSync.
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TB = os.path.join(HERE, 'obj_dir', 'crt_tb')
OUT = os.path.join(HERE, 'out')
DT = np.dtype([('c', '<u8'), ('r', 'u1'), ('g', 'u1'), ('b', 'u1'), ('f', 'u1')])
FRAME = 506 * 289 * 12

def run(name, vshift=0, vsize=0, mode=0, vt=0):
    p = os.path.join(OUT, name + '.bin')
    subprocess.run([TB, p, '35', '3', '1', '0', '0', '0', str(vshift & 31), str(vsize), str(mode), str(vt)], check=True)
    return p

def last_frame(p):
    d = np.fromfile(p, dtype=DT)
    hs = d['f'] & 1; vs = (d['f'] >> 1) & 1; de = (d['f'] >> 2) & 1
    lit = (d['r'] | d['g'] | d['b']) != 0
    in_vs = int(np.sum((vs == 1) & ((de == 1) | lit)))    # dots sent during VSync
    st = np.where((hs[1:] == 1) & (hs[:-1] == 0))[0] + 1
    L = []
    for i in range(len(st) - 1):
        a, b = st[i], st[i + 1]
        idx = np.where(de[a:b])[0]
        rr = d['r'][a:b][idx]
        L.append(dict(c=int(d['c'][a]), per=int(d['c'][b] - d['c'][a]), vs=bool(vs[a] and not vs[a - 1]),
                      den=len(idx), r=rr))
    vi = [i for i, l in enumerate(L) if l['vs']]
    seg = L[vi[-2]:vi[-1]]
    rows = [(i, l) for i, l in enumerate(seg) if l['den'] > 0]
    return dict(lines=len(seg), clocks=seg[-1]['c'] + seg[-1]['per'] - seg[0]['c'],
                pers=sorted(set(l['per'] for l in seg)), first=rows[0][0], last=rows[-1][0],
                nrows=len(rows), dots=sorted(set(l['den'] for _, l in rows)),
                src=[int(np.bincount(l['r']).argmax()) for _, l in rows],
                pure=all(l['r'].min() == l['r'].max() for _, l in rows),
                mean=[float(l['r'].mean()) for _, l in rows], in_vs=in_vs)

STEP = {1: 1, 3: 3, 7: 7, 14: -1, 12: -3, 8: -7}     # OSD value -> step
cases = [('v0', 0, 0, 0), ('v0_up5', 5, 0, 0), ('v0_dn5', -5, 0, 0)]
for m in (0, 1):
    for v in STEP:
        cases.append(('%s_%+d' % ('pvm' if m == 0 else 'cab', STEP[v]), 0, v, m))
    cases.append(('%s_-7_up5' % ('pvm' if m == 0 else 'cab'), 5, 8, m))
    cases.append(('%s_-7_dn5' % ('pvm' if m == 0 else 'cab'), -5, 8, m))
cases += [('vt57', 0, 0, 0, 1), ('vt60', 0, 0, 0, 2), ('vt60_dn5', -5, 0, 0, 2), ('vt60_up10', 10, 0, 0, 2)]

os.makedirs(OUT, exist_ok=True)
with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
    res = dict(zip([c[0] for c in cases], ex.map(lambda c: last_frame(run(*c)), cases)))

fails = []
def check(name, ok, what):
    print('%-14s %-4s %s' % (name, 'ok' if ok else 'FAIL', what))
    if not ok: fails.append(name)

r = res['v0']
check('v0', r['lines'] == 289 and r['clocks'] == FRAME and r['pers'] == [6072] and (r['first'], r['last']) == (11, 264)
      and r['src'] == list(range(254)) and r['pure'] and r['dots'] == [400],
      'lines %d, rows %d-%d, dots %s' % (r['lines'], r['first'], r['last'], r['dots']))
for m in ('pvm', 'cab'):
    for s in (1, 3, 7, -1, -3, -7):
        n = '%s_%+d' % (m, s); r = res[n]
        if m == 'pvm':
            ok = (r['lines'] == 289 - 3 * s and r['clocks'] == FRAME and r['src'] == list(range(254)) and r['pure']
                  and (r['first'], r['last']) == (11, 264) and r['dots'] == [400])
            what = 'lines %d, line %s clocks, rows %d-%d, every picture line once: %s' % (
                r['lines'], '/'.join(map(str, r['pers'])), r['first'], r['last'], r['src'] == list(range(254)))
        else:
            mono = all(b >= a for a, b in zip(r['mean'], r['mean'][1:]))
            ok = (r['lines'] == 289 and r['pers'] == [6072] and r['nrows'] == 254 + 3 * s and mono
                  and r['src'][0] == 0 and r['src'][-1] >= 252 and r['dots'] == [400])
            what = 'lines %d of %s clocks, %d rows (%d-%d), source %d..%d rising' % (
                r['lines'], r['pers'][0], r['nrows'], r['first'], r['last'], r['src'][0], r['src'][-1])
        check(n, ok, what)
for base in ('v0', 'pvm_-7', 'cab_-7'):
    b = res[base]
    for d, sh in (('up5', -5), ('dn5', 5)):
        n = (base if base == 'v0' else base) + '_' + d
        r = res[n]
        check(n, r['first'] == b['first'] + sh and r['last'] == b['last'] + sh and r['nrows'] == b['nrows'],
              'rows %d-%d (V-Shift 0: %d-%d)' % (r['first'], r['last'], b['first'], b['last']))
for n, lines, rows in (('vt57', 277, (11, 264)), ('vt60', 263, (9, 262))):
    r = res[n]
    check(n, r['lines'] == lines and (r['first'], r['last']) == rows and r['src'] == list(range(254)) and r['pure']
          and r['dots'] == [400] and r['in_vs'] == 0,
          'lines %d, rows %d-%d, every picture line once: %s' % (r['lines'], r['first'], r['last'], r['src'] == list(range(254))))
for n in ('vt60_dn5', 'vt60_up10'):
    r = res[n]
    check(n, r['lines'] == 263 and r['src'] == sorted(set(r['src'])) and r['pure'] and r['in_vs'] == 0,
          'lines %d, rows %d-%d, picture lines %d..%d in order, %d dots during VSync' % (
              r['lines'], r['first'], r['last'], r['src'][0], r['src'][-1], r['in_vs']))
print('%d checks failed' % len(fails) if fails else 'all checks passed')
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
# state_cmp.py - compare the DCS DSP's registers with MAME's, instruction by
# instruction
#
#   python3 state_cmp.py sim_state.bin mame_state.bin [sim_first mame_first [lead]]
#
# sim_state.bin: the simulator's --dcsstate (per retired instruction: its PC
# and the registers after it). mame_state.bin: MAME's ADSP_LOG (per
# instruction: its PC and the registers before it, from a MAME built with the
# state log in adsp21xx_device::execute_run). Both are 32 16-bit words a
# record: PC, AX0 AX1 AY0 AY1 AR AF MX0 MX1 MY0 MY1 MR0 MR1 MR2 MF SI SE SB
# SR0 SR1, ASTAT PX CNTR, I0-I7, MSTAT.
#
# MAME's records are turned into "PC, registers after it" (the next record's
# registers), the two streams are lined up on their PCs (a wait loop may run
# a different number of times: the comparison resynchronises there, and
# skips the registers a waiting loop changes, AR / AF / ASTAT and the I
# register it polls), and the first register that differs is reported.
#
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

import sys
import numpy as np

NAMES = ['PC', 'AX0', 'AX1', 'AY0', 'AY1', 'AR', 'AF', 'MX0', 'MX1', 'MY0', 'MY1', 'MR0', 'MR1',
         'MR2', 'MF', 'SI', 'SE', 'SB', 'SR0', 'SR1', 'ASTAT', 'PX', 'CNTR',
         'I0', 'I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'MSTAT']

s = np.fromfile(sys.argv[1], dtype='<u2').reshape(-1, 32)
m = np.fromfile(sys.argv[2], dtype='<u2').reshape(-1, 32)
# MAME: registers after instruction k = registers before k+1
ma = np.concatenate([m[:-1, :1], m[1:, 1:]], axis=1)

sp, mp = s[:, 0], ma[:, 0]
# line up: given the two logs' first instruction numbers and MAME's lead (it
# runs 36 instructions before its start-up reset), or by searching
if len(sys.argv) > 4:
    s0, m0 = int(sys.argv[3]), int(sys.argv[4])
    lead = int(sys.argv[5]) if len(sys.argv) > 5 else 36
    d = s0 + lead - m0                      # sim record i = MAME record i + d
    if d < 0: s = s[-d:]; sp = s[:, 0]; off = 0
    else: off = d
    # settle within a few instructions
    W = 64
    best = None
    for t in range(0, 200):
        for o in (off + t, off - t):
            if 0 <= o < len(mp) - W and np.array_equal(sp[:W], mp[o:o + W]):
                best = o; break
        if best is not None: break
    off = best if best is not None else off
else:
    W = 64
    key = sp[:W].tobytes()
    off = -1
    for j in range(0, len(mp) - W):
        if mp[j] == sp[0] and mp[j:j + W].tobytes() == key:
            off = j; break
    if off < 0:
        print("could not line the streams up"); sys.exit(1)
print("simulation record 0 = MAME record %d" % off)

i, j = 0, off
resync = 0
checked = 0
first_bad = None
K = 3000
while i < len(sp) and j < len(mp):
    if sp[i] != mp[j]:
        found = None
        for t in range(1, K + 1):
            for di in range(t + 1):
                dj = t - di
                a, b = i + di, j + dj
                if a + 32 <= len(sp) and b + 32 <= len(mp) and np.array_equal(sp[a:a + 32], mp[b:b + 32]):
                    found = (di, dj); break
            if found: break
        if not found:
            print("lost the PC stream at simulation %d / MAME %d" % (i, j)); break
        i += found[0]; j += found[1]; resync += 1
        continue
    d = np.nonzero(s[i] != ma[j])[0]
    if len(d):
        # a wait loop that ran a different number of times leaves its
        # registers different for a while; report only lasting differences
        if first_bad is None:
            first_bad = (i, j, d)
    else:
        if first_bad is not None and i - first_bad[0] < 64:
            first_bad = None
    if first_bad is not None and i - first_bad[0] >= 64:
        break
    checked += 1
    i += 1; j += 1

print("%d instructions compared, %d resynchronisations" % (checked, resync))
if first_bad is None:
    print("registers agree")
else:
    a, b, d = first_bad
    print("registers differ from simulation record %d (MAME %d), PC %04X:" % (a, b, sp[a]))
    for k in d:
        print("   %-5s sim %04X  MAME %04X" % (NAMES[k], s[a][k], ma[b][k]))
    print("context (PC, then sim / MAME of those registers):")
    for t in range(-8, 4):
        x, y = a + t, b + t
        if 0 <= x < len(s) and 0 <= y < len(ma):
            print("   %04X/%04X  " % (s[x][0], ma[y][0]) +
                  "  ".join("%s %04X/%04X" % (NAMES[k], s[x][k], ma[y][k]) for k in d))

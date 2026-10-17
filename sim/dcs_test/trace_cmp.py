#!/usr/bin/env python3
# trace_cmp.py - compare the DCS DSP's instruction stream with MAME's
#
#   python3 trace_cmp.py sim_trace.txt mame_trace.txt [context]
#
# sim_trace.txt: the simulator's --dcstrace ("cycle PC debt" per instruction,
# "cycle IRQ" where the DSP took an interrupt); mame_trace.txt: MAME's
# debugger trace of :dcs:dcs ("PC: disassembly", noloop).
#
# The streams are lined up on MAME's second start at PC 0 (MAME resets the
# DSP once more during its start-up). Interrupt service sequences (vector to
# the RTI that ends them; MAME's entries are where the PC lands on a vector
# without a jump or call to it) are taken out of both; the rest must match
# instruction for instruction. Then the services are compared one by one,
# with how far apart (in main-stream instructions) each was taken.
#
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

import sys, collections
from array import array

VECTORS = {0x04, 0x08, 0x0C, 0x10, 0x14, 0x18}

def load_sim(p):
    pcs, cyc, irq = array('H'), array('L'), bytearray()
    pend = False
    for ln in open(p):
        f = ln.split()
        if len(f) >= 2 and f[1] == 'IRQ':
            pend = True
            continue
        if len(f) >= 2:
            cyc.append(int(f[0])); pcs.append(int(f[1], 16)); irq.append(pend); pend = False
    return pcs, cyc, irq

def load_mame(p):
    """PCs, interrupt entry flags, RTI addresses, an op text per PC (display)"""
    pcs, irq = array('H'), bytearray()
    rti, optext = set(), {}
    prev_pc, prev_op = -2, ''
    for ln in open(p):
        if ':' not in ln: continue
        a, b = ln.split(':', 1)
        try: pc = int(a.strip().split()[-1], 16)
        except ValueError: continue
        op = b.strip()
        e = (pc in VECTORS and pc != prev_pc + 1 and
             not any(w in prev_op for w in ('JUMP', 'CALL', 'RTS', 'RTI')))
        pcs.append(pc); irq.append(e)
        if op.startswith('RTI') or op.endswith('RTI'): rti.add(pc)
        optext[pc] = op
        prev_pc, prev_op = pc, op
    return pcs, irq, rti, optext

def split(pcs, irq, rti):
    """main stream [(index)] and services [(main position, start index, pcs)]"""
    main, svc = [], []
    k, n = 0, len(pcs)
    while k < n:
        if irq[k]:
            start, depth, seq = k, 1, []
            while k < n and depth:
                if k != start and irq[k]: depth += 1
                seq.append(pcs[k])
                if pcs[k] in rti: depth -= 1
                k += 1
            svc.append((len(main), start, seq))
            continue
        main.append(k)
        k += 1
    return main, svc

def main():
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    s_pc, s_cyc, s_irq = load_sim(sys.argv[1])
    m_pc, m_irq, rti, optext = load_mame(sys.argv[2])
    rm = [k for k in range(min(len(m_pc), 2000000)) if m_pc[k] == 0]
    m0 = rm[1] if len(rm) > 1 else (rm[0] if rm else 0)
    m_pc, m_irq = m_pc[m0:], m_irq[m0:]
    print("sim %d instructions, MAME %d" % (len(s_pc), len(m_pc)))

    n = min(len(s_pc), len(m_pc))
    k = 0
    while k < n and s_pc[k] == m_pc[k]: k += 1
    print("identical for the first %d instructions%s" % (k, "" if k == n else
          " (to cycle %d of the simulation)" % (s_cyc[k] - s_cyc[0])))

    smain, ssvc = split(s_pc, s_irq, rti)
    mmain, msvc = split(m_pc, m_irq, rti)
    sm = array('H', (s_pc[i] for i in smain))
    mm = array('H', (m_pc[i] for i in mmain))
    # walk both main streams; where they part (a wait loop that ran a
    # different number of times), find the nearest point where they agree
    # again for W instructions
    W, K = 48, 400
    i = j = 0
    resync, skipped_s, skipped_m, worst = 0, 0, 0, 0
    first = None
    while i < len(sm) and j < len(mm):
        if sm[i] == mm[j]:
            i += 1; j += 1; continue
        if first is None: first = (i, j)
        found = None
        for t in range(1, K + 1):
            for di in range(t + 1):
                dj = t - di
                a, b = i + di, j + dj
                if a + W <= len(sm) and b + W <= len(mm) and sm[a:a + W].tobytes() == mm[b:b + W].tobytes():
                    found = (di, dj); break
            if found: break
        if not found:
            print("outside interrupts: lost step at simulation %d / MAME %d (cycle %d)" %
                  (i, j, s_cyc[smain[i]] - s_cyc[0]))
            for d in range(-ctx, ctx + 1):
                a = sm[i + d] if 0 <= i + d < len(sm) else None
                b = mm[j + d] if 0 <= j + d < len(mm) else None
                bo = optext.get(mm[j + d], '') if 0 <= j + d < len(mm) else ''
                print("   %+3d  sim %s  MAME %s %s" % (d, ('%04X' % a) if a is not None else '----',
                                                     ('%04X' % b) if b is not None else '----', bo))
            break
        resync += 1; skipped_s += found[0]; skipped_m += found[1]
        worst = max(worst, found[0], found[1])
        i += found[0]; j += found[1]
    k = i
    print("outside interrupts: %d simulation / %d MAME instructions compared, %d places where a loop "
          "ran a different number of times (largest difference %d instructions, %d / %d instructions in all)" %
          (i, j, resync, worst, skipped_s, skipped_m))
    if first:
        print("  first such place: simulation instruction %d (cycle %d)" % (first[0], s_cyc[smain[first[0]]] - s_cyc[0]))
    ni = min(len(ssvc), len(msvc))
    same = sum(1 for a, b in zip(ssvc, msvc) if a[2] == b[2])
    off = collections.Counter(a[0] - b[0] for a, b in zip(ssvc, msvc) if a[0] <= k and b[0] <= k)
    print("interrupts: simulation %d, MAME %d; %d of the first %d services identical" %
          (len(ssvc), len(msvc), same, ni))
    if off:
        print("  taken at (simulation - MAME, main-stream instructions):",
              ", ".join("%+d x%d" % (d, off[d]) for d in sorted(off)))

if __name__ == '__main__':
    main()

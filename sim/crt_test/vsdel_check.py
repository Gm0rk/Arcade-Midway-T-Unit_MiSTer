#!/usr/bin/env python3
# vsdel_check.py - the registered t_over / t_cap2 of rtl/crt_adjust/crt_vsize.sv
# give the same V-Sync delay as the combinational chain they replaced.
#
# Copyright (C) 2026 Gm0rk. Distributed under GNU GPL v3 or later.
#
# A copy of crt_vsize.sv in a temporary directory gets a $display at every
# vs_rise of the old chain (t_over, t_cap2 straight into t_k) next to the
# value the module loads into t_vsdel (t_k, from the registers). The bench of
# tunit_crt runs on the T-Unit raster in Cabinet mode (the only mode that
# loads t_vsdel) for V-Size steps 0-15 with both Video Timings, and in PVM
# mode for four steps; every vs_rise must show the same K. It counts the
# vsyncs and the ones with K > 0 (they must exist, or the check proves nothing).
#   python3 vsdel_check.py [rtl directory]
import os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
RTL = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'rtl')
OLD = ("    wire [9:0] t_k1       = (t_over_r > 10'd24) ? 10'd24 : t_over_r;\n"
       "    wire [9:0] t_k        = (t_k1 > t_cap2_r) ? t_cap2_r : t_k1;\n")
PROBE = ("    wire [9:0] t_k1_o = (t_over > 10'd24) ? 10'd24 : t_over;\n"
         "    wire [9:0] t_k_o  = (t_k1_o > t_cap2) ? t_cap2 : t_k1_o;\n"
         "    always @(posedge clk) if (vs_rise) $display(\"K %0d %0d\", t_k_o, t_k);\n")

def main():
    src = open(os.path.join(RTL, 'crt_adjust', 'crt_vsize.sv'), encoding='utf-8').read()
    if src.count(OLD) != 1:
        sys.exit('crt_vsize.sv: the registered t_k chain was not found')
    tmp = tempfile.mkdtemp(prefix='vsdel_')
    try:
        for d in ('video', 'crt_adjust'):
            os.makedirs(os.path.join(tmp, 'rtl', d))
        for f in ('video/tunit_crt.sv', 'video/sync_center.sv', 'crt_adjust/crt_adjust.sv'):
            shutil.copy(os.path.join(RTL, f), os.path.join(tmp, 'rtl', f))
        open(os.path.join(tmp, 'rtl', 'crt_adjust', 'crt_vsize.sv'), 'w', encoding='utf-8').write(
            src.replace(OLD, OLD + PROBE))
        for f in ('tb_crt.sv', 'crt_tb.cpp'):
            shutil.copy(os.path.join(HERE, f), tmp)
        r = tmp + '/rtl/'
        subprocess.run(['verilator', '--cc', '--exe', '--build', '-j', '2', '-O3', '-Wno-fatal', '-Wno-WIDTH',
                        '-Wno-lint', '--top-module', 'tb_crt', '-o', 'crt_tb', '-CFLAGS', '-O2', 'tb_crt.sv',
                        r + 'video/tunit_crt.sv', r + 'video/sync_center.sv', r + 'crt_adjust/crt_adjust.sv',
                        r + 'crt_adjust/crt_vsize.sv', 'crt_tb.cpp'],
                       cwd=tmp, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        jobs = [(1, vt, vs, 0) for vt in (0, 1) for vs in range(16)] + [(0, 0, vs, 0) for vs in (0, 3, 8, 15)]
        def run(j):
            mode, vt, vs, sh = j
            out = subprocess.run([tmp + '/obj_dir/crt_tb', tmp + '/x%d_%d_%d.bin' % (mode, vt, vs), '32', '3', '1',
                                  '0', '0', str(sh), str(vs), str(mode), str(vt)],
                                 capture_output=True, text=True, timeout=600).stdout
            return [tuple(map(int, m.groups())) for m in re.finditer(r'^K (\d+) (\d+)$', out, re.M)]
        with ThreadPoolExecutor(2) as ex:
            res = list(ex.map(run, jobs))
        n = sum(len(r) for r in res)
        bad = sum(1 for r in res for a, b in r if a != b)
        nz = sum(1 for r in res for a, b in r if a > 0)
        mx = max((a for r in res for a, _ in r), default=0)
        print('%d settings, %d vsyncs: %d with K > 0 (largest %d), %d differ between the chains'
              % (len(jobs), n, nz, mx, bad))
        if bad or nz == 0 or n == 0:
            sys.exit('FAILED')
        print('all checks passed')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

main()

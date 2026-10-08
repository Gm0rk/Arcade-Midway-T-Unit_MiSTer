# rtl/crt — CRT Adjust and CRT V-Size (third party)

Analog CRT geometry controls by **Umberto Parisi (rmonic79)**, with
integration work by **Andrea Bogazzi (@asturur)**, from
[github.com/rmonic79/MiSTer-CRT-Adjust](https://github.com/rmonic79/MiSTer-CRT-Adjust)
at commit `c682de9` (6 August 2026).

| File | What it does |
|---|---|
| `crt_adjust.sv` | H-Size, H-Position and V-Shift through a one-line buffer. The sync stays native, so the monitor never loses lock |
| `crt_vsize.sv` | V-Size, experimental upstream. PVM mode retimes the frame with more or fewer lines; Cabinet mode keeps native timing and rescales the picture in linear light |
| `LICENSE` | GNU General Public License v3 |

Licensed **GPL-3.0-or-later**, which is compatible with the rest of this
core (GPL-2.0-or-later) and makes the combined core GPL-3.0-or-later as
distributed. See the Licence section of the top-level `README.md`.

## How this core uses them

Core-side, inside the `emu` wrapper, through `rtl/video/vunit_crt_out.sv`:

```
core picture -> crt_vsize -> crt_adjust -> arcade_video -> sys/
```

Nothing in `sys/` is modified. Upstream also ships `crt_adjust_sys.sv`, which
is installed by editing `sys_top.v`; it is deliberately **not** included,
because MiSTer-devel cores do not modify the framework.

## Local changes

Every change is marked `V-UNIT` at the point it is made and described in the
file's header. All of them were found by `sim/crt`, and each has a negative
control there: undo it and the harness fails.

**crt_adjust.sv**

1. *Line buffer sized from `HTOTAL`.* The address width was fixed at 10 bits:
   two banks of 512 samples. The write pointer counts every pixel of the line,
   and the V-Unit line is 666 pixels, so the front porch wrapped round onto
   the first 154 samples of the picture and blacked them out. For lines of 512
   pixels or fewer the width is unchanged.
2. *H-Position offset sign-extended.* The offset was built by a conditional
   whose other arm is an unsized replication. That arm is unsigned, which
   makes the whole conditional unsigned (IEEE 1364-2005 §5.5.1), so a
   negative H-Position was zero-extended: −20 became +492. The read address
   still came out right, because it is taken modulo the bank size, but the
   active-window compare did not, and the picture vanished off the end of the
   line. This is likely to affect any core using negative H-Position in
   content-shift mode, if Quartus follows the standard here.

**crt_vsize.sv**

1. *VSync width counter 6 bits, was 4.* A 16-line VSync wrapped the counter
   to zero and the measured width stayed at its default of 3.
2. *Cabinet pipeline sequenced from a delay line.* The eight phases were
   selected by `p_cnt`, which only counts to (clocks per pixel − 1). This core
   has six clocks per pixel, so phases 6 and 7 never happened and Cabinet mode
   produced no picture. Upstream documents a ratio of at least 8 as a
   requirement; the delay line removes it for ratios of 6 and up, and is
   cycle-identical to upstream at 8 and above.
3. *PVM vertical blank set with the sync.* It changed two clocks after the
   output HSync rose, so the next stage sampled the previous line's value on
   the sync edge, and the picture lost its top line and gained a black one at
   the bottom.

## Notes for upstream

Things found here that may matter to other cores:

* the H-Position sign extension above;
* `crt_vsize`'s per-line pixel counter stops at `LINE_PX − 1`, so `LINE_PX`
  must be strictly greater than the active width — at exactly the active
  width every line loses its last pixel;
* the V-Size OSD list in the integration guide has 15 entries
  (`0,+1..+7,−7..−1`) but is decoded as a 4-bit two's-complement value.
  MiSTer stores an option's position in its list, so the entry labelled −7
  is position 8, which decodes as −8 — 24 lines, past the ring's limit of 21 —
  and every negative entry is one step off. This core decodes by position.

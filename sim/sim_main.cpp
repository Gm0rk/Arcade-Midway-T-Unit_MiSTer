//============================================================================
//  Full-board simulation harness (Verilator)
//
//  sim_tunit --game mk --rom0 mk_rom0.bin --rom3 mk_rom3.bin \
//            --frames 600 --snap every:100 --out frames/mk \
//            [--press "400:0:4:5;..."] [--dsw 0xFE7D] [--trace pc.bin:A:B]
//            [--wav out.wav] [--ddr-lat 24] [--ramclear] [--nosound]
//            [--wrlog writes.txt:A:B] [--rdlog] [--debt] [--lag lag.txt]
//            [--info mk_rom1.bin] [--osd "500:0:1;..."]
//            [--vtiming 0|1|2] [--lines lines.txt] [--level ADDR:N] [--lvlwatch ADDR]
//            [--dcslog samples.bin] [--dcstrace dsp.txt:A:B]
//            [--dcsstate regs.bin:A:B]
//
//  --game      mk, mkturbo, mk2, nbajam, nbajamte, jdreddp (the top level's
//              game table: protection, sound RAM window)
//  --rom0/3    ROM streams exactly as the MRA sends them (tools/mra_check.py
//              --out writes them); loaded straight into the SDRAM model at
//              0x000000 and 0xD00000
//  --snap      frames to save (comma list or every:N), RGB1 files of the
//              whole raster (tools/rgbtool.py crops and compares)
//  --press     frame:port:bit:length, ';' separated: input port (0 IN0,
//              1 IN1, 2 IN2) bit held low for length frames, starting at the
//              moment MAME's ports change for a tools/mame/frames.lua PRESS
//              with the same numbers (one frame notification after the one
//              that sets it), so the two runs see the press at the same
//              instruction
//  --trace     write each retired instruction's PC and the machine cycles
//              charged for it (two 32-bit little-endian words) for frames
//              A..B, with markers (0xFFFFFFFF, frame) where each frame
//              starts and (0xFFFFFFFE, frame) where its vertical blank starts
//  --wrlog     log the CPU's writes outside main RAM and VRAM (palette,
//              CMOS, DMA, control, sound) for frames A..B, one line each:
//              frame, line, word address, data (tools/mame/wrlog.lua writes
//              the same from MAME); also a line where each blit starts and
//              ends (the blitter's busy flag), with the clock count
//  --rdlog     also log reads of 0x01600000-0x01FFFFFF (inputs, DMA, sound;
//              not the palette) in the --wrlog file, marked R
//  --debt      also log, per frame, the lowest and the final value of the
//              34010's cycle debt (negative: behind MAME's timing)
//  --lag       write a line each time the 34010 falls further behind real
//              time (machine cycles since reset minus cycles charged for the
//              instructions it has retired): clock, PC, lag
//  --wav       16-bit mono 48 kHz audio of the whole run
//  --nosound   hold the sound board in reset: the T-Unit's ADPCM games
//              never read it back (MAME fakes its status), so the video is
//              the same and the simulation runs faster
//  --info      the ROM index 1 stream (game id and secrets table, written by
//              tools/mra_check.py --out), loaded into the secrets module
//              during reset
//  --dcslog    write every sample the DCS board copies into its DAC queue,
//              with the clock count (64-bit clock, 16-bit sample)
//  --dcstrace  file:A:B - each instruction the DCS DSP retires in frames
//              A..B: the board's 10 MHz cycle count, the PC, the DSP's
//              cycle debt (tools: compare with a MAME trace of :dcs:dcs)
//  --dcsstate  file:A:B - DSP instructions A..B (counted from the start):
//              PC and registers after each (sim/dcs_test/state_cmp.py)
//  DCS_DUMP    (environment) file: the DCS board's external RAM, bits
//              23-8, at the end of the run
//  --osd       frame:item:length, ';' separated: OSD Secrets page items,
//              timed like --press; item 0 and 1 are the triggers R[14] and
//              R[15] (code 1 and 2), 2-12 the option slots 1-11 of the
//              secrets module
//  --level     Fixed AI Difficulty on: ADDR is the AI level word's bit
//              address (hex, e.g. 010519C0 in MK, 01061AD0 in MK2), N the
//              level 0-9
//  --lvlwatch  log the CPU's reads and writes of the word at bit address ADDR
//              (hex; with --level, its address): frame, R or W, value read
//              or written, to stderr (the first 400), and a summary at the end
//  --vtiming   the OSD's Video Timing: 0 native 289-line frames (54.7 Hz),
//              1 277 lines (57 Hz), 2 263 lines (60 Hz)
//  --lines     write a line per frame: frame, lines from one VSync to the
//              next, clocks (96 MHz) from one VSync to the next
//
//  The DDR3 port is a model of MiSTer's DDRAM interface: reads return
//  their burst after a fixed latency, writes are accepted one beat per
//  clock; both stall now and then (busy) to exercise the handshakes.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <string>
#include <vector>
#include <set>
#include <deque>

#include "Vsim_top.h"
#include "Vsim_top___024root.h"
#include "Vsim_top_sim_top.h"
#include "Vsim_top_sdram_model.h"
#include "verilated.h"

static Vsim_top *top;

// 34010 machine cycles per frame: 50 MHz / 8 x 289 lines x 506 pixels / 8 MHz
static const double CYC_PER_FRAME = 6250000.0 * 289.0 * 506.0 / 8000000.0;

//----------------------------------------------------------------------------
// DDR3 model (1 MB VRAM window at beat 0x06000000)
//----------------------------------------------------------------------------

struct Ddr {
	std::vector<uint64_t> mem = std::vector<uint64_t>(1 << 20);   // 8 MB, plenty
	int lat = 24;
	// read requests in flight: (ready cycle, address, beats)
	struct Rd { uint64_t ready; uint32_t addr; int beats; };
	std::deque<Rd> rds;
	int wr_left = 0;
	uint32_t wr_addr = 0;
	uint64_t cyc = 0;
	uint32_t lfsr = 0x1234567;

	uint32_t idx(uint32_t beat) { return (beat - 0x06000000u) & 0xFFFFF; }

	// core outputs as they stand before the clock edge
	bool s_rd, s_we, s_busy;
	uint32_t s_addr;
	int s_cnt;
	uint64_t s_din;
	uint8_t s_be;

	void pre() {
		s_rd = top->ddr_rd; s_we = top->ddr_we; s_busy = top->ddr_busy;
		s_addr = top->ddr_addr; s_cnt = top->ddr_burstcnt ? top->ddr_burstcnt : 256;
		s_din = top->ddr_din; s_be = top->ddr_be;
	}

	// the edge: accept what the core offered while not busy, then set the
	// outputs for the next clock
	void post() {
		cyc++;
		if (s_rd && !s_busy)
			rds.push_back({cyc + lat, s_addr, s_cnt});
		if (s_we && !s_busy) {
			if (wr_left == 0) { wr_addr = s_addr; wr_left = s_cnt; }
			uint64_t &m = mem[idx(wr_addr)];
			for (int b = 0; b < 8; b++)
				if (s_be & (1 << b))
					m = (m & ~(0xFFull << (8 * b))) | (s_din & (0xFFull << (8 * b)));
			wr_addr++;
			wr_left--;
		}
		// read data: one beat per clock from the oldest request
		top->ddr_dout_ready = 0;
		if (!rds.empty() && rds.front().ready <= cyc) {
			Rd &r = rds.front();
			top->ddr_dout = mem[idx(r.addr)];
			top->ddr_dout_ready = 1;
			r.addr++;
			if (--r.beats == 0) rds.pop_front();
		}
		// busy: random short stalls (about 1 clock in 16)
		lfsr = lfsr * 1103515245u + 12345u;
		top->ddr_busy = ((lfsr >> 20) & 15) == 0;
	}
};

//----------------------------------------------------------------------------
// Frames
//----------------------------------------------------------------------------

struct Frames {
	static const int W = 512, H = 300;
	std::vector<uint8_t> buf = std::vector<uint8_t>(W * H * 3);
	int x = 0, y = 0, maxx = 0, maxy = 0;
	int last_lines = 0;                  // lines of the frame that just ended
	bool hs_d = false, vs_d = false;
	int frame = 0;
	std::set<int> want;
	int every = 0;
	std::string dir;

	void save() {
		char name[512];
		snprintf(name, sizeof name, "%s/f%05d.rgb", dir.c_str(), frame);
		FILE *f = fopen(name, "wb");
		if (!f) return;
		uint32_t hdr[3] = { (uint32_t)W, (uint32_t)H, (uint32_t)frame };
		fwrite("RGB1", 1, 4, f);
		fwrite(hdr, 4, 3, f);
		fwrite(buf.data(), 1, buf.size(), f);
		fclose(f);
	}

	// returns true at the start of a new frame
	bool pixel() {
		bool newframe = false;
		bool hs = top->vid_hs, vs = top->vid_vs;
		if (hs && !hs_d) { x = 0; y++; }
		if (vs && !vs_d) {
			frame++;
			newframe = true;
			if (want.count(frame - 1) || (every && (frame - 1) % every == 0 && frame > 1)) {
				int keep = frame;
				frame = frame - 1;
				save();
				frame = keep;
			}
			std::fill(buf.begin(), buf.end(), 0);
			last_lines = y;
			y = 0;
		}
		hs_d = hs; vs_d = vs;
		if (x < W && y < H) {
			uint8_t *p = &buf[(y * W + x) * 3];
			p[0] = top->vid_r; p[1] = top->vid_g; p[2] = top->vid_b;
		}
		x++;
		return newframe;
	}
};

//----------------------------------------------------------------------------
// WAV output
//----------------------------------------------------------------------------

struct Wav {
	FILE *f = nullptr;
	uint32_t n = 0;
	void open(const char *path) {
		f = fopen(path, "wb");
		uint8_t hdr[44] = {0};
		fwrite(hdr, 1, 44, f);
	}
	void put(int16_t s) { if (f) { fwrite(&s, 2, 1, f); n++; } }
	void close() {
		if (!f) return;
		auto le32 = [](uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; };
		uint8_t h[44];
		memcpy(h, "RIFF", 4); le32(h + 4, 36 + n * 2); memcpy(h + 8, "WAVEfmt ", 8);
		le32(h + 16, 16); h[20] = 1; h[21] = 0; h[22] = 1; h[23] = 0;
		le32(h + 24, 48000); le32(h + 28, 96000); h[32] = 2; h[33] = 0; h[34] = 16; h[35] = 0;
		memcpy(h + 36, "data", 4); le32(h + 40, n * 2);
		fseek(f, 0, SEEK_SET); fwrite(h, 1, 44, f); fclose(f);
	}
};

//----------------------------------------------------------------------------

static std::vector<uint8_t> load(const char *path) {
	std::vector<uint8_t> d;
	FILE *f = fopen(path, "rb");
	if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
	uint8_t b[65536];
	size_t n;
	while ((n = fread(b, 1, sizeof b, f)) > 0) d.insert(d.end(), b, b + n);
	fclose(f);
	return d;
}

struct Press { int frame, port, bit, len; };

int main(int argc, char **argv) {
	Verilated::commandArgs(argc, argv);
	std::string game = "mk", rom0, rom3, out = "frames", snap = "", presses = "", wav = "", trace = "", wrlog = "", lagpath = "";
	std::string info, osds, dcslog, linespath, dcstrace, dcsstate;
	int frames = 100, dsw = -1, vtiming = 0;
	bool lvl_on = false, lvl_watch = false; uint32_t lvl_addr = 0; int lvl_val = 0;
	long lvl_r = 0, lvl_w = 0, lvl_hist[16] = {0}, lvl_lines = 0;
	bool ramclear = false, nosound = false, rdlog = false, debtlog = false;
	Ddr ddr;
	for (int i = 1; i < argc; i++) {
		std::string a = argv[i];
		auto next = [&]() { return std::string(argv[++i]); };
		if (a == "--game") game = next();
		else if (a == "--rom0") rom0 = next();
		else if (a == "--rom3") rom3 = next();
		else if (a == "--frames") frames = atoi(next().c_str());
		else if (a == "--snap") snap = next();
		else if (a == "--out") out = next();
		else if (a == "--press") presses = next();
		else if (a == "--dsw") dsw = strtol(next().c_str(), nullptr, 0);
		else if (a == "--wav") wav = next();
		else if (a == "--trace") trace = next();
		else if (a == "--wrlog") wrlog = next();
		else if (a == "--rdlog") rdlog = true;
		else if (a == "--debt") debtlog = true;
		else if (a == "--lag") lagpath = next();
		else if (a == "--ddr-lat") ddr.lat = atoi(next().c_str());
		else if (a == "--ramclear") ramclear = true;
		else if (a == "--nosound") nosound = true;
		else if (a == "--info") info = next();
		else if (a == "--osd") osds = next();
		else if (a == "--dcslog") dcslog = next();
		else if (a == "--dcstrace") dcstrace = next();
		else if (a == "--dcsstate") dcsstate = next();
		else if (a == "--vtiming") vtiming = atoi(next().c_str());
		else if (a == "--lvlwatch") { lvl_watch = true; lvl_addr = strtoul(next().c_str(), nullptr, 16) >> 4; }
		else if (a == "--level") {
			lvl_watch = true;
			std::string v = next(); size_t c = v.find(':');
			lvl_on = true; lvl_addr = strtoul(v.substr(0, c).c_str(), nullptr, 16) >> 4;
			lvl_val = c == std::string::npos ? 0 : atoi(v.substr(c + 1).c_str());
		}
		else if (a == "--lines") linespath = next();
	}

	top = new Vsim_top;
	auto &mem = top->rootp->sim_top->sdram_chip->mem;

	// ROM streams into the SDRAM model (16-bit words, little endian)
	auto r0 = load(rom0.c_str());
	for (size_t i = 0; i + 1 < r0.size(); i += 2) mem[i / 2] = r0[i] | (r0[i + 1] << 8);
	auto r3 = load(rom3.c_str());
	for (size_t i = 0; i + 1 < r3.size(); i += 2) mem[(0xD00000 + i) / 2] = r3[i] | (r3[i + 1] << 8);

	// the top level's game table
	int gfx_mb = (int)((r0.size() - 0x100000 + 0xFFFFF) >> 20);
	top->gfx_mb = gfx_mb > 12 ? 12 : gfx_mb;
	top->prot_id = 0; top->mk_turbo = 0; top->big_rom = 0; top->dcs = 0;
	top->sprot_start = 0xFFFF; top->sprot_end = 0;
	int def_dsw = 0xFFFF;
	if (game == "mk" || game == "mkturbo") {
		top->prot_id = 1; top->mk_turbo = (game == "mkturbo");
		top->sprot_start = 0xFB9C; top->sprot_end = 0xFBC6; def_dsw = 0xFE7D;
	} else if (game == "mk2") {
		top->prot_id = 5; top->big_rom = 1; top->dcs = 1; def_dsw = 0xFC7D;
	} else if (game == "nbajam") {
		top->prot_id = 2; top->sprot_start = 0xFBAA; top->sprot_end = 0xFBD4; def_dsw = 0x7FFD;
	} else if (game == "nbajamte") {
		top->prot_id = 3; top->sprot_start = 0xFBEC; top->sprot_end = 0xFC16; def_dsw = 0x7FFD;
	} else if (game == "jdreddp") {
		top->prot_id = 4; top->sprot_start = 0xFBCF; top->sprot_end = 0xFBF9; def_dsw = 0x5CFF;
	}
	if (dsw < 0) dsw = def_dsw;

	std::vector<Press> press;
	for (size_t p = 0; p < presses.size();) {
		size_t e = presses.find(';', p);
		std::string item = presses.substr(p, e == std::string::npos ? std::string::npos : e - p);
		Press pr;
		if (sscanf(item.c_str(), "%d:%d:%d:%d", &pr.frame, &pr.port, &pr.bit, &pr.len) == 4) press.push_back(pr);
		if (e == std::string::npos) break;
		p = e + 1;
	}

	std::vector<Press> osd;                  // port unused; bit = item
	for (size_t p = 0; p < osds.size();) {
		size_t e = osds.find(';', p);
		std::string item = osds.substr(p, e == std::string::npos ? std::string::npos : e - p);
		Press pr;
		pr.port = 0;
		if (sscanf(item.c_str(), "%d:%d:%d", &pr.frame, &pr.bit, &pr.len) == 3) osd.push_back(pr);
		if (e == std::string::npos) break;
		p = e + 1;
	}
	std::vector<uint8_t> info_d;
	if (!info.empty()) info_d = load(info.c_str());

	Frames fr;
	fr.dir = out;
	if (snap.rfind("every:", 0) == 0) fr.every = atoi(snap.c_str() + 6);
	else for (size_t p = 0; p < snap.size();) {
		size_t e = snap.find(',', p);
		fr.want.insert(atoi(snap.substr(p, e - p).c_str()));
		if (e == std::string::npos) break;
		p = e + 1;
	}
	std::string mk = "mkdir -p '" + out + "'";
	if (system(mk.c_str())) {}

	Wav w;
	if (!wav.empty()) w.open(wav.c_str());

	FILE *tf = nullptr;
	int tr_a = 0, tr_b = 0;
	if (!trace.empty()) {
		char path[512];
		if (sscanf(trace.c_str(), "%511[^:]:%d:%d", path, &tr_a, &tr_b) == 3) tf = fopen(path, "wb");
	}

	FILE *wf = nullptr;
	int wr_a = 0, wr_b = 0;
	if (!wrlog.empty()) {
		char path[512];
		if (sscanf(wrlog.c_str(), "%511[^:]:%d:%d", path, &wr_a, &wr_b) == 3) wf = fopen(path, "w");
	}

	top->in_ports = ((uint64_t)dsw << 48) | 0xFFFFFFFFFFFFull;
	top->info_start = 0; top->info_wr = 0; top->info_addr = 0; top->info_data = 0;
	top->osd_trig = 0; top->osd_opt = 0;
	top->pause = 0;
	top->vtiming = vtiming & 3;
	top->lvl_on = lvl_on; top->lvl_addr = lvl_addr; top->lvl_val = lvl_val & 15;
	top->ram_clr_req = 0;
	top->snd_off = nosound;
	top->reset = 1;
	top->clk = 0;
	top->eval();

	uint64_t cyc = 0;
	FILE *linesf = linespath.empty() ? nullptr : fopen(linespath.c_str(), "w");
	uint64_t lines_cyc = 0;
	int wav_div = 0;
	bool blit_d = false, vb_d = false;
	int in_frame = -1;
	int32_t debt_min = 0;
	int debt_frame = 0;
	uint64_t retired = 0;
	double charged = 0;
	FILE *lagf = lagpath.empty() ? nullptr : fopen(lagpath.c_str(), "w");
	// --dcslog: every sample the DCS board copies into its DAC queue, as
	// (clock count, sample) pairs (64-bit, 16-bit, little endian)
	FILE *dcsf = dcslog.empty() ? nullptr : fopen(dcslog.c_str(), "wb");
	FILE *dcstf = nullptr;
	int dt_a = 0, dt_b = 0;
	FILE *dcssf = nullptr;
	uint64_t ds_a = 0, ds_b = 0, dcs_n = 0;
	if (!dcsstate.empty()) {
		char fn[512] = {0};
		unsigned long long a = 0, b = 0;
		sscanf(dcsstate.c_str(), "%511[^:]:%llu:%llu", fn, &a, &b);
		ds_a = a; ds_b = b;
		dcssf = fopen(fn, "wb");
	}
	if (!dcstrace.empty()) {
		char fn[512] = {0};
		sscanf(dcstrace.c_str(), "%511[^:]:%d:%d", fn, &dt_a, &dt_b);
		dcstf = fopen(fn, "w");
	}
	int lag_max = 0;                         // 34010 machine cycles of retired instructions
	int last_report = -1;
	while (fr.frame <= frames) {
		// reset until the SDRAM has finished its power-up sequence (12100
		// clocks in rtl/sdram.sv), as in the core, where the board leaves reset
		// long after it; then optionally the main RAM clear. Starting the
		// 34010 earlier would leave it waiting ~780 machine cycles for its
		// reset vector while the raster runs, a phase MAME does not have.
		if (cyc == 13000) {
			top->reset = 0;
			if (ramclear) top->ram_clr_req = 1;
		}

		// the secrets table, one word per clock during reset (as the ROM
		// index 1 download: a start pulse, then the words)
		top->info_start = (cyc == 100);
		top->info_wr = 0;
		if (cyc >= 200 && (cyc - 200) * 2 + 1 < info_d.size() && (cyc - 200) < 512) {
			size_t i = (cyc - 200) * 2;
			top->info_wr = 1;
			top->info_addr = (uint32_t)(cyc - 200);
			top->info_data = info_d[i] | (info_d[i + 1] << 8);
		}

		// inputs: MAME's ports take a value frames.lua sets at its frame
		// notification N at the next notification, N + 1, which comes when
		// the 34010 has run (N + 1) frames of machine cycles (MAME starts the
		// CPU with the raster and never loses time). The simulator presses at
		// the same point of the CPU's own cycle count (the cycles charged for
		// the instructions it has retired), so both runs see the press at the
		// same instruction whatever phase the CPU has against the raster.
		{
			int f = (int)(charged / CYC_PER_FRAME);           // notifications passed
			if (f != in_frame) {
				in_frame = f;
				uint64_t in = ((uint64_t)dsw << 48) | 0xFFFFFFFFFFFFull;
				for (auto &p : press)
					if (in_frame > p.frame && in_frame <= p.frame + p.len)
						in &= ~(1ull << (p.port * 16 + p.bit));
				top->in_ports = in;
				uint32_t items = 0;
				for (auto &o : osd)
					if (in_frame > o.frame && in_frame <= o.frame + o.len)
						items |= 1u << o.bit;
				top->osd_trig = items & 3;
				top->osd_opt  = (items >> 2) & 0x7FF;
			}
		}

		ddr.pre();
		bool ce = top->ce_pix;             // the video outputs change on this edge
		top->clk = 1;
		top->eval();
		ddr.post();
		top->clk = 0;
		top->eval();
		cyc++;

		bool newframe = ce && fr.pixel();
		if (newframe && linesf) {
			fprintf(linesf, "%d %d %llu\n", fr.frame - 1, fr.last_lines, (unsigned long long)(cyc - lines_cyc));
			lines_cyc = cyc;
		}
		// trace markers: (0xFFFFFFFF, frame) at the start of each frame (VSync),
		// (0xFFFFFFFE, frame) where its vertical blank starts
		if (tf && fr.frame >= tr_a && fr.frame <= tr_b) {
			if (newframe) { uint32_t rec[2] = { 0xFFFFFFFFu, (uint32_t)fr.frame }; fwrite(rec, 4, 2, tf); }
			if (top->vid_vb && !vb_d) { uint32_t rec[2] = { 0xFFFFFFFEu, (uint32_t)fr.frame }; fwrite(rec, 4, 2, tf); }
		}
		vb_d = top->vid_vb;
		if (top->dbg_retire) {
			retired++;
			charged += top->rootp->sim_top->board__DOT__cpu__DOT__dbg_cycles;
			if (lagf) {
				// lag of the CPU behind real time since reset, in machine cycles
				double real = (cyc - 13000) * 6.25 / 96.0;
				int lag = (int)(real - charged);
				if (lag > lag_max + 8) { fprintf(lagf, "%llu %08X lag %d\n", (unsigned long long)cyc, top->dbg_pc, lag); lag_max = lag; }
			}
			if (tf && fr.frame >= tr_a && fr.frame <= tr_b) {
				uint32_t rec[2] = { top->dbg_pc, top->rootp->sim_top->board__DOT__cpu__DOT__dbg_cycles };
				fwrite(rec, 4, 2, tf);
			}
		}
		if (wf && top->dbg_blit_busy != blit_d && fr.frame >= wr_a && fr.frame <= wr_b)
			fprintf(wf, "%d %d %s %llu\n", fr.frame, fr.y, top->dbg_blit_busy ? "blit-start" : "blit-end",
			        (unsigned long long)cyc);
		blit_d = top->dbg_blit_busy;
		if (lvl_watch && (top->dbg_rd || top->dbg_wr) && top->dbg_wa == lvl_addr) {
			bool rd = top->dbg_rd;
			unsigned v = rd ? top->dbg_rdata : top->dbg_wdata;
			if (rd) { lvl_r++; lvl_hist[v & 15]++; } else lvl_w++;
			if (lvl_lines++ < 400) fprintf(stderr, "lvl %d %c %04X\n", fr.frame, rd ? 'R' : 'W', v);
		}
		if (wf && top->dbg_wr && fr.frame >= wr_a && fr.frame <= wr_b) {
			uint32_t wa = top->dbg_wa;
			bool ram = (wa >> 18) == 0x004, vram = (wa >> 18) == 0;
			if (!ram && !vram)
				fprintf(wf, "%d %d %07X %04X\n", fr.frame, fr.y, wa, top->dbg_wdata);
		}
		if (wf && rdlog && top->dbg_rd && fr.frame >= wr_a && fr.frame <= wr_b) {
			uint32_t wa = top->dbg_wa;
			if (wa >= 0x0160000 && wa < 0x0200000 && (wa >> 15) != 0x30)   // inputs .. sound, not palette
				fprintf(wf, "%d %d %07X %04X R\n", fr.frame, fr.y, wa, top->dbg_rdata);
		}
		if (++wav_div == 2000) { wav_div = 0; w.put((int16_t)top->audio); }
		if (dcsf && top->dbg_dcs_we) {
			uint64_t c = cyc; int16_t v = (int16_t)top->dbg_dcs_smp;
			fwrite(&c, 8, 1, dcsf); fwrite(&v, 2, 1, dcsf);
		}
		// --dcstrace: each instruction the DCS DSP retires in frames A..B, with
		// the board's 10 MHz cycle count and the DSP's cycle debt
		if (dcstf && top->dbg_dcs_valid && fr.frame >= dt_a && fr.frame <= dt_b)
			fprintf(dcstf, "%u %04X %d\n", top->dbg_dcs_cyc, top->dbg_dcs_pc, (int16_t)top->dbg_dcs_debt);
		if (dcstf && top->dbg_dcs_irq && fr.frame >= dt_a && fr.frame <= dt_b)
			fprintf(dcstf, "%u IRQ\n", top->dbg_dcs_cyc);
		// --dcsstate: per retired instruction its PC and the registers after it
		// (32 16-bit words, MAME's ADSP_LOG layout: pc, AX0 AX1 AY0 AY1 AR AF
		// MX0 MX1 MY0 MY1 MR0 MR1 MR2 MF SI SE SB SR0 SR1, ASTAT PX CNTR,
		// I0-I7, MSTAT)
		if (dcssf && top->dbg_dcs_valid && dcs_n >= ds_a && dcs_n < ds_b) {
			auto *rp = top->rootp;
			int bank = rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__mstat & 1;
			const auto &rf = bank ? rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__rf1
			                      : rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__rf0;
			auto f16 = [&](int k) { return (uint16_t)((rf[(k * 16) >> 5] >> ((k * 16) & 31)) & 0xffff); };
			// rf order: AX0 AX1 MX0 MX1 AY0 AY1 MY0 MY1 SI SE AR MR0 MR1 MR2 SR0 SR1 AF MF SB
			uint16_t r[32];
			r[0] = top->dbg_dcs_pc;
			r[1] = f16(0); r[2] = f16(1); r[3] = f16(4); r[4] = f16(5); r[5] = f16(10); r[6] = f16(16);
			r[7] = f16(2); r[8] = f16(3); r[9] = f16(6); r[10] = f16(7); r[11] = f16(11); r[12] = f16(12);
			r[13] = f16(13); r[14] = f16(17); r[15] = f16(8); r[16] = f16(9); r[17] = f16(18); r[18] = f16(14);
			r[19] = f16(15);
			r[20] = rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__astat;
			r[21] = rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__px;
			r[22] = rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__cntr;
			const auto &ir = rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__ir;
			for (int k = 0; k < 8; k++) {
				uint32_t v = 0;
				for (int b = 0; b < 15; b++) { int bit = k * 15 + b; v |= ((ir[bit >> 5] >> (bit & 31)) & 1) << b; }
				r[23 + k] = v;
			}
			r[31] = rp->sim_top->dcs_board__DOT__board__DOT__dsp__DOT__mstat;
			fwrite(r, 2, 32, dcssf);
		}
		if (top->dbg_dcs_valid) dcs_n++;
		if (debtlog) {
			// the 34010's cycle debt (rtl/tms34010): below zero the CPU is behind
			// MAME's instruction timing (memory slower than the cycle counts)
			int32_t d = top->rootp->sim_top->board__DOT__cpu__DOT__debt;
			d = (d << 8) >> 8;
			if (d < debt_min) debt_min = d;
			if (fr.frame != debt_frame) {
				if (wf && debt_frame >= wr_a && debt_frame <= wr_b)
					fprintf(wf, "%d debt min %d end %d\n", debt_frame, debt_min, d);
				debt_frame = fr.frame;
				debt_min = d;
			}
		}
		if (fr.frame != last_report && fr.frame % 10 == 0) {
			last_report = fr.frame;
			fprintf(stderr, "frame %d  cycles %llu  instructions %llu  pc %08X\n", fr.frame,
			        (unsigned long long)cyc, (unsigned long long)retired, top->dbg_pc);
		}
	}
	w.close();
	if (dcsf) fclose(dcsf);
	if (dcstf) fclose(dcstf);
	if (dcssf) fclose(dcssf);
	if (getenv("DCS_DUMP")) {
		// the DCS board's external RAM (bits 23-8) at the end of the run
		FILE *f = fopen(getenv("DCS_DUMP"), "wb");
		for (int a = 0; a < 2048; a++) {
			uint16_t v = top->rootp->sim_top->dcs_board__DOT__board__DOT__eph__DOT__mem[a];
			fwrite(&v, 2, 1, f);
		}
		fclose(f);
	}
	if (lvl_watch) {
		fprintf(stderr, "lvl summary: %ld reads, %ld writes; values read:", lvl_r, lvl_w);
		for (int i = 0; i < 16; i++) if (lvl_hist[i]) fprintf(stderr, " %d x%ld", i, lvl_hist[i]);
		fprintf(stderr, "\n");
	}
	if (tf) fclose(tf);
	if (linesf) fclose(linesf);
	if (wf) fclose(wf);
	top->final();
	delete top;
	return 0;
}

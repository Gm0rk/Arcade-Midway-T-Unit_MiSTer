//============================================================================
//  MAME's T-Unit blitter as a reference model (midtunit_v.cpp, MAME 0.289)
//
//  dma_w and dma_draw transcribed with the template parameters turned into
//  run-time arguments; the arithmetic, the order of operations and the
//  integer types are MAME's. Used by dma_tb.cpp to check rtl/tunit_dma.sv.
//
//  Original code: license BSD-3-Clause, copyright-holders Alex Pasadyn,
//  Zsolt Vasvari, Ernesto Corvi, Aaron Giles.
//============================================================================

#pragma once
#include <cstdint>
#include <vector>

struct MameDma {
	enum { PIXEL_SKIP = 0, PIXEL_COLOR = 1, PIXEL_COPY = 2 };
	enum { DMA_LRSKIP = 0, DMA_COMMAND, DMA_OFFSETLO, DMA_OFFSETHI, DMA_XSTART,
	       DMA_YSTART, DMA_WIDTH, DMA_HEIGHT, DMA_PALETTE, DMA_COLOR, DMA_SCALE_X,
	       DMA_SCALE_Y, DMA_TOPCLIP, DMA_BOTCLIP, DMA_UNKNOWN_E, DMA_CONFIG,
	       DMA_LEFTCLIP, DMA_RIGHTCLIP };
	static constexpr uint32_t XPOSMASK = 0x3ff, YPOSMASK = 0x1ff;

	const uint8_t *gfxrom;          // the "video" region (padded at the end)
	uint16_t *vram;                 // m_local_videoram, 0x80000 entries
	bool gfx_rom_large = false;
	uint16_t reg[18] = {0};

	struct {
		uint32_t offset; int32_t xpos, ypos, width, height;
		uint16_t palette, color;
		uint8_t yflip, preskip, postskip;
		int32_t topclip, botclip, leftclip, rightclip, startskip, endskip;
		uint16_t xstep, ystep;
	} st;

	int pixels = 0;                 // for the completion time

	uint32_t extract(uint32_t o, int m) const {
		return ((gfxrom[o >> 3] | (gfxrom[(o >> 3) + 1] << 8)) >> (o & 7)) & m;
	}

	void draw(int BitsPerPixel, bool XFlip, bool Skip, bool Scale, int Zero, int NonZero) {
		int const height = st.height << 8;
		uint32_t offset = st.offset;
		uint16_t pal = st.palette;
		uint16_t color = pal | st.color;
		int sy = st.ypos;
		int iy = 0;
		int ty;
		int const mask = (1 << BitsPerPixel) - 1;
		int const xstep = Scale ? st.xstep : 0x100;

		while (iy < height) {
			int const startskip = st.startskip << 8;
			int endskip = st.endskip << 8; (void)endskip;
			int width = st.width << 8;
			int sx = st.xpos;
			int ix = 0;
			int tx;
			uint32_t o = offset;
			int pre = 0, post = 0;
			uint16_t *d;

			if (Skip) {
				uint8_t const value = extract(o, 0xff);
				o += 8;
				pre = (value & 0x0f) << (st.preskip + 8);
				tx = pre / xstep;
				if (XFlip) sx = (sx - tx) & XPOSMASK;
				else       sx = (sx + tx) & XPOSMASK;
				ix += tx * xstep;
				post = ((value >> 4) & 0x0f) << (st.postskip + 8);
				width -= post;
				endskip -= post;
			}

			if (sy < st.topclip || sy > st.botclip)
				goto clipy;

			if (ix < startskip) {
				tx = ((startskip - ix) / xstep) * xstep;
				ix += tx;
				o += (tx >> 8) * BitsPerPixel;
			}

			if ((width >> 8) > st.width - st.endskip)
				width = (st.width - st.endskip) << 8;

			d = &vram[sy * 512];

			while (ix < width) {
				if (sx >= st.leftclip && sx <= st.rightclip) {
					if (Zero == NonZero) {
						if (Zero == PIXEL_COLOR) d[sx] = color;
						else if (Zero == PIXEL_COPY) d[sx] = extract(o, mask) | pal;
					} else {
						int pixel = extract(o, mask);
						if (pixel) {
							if (NonZero == PIXEL_COLOR) d[sx] = color;
							else if (NonZero == PIXEL_COPY) d[sx] = pixel | pal;
						} else {
							if (Zero == PIXEL_COLOR) d[sx] = color;
							else if (Zero == PIXEL_COPY) d[sx] = pal;
						}
					}
				}
				if (XFlip) sx = (sx - 1) & XPOSMASK;
				else       sx = (sx + 1) & XPOSMASK;
				if (!Scale) {
					ix += 0x100;
					o += BitsPerPixel;
				} else {
					tx = ix >> 8;
					ix += xstep;
					tx = (ix >> 8) - tx;
					o += BitsPerPixel * tx;
				}
			}

		clipy:
			if (st.yflip) sy = (sy - 1) & YPOSMASK;
			else          sy = (sy + 1) & YPOSMASK;
			if (!Scale) {
				iy += 0x100;
				width = st.width;
				if (Skip) {
					offset += 8;
					width -= (pre + post) >> 8;
					if (width > 0) offset += width * BitsPerPixel;
				} else {
					offset += width * BitsPerPixel;
				}
			} else {
				ty = iy >> 8;
				iy += st.ystep;
				ty = (iy >> 8) - ty;
				if (!Skip) {
					offset += ty * st.width * BitsPerPixel;
				} else if (ty--) {
					o = offset + 8;
					width = st.width - ((pre + post) >> 8);
					if (width > 0) o += width * BitsPerPixel;
					while (ty--) {
						uint8_t const value = extract(o, 0xff);
						o += 8;
						pre = (value & 0x0f) << st.preskip;
						post = ((value >> 4) & 0x0f) << st.postskip;
						width = st.width - pre - post;
						if (width > 0) o += width * BitsPerPixel;
					}
					offset = o;
				}
			}
		}
	}

	// returns true if a blit was started (and drawn)
	bool write(int offset, uint16_t data) {
		static const uint8_t register_map[2][16] = {
			{ 0,1,2,3,4,5,6,7,8,9,10,11,16,17,14,15 },
			{ 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 }
		};
		int const regbank = (reg[DMA_CONFIG] >> 5) & 1;
		int regnum = register_map[regbank][offset];
		reg[regnum] = data;
		if (regnum != DMA_COMMAND) return false;
		int const command = reg[DMA_COMMAND];
		if (!(command & 0x8000)) return false;

		int const bpp = (command >> 12) & 7;
		st.xpos = reg[DMA_XSTART] & XPOSMASK;
		st.ypos = reg[DMA_YSTART] & YPOSMASK;
		st.width = reg[DMA_WIDTH] & 0x3ff;
		st.height = reg[DMA_HEIGHT] & 0x3ff;
		st.palette = reg[DMA_PALETTE] & 0x7f00;
		st.color = reg[DMA_COLOR] & 0xff;
		st.yflip = (command & 0x20) >> 5;
		st.preskip = (command >> 8) & 3;
		st.postskip = (command >> 10) & 3;
		st.xstep = reg[DMA_SCALE_X] ? reg[DMA_SCALE_X] : 0x100;
		st.ystep = reg[DMA_SCALE_Y] ? reg[DMA_SCALE_Y] : 0x100;
		st.topclip = reg[DMA_TOPCLIP] & 0x1ff;
		st.botclip = reg[DMA_BOTCLIP] & 0x1ff;
		st.leftclip = reg[DMA_LEFTCLIP] & 0x3ff;
		st.rightclip = reg[DMA_RIGHTCLIP] & 0x3ff;

		uint32_t gfxoffset = reg[DMA_OFFSETLO] | (reg[DMA_OFFSETHI] << 16);
		if ((command & 0x0f) == 0x0c) gfxoffset = 0;
		if (!gfx_rom_large && gfxoffset >= 0x2000000) gfxoffset -= 0x2000000;
		if (gfxoffset >= 0xf8000000) gfxoffset -= 0xf8000000;
		pixels = 0;
		if (gfxoffset < 0x10000000) st.offset = gfxoffset;
		else return true;

		if (command & 0x40) {
			st.startskip = reg[DMA_LRSKIP] & 0xff;
			st.endskip = reg[DMA_LRSKIP] >> 8;
		} else {
			st.startskip = 0;
			st.endskip = reg[DMA_LRSKIP];
		}

		// the draw function for (command & 0x1f) and bpp (INIT_TEMPLATED_DMA_DRAW_GROUP)
		static const int zero[16]    = {-1, PIXEL_COPY, PIXEL_SKIP, PIXEL_COPY, PIXEL_COLOR, PIXEL_COLOR,
		                                PIXEL_COLOR, PIXEL_COLOR, PIXEL_SKIP, PIXEL_COPY, PIXEL_SKIP,
		                                PIXEL_COPY, PIXEL_COLOR, PIXEL_COLOR, PIXEL_COLOR, PIXEL_COLOR};
		static const int nonzero[16] = {-1, PIXEL_SKIP, PIXEL_COPY, PIXEL_COPY, PIXEL_SKIP, PIXEL_SKIP,
		                                PIXEL_COPY, PIXEL_COPY, PIXEL_COLOR, PIXEL_COLOR, PIXEL_COLOR,
		                                PIXEL_COLOR, PIXEL_COLOR, PIXEL_COLOR, PIXEL_COLOR, PIXEL_COLOR};
		int m = command & 0x0f;
		bool scale = !(st.xstep == 0x100 && st.ystep == 0x100);
		if (m != 0)
			draw(bpp ? bpp : 8, command & 0x10, command & 0x80, scale, zero[m], nonzero[m]);
		if (!scale)
			pixels = st.width * st.height;
		else
			pixels = ((st.width << 8) / st.xstep) * ((st.height << 8) / st.ystep);
		return true;
	}
};

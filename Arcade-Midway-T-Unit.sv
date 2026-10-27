//============================================================================
//  Williams/Midway T-Unit for MiSTer
//
//  Top level (emu): HPS interface, ROM loading, memories, per-game
//  configuration and inputs, video output with CRT Adjust and CRT V-Size,
//  audio.
//
//  Clocks: everything runs from one 96 MHz clock (clk_sys). The 34010, the
//  pixel clock (8 MHz), the sound CPU (2 MHz E clock), the YM2151 and the
//  OKI are clock enables derived from it.
//
//  Memory:
//    SDRAM  program ROM, graphics ROM, sound ROMs, 512 KB main RAM
//    DDR3   the 1 MB frame store (VRAM)
//    BRAM   CMOS, palette, caches and line buffers
//
//  This program is free software; you can redistribute it and/or modify it
//  under the terms of the GNU General Public License as published by the Free
//  Software Foundation; either version 3 of the License, or (at your option)
//  any later version.
//
//  Copyright (C) 2026 Gm0rk
//============================================================================

module emu
(
	`include "sys/emu_ports.vh"
);

///////// Default values for ports not used in this core /////////

assign ADC_BUS  = 'Z;
assign USER_OUT = '1;
assign {UART_RTS, UART_TXD, UART_DTR} = 0;
assign {SD_SCK, SD_MOSI, SD_CS} = 'Z;

assign VGA_F1        = 0;
assign VGA_SCALER    = 0;
assign VGA_DISABLE   = 0;
assign HDMI_FREEZE   = 0;
assign HDMI_BLACKOUT = 0;
assign HDMI_BOB_DEINT = 0;

assign LED_DISK  = 0;
assign LED_POWER = 0;
assign BUTTONS   = 0;

//////////////////////////////////////////////////////////////////
// OSD
//////////////////////////////////////////////////////////////////

`include "build_id.v"
`include "rtl/tunit_fmoves_osd.svh"
`include "rtl/tunit_secrets_osd.svh"
`include "rtl/tunit_window_pages.svh"
localparam CONF_STR = {
	"A.MIDWAYT;;",
	"-;",
	"P1,Video Settings;",
	"P1-;",
	"P1O[2:1],Aspect Ratio,Original,Full Screen,[ARC1],[ARC2];",
	"P1O[5:3],Scandoubler Fx,None,HQ2x,CRT 25%,CRT 50%,CRT 75%;",
	"P1O[7:6],Scale,Normal,V-Integer,Narrower HV-Integer,Wider HV-Integer;",
	"P1-;",
	"P1O[11:10],Video Timing,Native 54.7Hz,57Hz,60Hz;",
	"P1O[101],CRT Adjust,Off,On;",
	"H1P1O[102],CRT Auto-Width,Off,On;",
	"H1P1O[100:96],CRT H-Size,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14,+15,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[85:79],CRT H-Position,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14,+15,+16,+17,+18,+19,+20,+21,+22,+23,+24,+25,+26,+27,+28,+29,+30,+31,+32,+33,+34,+35,+36,+37,+38,+39,+40,+41,+42,+43,+44,+45,+46,+47,+48,-48,-47,-46,-45,-44,-43,-42,-41,-40,-39,-38,-37,-36,-35,-34,-33,-32,-31,-30,-29,-28,-27,-26,-25,-24,-23,-22,-21,-20,-19,-18,-17,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[78:74],CRT V-Shift,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14,+15,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[107:104],CRT V-Size,0,+1,+2,+3,+4,+5,+6,+7,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[108],CRT V-Size Mode,PVM,Cabinet;",
	"-;",
	`FMOVES_OSD,
	"hEO[113:110],Fixed AI Difficulty,Off,0,1,2,3,4,5,6,7,8,9;",
	"DIP;",
	`NBA_OSD,
	"h7P3,Secret Menus;",
	"P3-;",
	"P3R[14],Secret Audit Menu;",
	"P3R[15],Secret Audit Menu + Credits;",
	"P3-;",
	"P3-,Codes work in attract mode;",
	"h3P6,Hidden Items;",
	"P6-;",
	"P6R[14],EJB Menu;",
	"h4P6R[15],EJB Menu (Copyright Screen);",
	"h4P6O[42],Moon Silhouettes Always,Off,On;",
	"h4P6T[41],Reptile Fight Next;",
	"h4P6O[43],Reptile Hints Always,Off,On;",
	"h5P6O[17],Hitboxes,Off,On;",
	"h5P6O[20],Jade Fight,Off,On;",
	"h5P6O[19],Noob Saibot Fight,Off,On;",
	"h5P6O[18],Pong at Battle 250,Off,On;",
	"h5P6O[16],Security Screen,Off,On;",
	"h5P6O[21],Smoke Fight,Off,On;",
	"P6-;",
	"P6-,EJB Menu: attract mode only;",
	"O[9],Service Mode,Off,On;",
	"O[8],Pause when OSD is open,On,Off;",
	"-;",
	"T[0],Reset;",
	"R[0],Reset and close OSD;",
	"J1,B1,B2,B3,B4,B5,B6,Start,Coin,Test,Pause;",
	"jn,A,B,X,Y,L,R,Start,Select,,;",
	`CORE_INFO,
	"V,v",`BUILD_DATE
};

// OSD menu mask bits (assigned in "Game configuration"): which secrets the
// loaded game has; bits 8-11 the fighter picked on the Finishing Moves and
// Move List pages; bits 12 and 13 NBA Jam and TE (their own Secrets lines,
// rtl/tunit_secrets_osd.svh); bit 14 the Fixed AI Difficulty line (MK and
// MK2, see below). osd_ejb and osd_mk2 are menu_ejb and menu_mk2 less a set
// whose MRA hides the extras (hide_ext): they show or hide the Move List, the
// Finishing Moves page and the Hidden Items page.
wire        menu_secrets, menu_ejb, menu_mk, menu_mk2, menu_nba, menu_jd, menu_nj, menu_te;
wire        osd_ejb, osd_mk2;
wire        lvl_items;
wire  [3:0] fm_line;
wire        info_req;
wire  [7:0] info;

wire        forced_scandoubler;
wire        direct_video;
wire  [1:0] buttons;
wire [127:0] status;
wire [31:0] joy0, joy1, joy2, joy3;
wire [21:0] gamma_bus;

wire        ioctl_download;
wire        ioctl_upload;
wire        ioctl_upload_req;
wire [15:0] ioctl_index;
wire        ioctl_wr;
wire        ioctl_rd;
wire [26:0] ioctl_addr;
wire [15:0] ioctl_dout;
wire [15:0] ioctl_din;
reg         ioctl_wait;

hps_io #(.CONF_STR(CONF_STR), .CONF_STR_BRAM(1), .WIDE(1)) hps_io
(
	.clk_sys             (clk_sys),
	.HPS_BUS             (HPS_BUS),
	.EXT_BUS             (),
	.gamma_bus           (gamma_bus),

	.forced_scandoubler  (forced_scandoubler),
	.direct_video        (direct_video),

	.buttons             (buttons),
	.status              (status),
	.status_menumask     ({1'b0, lvl_items, menu_te, menu_nj, fm_line, menu_jd, menu_nba, osd_mk2, menu_mk, osd_ejb, menu_secrets, ~status[101], 1'b0}),
	.info_req            (info_req),
	.info                (info),

	.joystick_0          (joy0),
	.joystick_1          (joy1),
	.joystick_2          (joy2),
	.joystick_3          (joy3),

	.ioctl_download      (ioctl_download),
	.ioctl_upload        (ioctl_upload),
	.ioctl_upload_req    (ioctl_upload_req),
	.ioctl_upload_index  (8'd2),
	.ioctl_index         (ioctl_index),
	.ioctl_wr            (ioctl_wr),
	.ioctl_rd            (ioctl_rd),
	.ioctl_addr          (ioctl_addr),
	.ioctl_dout          (ioctl_dout),
	.ioctl_din           (ioctl_din),
	.ioctl_wait          (ioctl_wait)
);

//////////////////////////////////////////////////////////////////
// Clocks and reset
//////////////////////////////////////////////////////////////////

wire clk_sys;
wire pll_locked;

pll pll
(
	.refclk   (CLK_50M),
	.rst      (1'b0),
	.outclk_0 (clk_sys),
	.locked   (pll_locked)
);

// ROM downloads: index 0 (program + graphics) and index 3 (sound)
wire rom_download = ioctl_download && ((ioctl_index == 16'd0) || (ioctl_index == 16'd3));
reg  rom_loaded = 1'b0;
reg  rom_was_dl;
reg  ram_clr_req = 1'b0;

// the core runs once a complete ROM set has arrived; main RAM is cleared
// after each ROM load (MAME starts with it zeroed)
always @(posedge clk_sys) begin
	rom_was_dl <= rom_download;
	if (rom_download)
		rom_loaded <= 1'b0;
	else if (rom_was_dl) begin
		rom_loaded  <= 1'b1;
		ram_clr_req <= ~ram_clr_req;
	end
end

// The NVRAM file follows the ROMs in a separate transfer. Hold the board in
// reset for half a second after a download so the game never boots on an
// empty CMOS that is about to be replaced. Not for the DIP switches (index
// 254): Main_MiSTer sends them again each time one changes on the OSD, and
// the game goes on (it reads most of them at power-up; Service Credit and
// Tilt act at once).
reg  [25:0] boot_hold;
always @(posedge clk_sys) begin
	if (ioctl_download && ioctl_index != 16'd254)
		boot_hold <= 26'd48_000_000;
	else if (boot_hold != 26'd0)
		boot_hold <= boot_hold - 26'd1;
end

wire reset = RESET | status[0] | buttons[1] | rom_download | ~rom_loaded | (boot_hold != 26'd0);

// The picture is black while a ROM set loads (the "Sending ROM" box then sits
// on black). Black from the first byte of a download (not the DIP switches'
// index 254, re-sent while a game runs) until the board's half-second boot
// hold ends, and from power-up until the first ROM set is complete. The
// board's picture is gated to black and its stopped raster is replaced by
// the core's own black frames (see "video while a ROM set loads" below).
wire load_black = (ioctl_download && ioctl_index != 16'd254) | ~rom_loaded | (boot_hold != 26'd0);

//////////////////////////////////////////////////////////////////
// Game configuration
//
// MRA ROM index 1 carries the game id. Hardware differences between the
// games are all selected from it.
//////////////////////////////////////////////////////////////////

localparam G_MK       = 3'd0;    // Mortal Kombat (T-Unit, rev 4.0 / 5.0)
localparam G_MKTURBO  = 3'd1;    // Mortal Kombat Turbo Ninja (hack)
localparam G_MK2      = 3'd2;    // Mortal Kombat II (DCS sound)
localparam G_NBAJAM   = 3'd3;    // NBA Jam
localparam G_NBAJAMTE = 3'd4;    // NBA Jam Tournament Edition
localparam G_JDREDDP  = 3'd5;    // Judge Dredd (location test)

localparam L_MK = 2'd0, L_MK2 = 2'd1, L_NBA = 2'd2, L_JD = 2'd3;

reg   [2:0] game_id;
reg         hide_ext = 1'b0;    // the set hides the Move List, Finishing Moves and Hidden Items (index 1, word 0 bit 8)
reg   [2:0] cfg_prot;
reg         cfg_turbo;
reg         cfg_dcs;
reg  [15:0] cfg_sprot_start;
reg  [15:0] cfg_sprot_end;
reg   [1:0] cfg_layout;

always @(posedge clk_sys) begin
	cfg_prot        <= 3'd0;
	cfg_turbo       <= 1'b0;
	cfg_dcs         <= 1'b0;
	cfg_sprot_start <= 16'hFFFF;
	cfg_sprot_end   <= 16'h0000;
	cfg_layout      <= L_MK;

	// sound CPU hidden RAM windows and 34010 protections: MAME init_*
	case (game_id)
		G_MK, G_MKTURBO: begin
			cfg_prot  <= 3'd1;                         // P_MK
			cfg_turbo <= (game_id == G_MKTURBO);
			cfg_sprot_start <= 16'hFB9C; cfg_sprot_end <= 16'hFBC6;
		end
		G_MK2: begin
			cfg_prot   <= 3'd5;                        // P_MK2
			cfg_dcs    <= 1'b1;
			cfg_layout <= L_MK2;
		end
		G_NBAJAM: begin
			cfg_prot   <= 3'd2;                        // P_NBAJAM
			cfg_sprot_start <= 16'hFBAA; cfg_sprot_end <= 16'hFBD4;
			cfg_layout <= L_NBA;
		end
		G_NBAJAMTE: begin
			cfg_prot   <= 3'd3;                        // P_NBAJAMTE
			cfg_sprot_start <= 16'hFBEC; cfg_sprot_end <= 16'hFC16;
			cfg_layout <= L_NBA;
		end
		G_JDREDDP: begin
			cfg_prot   <= 3'd4;                        // P_JDREDD
			cfg_sprot_start <= 16'hFBCF; cfg_sprot_end <= 16'hFBF9;
			cfg_layout <= L_JD;
		end
		default: ;
	endcase
end

// OSD lines and pages of the loaded game (status_menumask bits 2-7, 12, 13)
assign menu_secrets = (game_id <= G_JDREDDP);
assign menu_ejb     = (game_id == G_MK) || (game_id == G_MKTURBO) || (game_id == G_MK2);
assign menu_mk      = (game_id == G_MK) || (game_id == G_MKTURBO);
assign menu_mk2     = (game_id == G_MK2);
assign menu_nba     = (game_id == G_NBAJAM) || (game_id == G_NBAJAMTE);
assign menu_nj      = (game_id == G_NBAJAM);
assign menu_te      = (game_id == G_NBAJAMTE);
assign menu_jd      = (game_id == G_JDREDDP);
assign osd_ejb      = menu_ejb & ~hide_ext;
assign osd_mk2      = menu_mk2 & ~hide_ext;

//////////////////////////////////////////////////////////////////
// Downloads: ROMs (index 0 and 3), game id and secrets table (1), NVRAM (2),
// DIP switches (254)
//
// Index 1 is the per-set table of rtl/tunit_secrets.sv; its first word is
// the game id.
//
// SDRAM layout (byte addresses):
//   0x0000000  program ROM, 1 MB          } index 0, as the MRA sends it
//   0x0100000  graphics ROM, up to 12 MB  }
//   0x0D00000  sound ROMs, up to 3 MB       index 3 (0xD00000 + offset)
//   0x1000000  main RAM, 512 KB (not downloaded)
// The graphics size is taken from the length of the index 0 download; the
// board reads 0 above it, as from MAME's empty region.
//////////////////////////////////////////////////////////////////

reg  [63:0] dsw;
reg  [26:0] rom0_end;           // last byte address of the index 0 download

always @(posedge clk_sys) begin
	if (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr == 27'd0) begin
		game_id  <= ioctl_dout[2:0];
		hide_ext <= ioctl_dout[8];
	end
	if (ioctl_wr && ioctl_index == 16'd254 && ioctl_addr[26:3] == 24'd0)
		dsw[{ioctl_addr[2:1], 4'b0000} +: 16] <= ioctl_dout;
	if (ioctl_download && ioctl_index == 16'd0 && !rom_was_dl)
		rom0_end <= 27'd0;
	else if (ioctl_wr && ioctl_index == 16'd0)
		rom0_end <= ioctl_addr + 27'd1;
end

// graphics MB loaded: (bytes after the program ROM) rounded up
wire [26:0] gfx_bytes = (rom0_end > 27'h010_0000) ? (rom0_end - 27'h010_0000 + 27'h00F_FFFF) : 27'd0;
wire  [3:0] gfx_mb    = (gfx_bytes[26:20] > 7'd12) ? 4'd12 : gfx_bytes[23:20];

wire [24:0] dl_sdram = (ioctl_index == 16'd3) ? (25'h0D0_0000 + ioctl_addr[24:0]) : ioctl_addr[24:0];

reg  [24:1] dl_wr_addr;
reg  [15:0] dl_wr_data;
reg         dl_wr_req = 1'b0;
reg         dl_wr_ack = 1'b0;

always @(posedge clk_sys) begin
	if (ioctl_wr && rom_download) begin
		dl_wr_addr <= dl_sdram[24:1];
		dl_wr_data <= ioctl_dout;
		dl_wr_req  <= ~dl_wr_req;
		ioctl_wait <= 1'b1;
	end
	else if (dl_wr_req == dl_wr_ack)
		ioctl_wait <= 1'b0;
end

// NVRAM (CMOS, 16 KB): loaded through port B of the CMOS RAM, cleared when a
// new ROM set arrives so a game never sees another game's settings, saved
// when the OSD opens after the game has changed it
reg  [12:0] cmos_clr_addr;
reg         cmos_clr;
reg         cmos_dirty = 1'b0;
reg         nv_req = 1'b0;          // save request to the HPS (ioctl_upload_req)
reg         nv_up_d = 1'b0;
reg         osd_d = 1'b0;
wire [15:0] nv_dout;
wire        cmos_write;

wire        nv_dl = ioctl_download && ioctl_index == 16'd2;
wire        nv_up = ioctl_upload && ioctl_index == 16'd2;

always @(posedge clk_sys) begin
	if (rom_download && !rom_was_dl) begin
		cmos_clr      <= 1'b1;
		cmos_clr_addr <= 13'd0;
	end
	else if (cmos_clr) begin
		cmos_clr_addr <= cmos_clr_addr + 13'd1;
		if (cmos_clr_addr == 13'h1FFF) cmos_clr <= 1'b0;
	end

	// the game has changed its CMOS since the last save; the save starting
	// clears it (a write during the save marks it again)
	nv_up_d <= nv_up;
	if (cmos_write) cmos_dirty <= 1'b1;
	else if (nv_up & ~nv_up_d) cmos_dirty <= 1'b0;

	// Save request: raised as the OSD opens, if the CMOS has changed, and
	// held until it closes. Main_MiSTer looks for a request (and saves,
	// showing "Saving...") every time it draws the OSD's main menu: when it
	// opens and again after every option change. A request that followed
	// cmos_dirty would make it save again after a change whenever the game
	// had written its CMOS in between; this one rises once per opening.
	osd_d <= OSD_STATUS;
	if (OSD_STATUS & ~osd_d) nv_req <= cmos_dirty;
	else if (~OSD_STATUS)    nv_req <= 1'b0;
end

assign ioctl_upload_req = nv_req;
assign ioctl_din        = nv_dout;

wire [12:0] nv_addr = cmos_clr ? cmos_clr_addr : ioctl_addr[13:1];
wire        nv_we   = cmos_clr | (nv_dl & ioctl_wr);
wire [15:0] nv_din  = cmos_clr ? 16'h0000 : ioctl_dout;

//////////////////////////////////////////////////////////////////
// Inputs
//
// Joystick bits: 0 R, 1 L, 2 D, 3 U, 4-9 B1-B6, 10 Start, 11 Coin, 12 Test,
// 13 Pause. B1-B6 are MAME's BUTTON1-BUTTON6 of each game, except MK and
// MK2: High Punch, Low Punch, High Kick, Low Kick, Block (B6 unused). The
// MRAs name the buttons in this order. Ports are active low; the layouts
// follow MAME's input ports (midtunit.cpp).
//
// Service Credit and Tilt are not on the controllers: they are lines of the
// OSD's DIP Switches page, handled in "Service credit and tilt" below.
//////////////////////////////////////////////////////////////////

// {R, L, D, U} as MAME's bit order up, down, left, right
function automatic [3:0] udlr(input [31:0] j);
	udlr = {j[0], j[1], j[2], j[3]};
endfunction

wire       test_sw = status[9] | joy0[12] | joy1[12];
reg  [3:0] svc_cnt  = 4'd0;                 // service credit held while non-zero
reg  [3:0] tilt_cnt = 4'd0;                 // slam tilt held while non-zero
wire       svc_sw  = |svc_cnt;
wire       tilt_sw = |tilt_cnt;

// secrets code player (OSD hidden items and cheat codes): while it plays a
// code it replaces IN0 and holds the start buttons it needs
wire        code_on;
wire [15:0] code_in0;
wire  [1:0] code_start;

// finishing-move player (OSD Finishing Moves page): while it plays a move it
// replaces the winner's controls
wire  [1:0] fm_drive;
wire  [8:0] fm_keys;

// active-high port images, inverted at the end
reg  [15:0] in0, in1, in2;
always @(*) begin
	in0 = 16'h0000;
	in1 = 16'h0000;
	in2 = 16'h0000;

	// common to every game
	in1[0] = joy0[11];               // coin 1
	in1[1] = joy1[11];               // coin 2
	in1[2] = joy0[10];               // start 1
	in1[3] = tilt_sw;                // tilt (slam switch)
	in1[4] = test_sw;                // test
	in1[5] = joy1[10];               // start 2
	in1[6] = svc_sw;                 // service credit
	in1[7] = joy2[11];               // coin 3
	in1[8] = joy3[11];               // coin 4

	case (cfg_layout)
		L_MK: begin
			// B1 high punch, B2 low punch, B3 high kick, B4 low kick, B5 block;
			// B6 not used (MAME's Block 2, a second block input, stays up)
			in0[3:0]   = udlr(joy0);  in0[4]  = joy0[4];  in0[5]  = joy0[8];  in0[6]  = joy0[6];
			in0[11:8]  = udlr(joy1);  in0[12] = joy1[4];  in0[13] = joy1[8];  in0[14] = joy1[6];
			in1[12]    = joy0[5];     in1[13] = joy0[7];  // P1 low punch, low kick
			in1[9]     = joy1[5];     in1[10] = joy1[7];  // P2 low punch, low kick
		end
		L_MK2: begin
			// as MK; the low punch / low kick bits are in IN2
			in0[3:0]   = udlr(joy0);  in0[4]  = joy0[4];  in0[5]  = joy0[8];  in0[6]  = joy0[6];
			in0[11:8]  = udlr(joy1);  in0[12] = joy1[4];  in0[13] = joy1[8];  in0[14] = joy1[6];
			in2[0]     = joy0[5];     in2[1]  = joy0[7];
			in2[4]     = joy1[5];     in2[5]  = joy1[7];
		end
		L_NBA: begin
			// B1 turbo (bit 6), B2 shoot / block (bit 4), B3 pass / steal (bit 5)
			in0[3:0]   = udlr(joy0);  in0[4]  = joy0[5];  in0[5]  = joy0[6];  in0[6]  = joy0[4];
			in0[11:8]  = udlr(joy1);  in0[12] = joy1[5];  in0[13] = joy1[6];  in0[14] = joy1[4];
			in1[9]     = joy2[10];    // start 3
			in1[10]    = joy3[10];    // start 4
			in2[3:0]   = udlr(joy2);  in2[4]  = joy2[5];  in2[5]  = joy2[6];  in2[6]  = joy2[4];
			in2[11:8]  = udlr(joy3);  in2[12] = joy3[5];  in2[13] = joy3[6];  in2[14] = joy3[4];
		end
		L_JD: begin
			// B1 kick (bit 6), B2 jump (bit 4), B3 punch (bit 5), B4 crouch (bit 7)
			in0[3:0]   = udlr(joy0);  in0[4]  = joy0[5];  in0[5]  = joy0[6];  in0[6]  = joy0[4];  in0[7]  = joy0[7];
			in0[11:8]  = udlr(joy1);  in0[12] = joy1[5];  in0[13] = joy1[6];  in0[14] = joy1[4];  in0[15] = joy1[7];
			in1[9]     = joy2[10];    // start 3
			in2[3:0]   = udlr(joy2);  in2[4]  = joy2[5];  in2[5]  = joy2[6];  in2[6]  = joy2[4];  in2[7]  = joy2[7];
		end
	endcase

	// finishing moves: the player's controls replaced by the move's
	// (fm_keys {BL, LK, HK, LP, HP, Right, Left, Down, Up}; Block 2 up)
	if (fm_drive[0]) begin
		in0[6:0] = {fm_keys[6], fm_keys[8], fm_keys[4], fm_keys[3:0]};
		if (cfg_layout == L_MK) {in1[15], in1[13:12]} = {1'b0, fm_keys[7], fm_keys[5]};
		else                    in2[2:0] = {1'b0, fm_keys[7], fm_keys[5]};
	end
	if (fm_drive[1]) begin
		in0[14:8] = {fm_keys[6], fm_keys[8], fm_keys[4], fm_keys[3:0]};
		if (cfg_layout == L_MK) in1[11:9] = {1'b0, fm_keys[7], fm_keys[5]};
		else                    in2[6:4]  = {1'b0, fm_keys[7], fm_keys[5]};
	end

	if (code_on) begin
		in0    = code_in0;
		in1[2] = in1[2] | code_start[0];
		in1[5] = in1[5] | code_start[1];
	end
end

wire [63:0] in_ports = {dsw[15:0], ~in2, ~in1, ~in0};

//////////////////////////////////////////////////////////////////
// Pause
//////////////////////////////////////////////////////////////////

reg  pause_toggle;
reg  pause_btn_d;
always @(posedge clk_sys) begin
	pause_btn_d <= joy0[13] | joy1[13];
	if (reset) pause_toggle <= 1'b0;
	else if ((joy0[13] | joy1[13]) & ~pause_btn_d) pause_toggle <= ~pause_toggle;
end

// the information windows (see Video) hold the game too: the OSD option
// picks the page (0 Off, n page n), a value past the list's pages is Off
wire [3:0] list_sel    = menu_nba ? {1'b0, status[67:65]} : status[64:61];
wire [4:0] list_n      = menu_te ? WIN_NBAJAMTE_N : menu_nj ? WIN_NBAJAM_N : menu_mk2 ? WIN_MK2_N : WIN_MK_N;
wire       list_valid  = list_sel != 4'd0 && {1'b0, list_sel} <= list_n;
wire       movelist_on = osd_ejb & list_valid;
wire       splist_on   = menu_nba & list_valid;
wire pause = pause_toggle | (OSD_STATUS & ~status[8]) | movelist_on | splist_on;

//////////////////////////////////////////////////////////////////
// T-Unit board
//////////////////////////////////////////////////////////////////

wire [24:3] cpu_sd_addr, dma_sd_addr, snd_sd_addr, oki_sd_addr;
wire        cpu_sd_req, dma_sd_req, snd_sd_req, oki_sd_req;
wire        cpu_sd_ack, dma_sd_ack, snd_sd_ack, oki_sd_ack;
wire [63:0] cpu_sd_data, dma_sd_data, snd_sd_data, oki_sd_data;

wire [24:1] ram_wr_addr;
wire [15:0] ram_wr_data;
wire        ram_wr_req;
reg         ram_wr_ack = 1'b0;      // from the write channel arbiter (SDRAM section)
wire        sd_wr_ack;

wire        snd_wr, snd_rd;
wire [15:0] snd_data;
wire [15:0] snd_status, snd_rdata;

wire        ce_pix;
wire  [7:0] brd_r, brd_g, brd_b;          // the board's picture
wire        brd_hs, brd_vs, brd_hb, brd_vb;    // and its sync and blanking
wire  [7:0] core_r, core_g, core_b;       // with the information window
wire        core_hs, core_vs, core_hb, core_vb;

// ---- video while a ROM set loads ----
//
// The board holds the 34010 in reset while a ROM set loads, and the 34010's
// raster counters stop with it: the board sends no frames at all, and the
// scaler goes on showing the last frame it had (the MiSTer menu's coloured
// or patterned background behind the "Sending ROM" box). So while load_black
// the core sends its own frames instead: black, with the timing the 34010
// starts from (253 VCLKs of 2 dots x 289 lines, the same blanking and sync;
// 15.81 kHz, 54.7 Hz), so the output stays locked and the scaler shows black.
reg   [8:0] idl_x = 9'd0;       // dot in the line, 0-505
reg   [8:0] idl_y = 9'd0;       // line in the frame, 0-288
always @(posedge clk_sys) if (ce_pix) begin
	if (idl_x == 9'd505) begin
		idl_x <= 9'd0;
		idl_y <= (idl_y == 9'd288) ? 9'd0 : idl_y + 9'd1;
	end
	else
		idl_x <= idl_x + 9'd1;
end

wire idl_hs = (idl_x < 9'd36);                           // HESYNC 18 VCLKs
wire idl_hb = (idl_x < 9'd90) | (idl_x >= 9'd500);       // HEBLNK 45, HSBLNK 250
wire idl_vs = (idl_y < 9'd3);                            // VESYNC 3
wire idl_vb = (idl_y < 9'd20) | (idl_y >= 9'd274);       // VEBLNK 20, VSBLNK 274

assign core_hs = load_black ? idl_hs : brd_hs;
assign core_vs = load_black ? idl_vs : brd_vs;
assign core_hb = load_black ? idl_hb : brd_hb;
assign core_vb = load_black ? idl_vb : brd_vb;

//////////////////////////////////////////////////////////////////
// Service credit and tilt (OSD DIP Switches page)
//
// The MRAs list them with the game's DIP switches (bits 16 and 17 of the
// switches, tools/mra_gen.py). Main_MiSTer sends all the switches each time
// one changes, so selecting the line flips its bit: each flip after the
// first download (the saved values when the game loads) holds the matching
// cabinet switch closed for 8 frames (about 150 ms), long enough for the
// game's switch scan to accept it, like a real coin or slam switch. Frames
// are counted only while the game runs, so with "Pause when OSD is open"
// the switch closes when the OSD is shut.
//////////////////////////////////////////////////////////////////

reg        osd_vb_d;
wire       osd_frame = brd_vb & ~osd_vb_d & ~pause;    // start of a running frame

reg        dsw_seen = 1'b0;      // the switches' second word has come once since the ROMs
wire       dsw_w1   = ioctl_wr && ioctl_index == 16'd254 && ioctl_addr[26:1] == 26'd1;
wire       svc_flip  = dsw_w1 && dsw_seen && (ioctl_dout[0] ^ dsw[16]);
wire       tilt_flip = dsw_w1 && dsw_seen && (ioctl_dout[1] ^ dsw[17]);

always @(posedge clk_sys) begin
	osd_vb_d <= brd_vb;
	if (rom_download)  dsw_seen <= 1'b0;     // a new game: its saved switches come next
	else if (dsw_w1)   dsw_seen <= 1'b1;

	if (reset) begin
		svc_cnt  <= 4'd0;
		tilt_cnt <= 4'd0;
	end
	else begin
		if (svc_flip)                    svc_cnt  <= 4'd8;
		else if (osd_frame && svc_sw)    svc_cnt  <= svc_cnt - 4'd1;

		if (tilt_flip)                   tilt_cnt <= 4'd8;
		else if (osd_frame && tilt_sw)   tilt_cnt <= tilt_cnt - 4'd1;
	end
end

//////////////////////////////////////////////////////////////////
// OSD secrets (Secret Menus, Hidden Items, Cheat Codes & Hidden Items)
//
// R[14] / R[15] play the loaded set's code 1 / code 2 (hidden menus, entered
// on the controls during the attract mode; NBA Jam's tank game and TE's
// tournament mode, entered on the Tonight's Match-Up screen and held until
// the game takes them); the options switch its read patches through the
// option slots of rtl/tunit_secrets.sv (MK: Reptile Fight Next, Moon
// Silhouettes Always and Reptile Hints Always, see Reptile below; MK2,
// O[21:16]: security screen, hitboxes, Pong at battle 250, Noob Saibot, Jade
// and Smoke fights; NBA Jam and TE, O[55:48]: the power-ups, slots in the
// order of tools/tunit_secrets.py's NJ_* / TE_* codes). The codes and patch
// addresses come with the MRA (ROM index 1), found per revision by
// tools/tunit_secrets.py.
// Frames are counted while the game runs, so with "Pause when OSD is open"
// a code starts when the OSD closes.
//////////////////////////////////////////////////////////////////

wire  [1:0] te_head  = status[49:48];          // TE Head Size: Normal, Big, Huge
reg         rep_arm  = 1'b0;                   // MK: Reptile Fight Next set (Reptile below)
wire [10:0] sec_opt  = hide_ext ? 11'd0 :
                       menu_mk2 ? {5'd0, status[21:16]} :
                       menu_mk  ? {8'd0, status[43], status[42], rep_arm} :
                       menu_nj  ? {6'd0, status[53], status[52], status[51], status[50], status[48]} :
                       menu_te  ? {3'd0, status[53], status[52], status[50], status[51], status[55],
                                   status[54], te_head == 2'd2, te_head != 2'd0} :
                                  11'd0;
wire [10:0] opt_avail;

wire [223:0] pt_addr;
wire [127:0] pt_data;
wire   [7:0] pt_en;
wire   [7:0] pt_fetch;           // entry is program code: instruction fetches only
wire         cpu_rd;             // the board's completed CPU reads (a code's success)
wire         cpu_wr;             // and writes (the finishing-move player follows the fight)
wire  [27:0] cpu_wa;
wire  [15:0] cpu_wd;
wire         code_ok, code_fail;
wire         code_cur;           // the code that ended: 0 code 1, 1 code 2
wire   [1:0] code_avail;         // the set has code 1 / code 2

reg  secrets_dl_d = 1'b0;
wire secrets_dl   = ioctl_download && ioctl_index == 16'd1;
always @(posedge clk_sys) secrets_dl_d <= secrets_dl;

tunit_secrets secrets
(
	.clk        (clk_sys),
	.reset      (reset),

	.dl_start   (secrets_dl & ~secrets_dl_d),
	.dl_wr      (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr[26:10] == 17'd0),
	.dl_addr    (ioctl_addr[9:1]),
	.dl_data    (ioctl_dout),

	.trig       (status[15:14]),
	.opt        (sec_opt),
	.frame      (osd_frame),

	.cpu_rd     (cpu_rd),
	.cpu_wa     (cpu_wa),

	.code_on    (code_on),
	.code_in0   (code_in0),
	.code_start (code_start),
	.code_ok    (code_ok),
	.code_fail  (code_fail),
	.code_cur   (code_cur),
	.code_avail (code_avail),
	.opt_avail  (opt_avail),

	.pt_addr    (pt_addr),
	.pt_data    (pt_data),
	.pt_en      (pt_en),
	.pt_fetch   (pt_fetch)
);

//////////////////////////////////////////////////////////////////
// Reptile (MK, MK Turbo)
//
// Three Hidden Items lines, option slots 1-3 of the secrets module: "Reptile
// Fight Next" (T[41]) sets or clears a one-time Reptile fight after the next
// match won in a 1-player game; it is used up when his fight starts (the
// CPU writes 1 to his flag, whose word address the MRA gives at ROM index 1
// words 0x228-0x229, tools/tunit_fmoves.py; other code writes other values
// there in the attract mode). "Moon Silhouettes Always" (O[42]) and
// "Reptile Hints Always" (O[43]) stay on. The patches are program
// instructions: the board applies them to instruction fetches only
// (pt_fetch, as every program ROM patch), so the game's data reads of its
// ROM see the original.
//////////////////////////////////////////////////////////////////

reg  [27:0] rep_flag = 28'd0;    // his flag's word address (0: none)
reg         rep_trig_d;
reg         rep_msg_set, rep_msg_clr, rep_msg_none;

always @(posedge clk_sys) begin
	rep_trig_d   <= status[41];
	rep_msg_set  <= 1'b0;
	rep_msg_clr  <= 1'b0;
	rep_msg_none <= 1'b0;

	if (secrets_dl & ~secrets_dl_d)
		rep_flag <= 28'd0;
	else if (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr == 27'h450)
		rep_flag[15:0]  <= ioctl_dout;
	else if (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr == 27'h452)
		rep_flag[27:16] <= ioctl_dout[11:0];

	if (reset)
		rep_arm <= 1'b0;
	else if (status[41] & ~rep_trig_d & menu_mk) begin
		if (opt_avail[0]) begin
			rep_arm     <= ~rep_arm;
			rep_msg_set <= ~rep_arm;
			rep_msg_clr <= rep_arm;
		end
		else
			rep_msg_none <= 1'b1;
	end
	else if (cpu_wr && cpu_wa == rep_flag && rep_flag != 28'd0 && cpu_wd == 16'd1)
		rep_arm <= 1'b0;             // his fight has started (the game sets the flag to 1)
end

//////////////////////////////////////////////////////////////////
// Fixed AI Difficulty (MK, MK2)
//
// MK and MK2 keep the CPU opponent's level (0 easiest to 9) in one main RAM
// word: the AI picks entries of its 10-entry tables with it, the game raises
// it after matches won and lowers it after matches lost. The MRA gives the
// word's address (ROM index 1, bytes 0x454-0x457, tools/tunit_fmoves.py;
// 0: none, and the OSD line is hidden). While O[113:110] is not Off, the
// board returns the chosen level for the CPU's reads of that word (with
// interrupts enabled, rtl/midway_tunit.sv "Read patches"): the game's own
// writes go on as before, so Off hands its own value back at once. It is off
// while the test menu is selected (the Service Mode option, a test button or
// the Test Switch DIP), so the diagnostics see the game's RAM as it is.
//////////////////////////////////////////////////////////////////

reg  [27:0] lvl_wa = 28'd0;     // the AI level word's word address (0: none)

always @(posedge clk_sys) begin
	if (secrets_dl & ~secrets_dl_d)
		lvl_wa <= 28'd0;
	else if (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr == 27'h454)
		lvl_wa[15:0]  <= ioctl_dout;
	else if (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr == 27'h456)
		lvl_wa[27:16] <= ioctl_dout[11:0];
end

wire [3:0] lvl_sel  = status[113:110];                    // Off, then levels 0-9
wire       lvl_test = test_sw | ~dsw[0];                  // the test menu is selected
assign lvl_items    = (menu_mk | menu_mk2) & (lvl_wa != 28'd0);
wire       lvl_on   = lvl_items & (lvl_sel != 4'd0) & ~lvl_test;
wire [3:0] lvl_val  = (lvl_sel > 4'd10) ? 4'd9 : (lvl_sel - 4'd1);

//////////////////////////////////////////////////////////////////
// Finishing moves (MK, MK2)
//
// The Finishing Moves page picks a character (O[30:28] MK, O[27:24] MK2;
// the menu mask's bits 8-11 show that character's lines) and one of its
// moves (R[32]-R[39], the character's lines in order; R[40] clears the set
// move). (The main menu's Move List option, O[64:61], only shows the moves
// in the window, see Video.)
// rtl/tunit_fmoves.sv plays it at the winner's next FINISH HIM, following
// the fight through the CPU's writes to the variables the MRA gives (ROM
// index 1, bytes 0x400-0x44F, tools/tunit_fmoves.py).
//////////////////////////////////////////////////////////////////

assign fm_line = menu_mk2 ? status[27:24] : {1'b0, status[30:28]};

reg   [8:0] fm_bits_d;
reg         fm_sel;
reg   [3:0] fm_slot;
wire        fm_msg_req;
wire  [4:0] fm_msg;

integer fi;
always @(posedge clk_sys) begin
	fm_bits_d <= status[40:32];
	fm_sel    <= 1'b0;
	for (fi = 8; fi >= 0; fi = fi - 1)
		if (status[32 + fi] & ~fm_bits_d[fi]) begin
			fm_sel  <= 1'b1;
			fm_slot <= (fi == 8) ? 4'd15 : fi[3:0];
		end
end

tunit_fmoves fmoves
(
	.clk       (clk_sys),
	.reset     (reset),
	.game_mk   (menu_mk),
	.game_mk2  (osd_mk2),

	.dl_start  (secrets_dl & ~secrets_dl_d),
	.dl_wr     (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr[26:7] == 20'h8),
	.dl_addr   (ioctl_addr[6:1]),
	.dl_data   (ioctl_dout),

	.sel       (fm_sel),
	.sel_line  (fm_line),
	.sel_slot  (fm_slot),
	.frame     (osd_frame),

	.cpu_wr    (cpu_wr),
	.cpu_wa    (cpu_wa),
	.cpu_wd    (cpu_wd),

	.drive     (fm_drive),
	.keys      (fm_keys),
	.msg_req   (fm_msg_req),
	.msg       (fm_msg)
);

//////////////////////////////////////////////////////////////////
// OSD messages (CONF_STR "I" line, rtl/tunit_fmoves_osd.svh)
//
// The finishing-move player's, the secrets' codes (their menu opened or the
// game took them, or not; a code this revision lacks), Reptile Fight Next
// set or cleared, and the hidden items' and power-ups' options turned on
// (looked at when the OSD closes: what an MK / MK2 option does, that an NBA
// Jam / TE power-up is on for all players, or that this revision does not
// have it). Main_MiSTer shows a message for 2 s, and only with the OSD
// closed: messages wait in a set (lowest number first) and go out one every
// 2.2 s, starting 0.3 s after the OSD closes.
//////////////////////////////////////////////////////////////////

localparam [27:0] MSG_GAP   = 28'd211_200_000;     // 2.2 s at 96 MHz
localparam [27:0] MSG_DELAY = 28'd28_800_000;      // 0.3 s

reg  [31:1] msg_pend;
reg   [1:0] code_trig_d;         // R[15:14] last clock: a code picked that the set lacks
reg  [10:0] sec_open;            // Secrets option slots when the OSD opened
reg  [27:0] msg_timer;
reg         osd_was;
reg         msg_out;
reg   [4:0] msg_num;             // the lowest waiting message
reg   [4:0] msg_num_q;           // the one going out

// MK2's option slots: what each turns on
function automatic [4:0] sec_msg_mk2(input integer slot);
	case (slot)
		0: sec_msg_mk2 = MSG_SECURITY;
		1: sec_msg_mk2 = MSG_HITBOXES;
		2: sec_msg_mk2 = MSG_PONG;
		3: sec_msg_mk2 = MSG_NOOB;
		4: sec_msg_mk2 = MSG_JADE;
		default: sec_msg_mk2 = MSG_SMOKE;
	endcase
endfunction

// MK's option slots 2 and 3 (slot 1, Reptile Fight Next, has its own messages)
function automatic [4:0] sec_msg_mk(input integer slot);
	case (slot)
		1: sec_msg_mk = MSG_REPT_MOON;
		default: sec_msg_mk = MSG_REPT_HINTS;
	endcase
endfunction

integer mi, si;
always @(*) begin
	msg_num = 5'd0;
	for (mi = 31; mi >= 1; mi = mi - 1)
		if (msg_pend[mi]) msg_num = mi[4:0];
end

always @(posedge clk_sys) begin
	osd_was <= OSD_STATUS;
	msg_out <= 1'b0;
	code_trig_d <= status[15:14];

	if (OSD_STATUS & ~osd_was) sec_open <= sec_opt;

	if (fm_msg_req) msg_pend[fm_msg] <= 1'b1;
	if (rep_msg_set)  begin msg_pend[MSG_REPT_SET] <= 1'b1; msg_pend[MSG_REPT_CLEARED] <= 1'b0; end
	if (rep_msg_clr)  begin msg_pend[MSG_REPT_CLEARED] <= 1'b1; msg_pend[MSG_REPT_SET] <= 1'b0; end
	if (rep_msg_none) msg_pend[MSG_NOT_HERE] <= 1'b1;
	if (code_ok)    msg_pend[MSG_CODE_OK] <= 1'b1;
	if (code_fail)  msg_pend[(menu_nba && code_cur) ? MSG_CODE_MATCHUP : MSG_CODE_FAIL] <= 1'b1;
	for (si = 0; si < 2; si = si + 1)
		if (status[14 + si] & ~code_trig_d[si] & ~code_avail[si]) msg_pend[MSG_NOT_HERE] <= 1'b1;
	if (~OSD_STATUS & osd_was) begin
		for (si = 0; si < 11; si = si + 1)
			if (sec_opt[si] & ~sec_open[si] & ~(menu_mk && si == 0))
				msg_pend[~opt_avail[si] ? MSG_NOT_HERE : menu_mk2 ? sec_msg_mk2(si) :
				         menu_mk ? sec_msg_mk(si) :
				         (si == 0 || (menu_te && si <= 2)) ? MSG_ON_NEXT : MSG_ON_ALL] <= 1'b1;
	end

	if (reset)
		msg_pend <= 31'd0;
	else if (OSD_STATUS) begin
		if (msg_timer < MSG_DELAY) msg_timer <= MSG_DELAY;
	end
	else if (msg_timer != 28'd0)
		msg_timer <= msg_timer - 28'd1;
	else if (msg_num != 5'd0) begin
		msg_out  <= 1'b1;
		msg_pend[msg_num] <= 1'b0;
		msg_timer <= MSG_GAP;
	end
end

always @(posedge clk_sys) if (!msg_out) msg_num_q <= msg_num;

assign info_req = msg_out;
assign info     = {3'd0, msg_num_q};

midway_tunit board
(
	.clk            (clk_sys),
	.reset          (reset),
	.pause          (pause),
	.vtiming        (status[11:10]),    // 54.7 / 57 / 60 Hz frames (see midway_tunit.sv)

	.prot_id        (cfg_prot),
	.mk_turbo       (cfg_turbo),
	.big_rom        (cfg_dcs),          // MK2: the large-ROM board
	.dcs            (cfg_dcs),
	.gfx_mb         (gfx_mb),

	.ram_clr_req    (ram_clr_req),

	.in_ports       (in_ports),

	.pt_addr        (pt_addr),
	.pt_data        (pt_data),
	.pt_en          (pt_en),
	.pt_fetch       (pt_fetch),         // program code patches: instruction fetches only

	.lvl_on         (lvl_on),           // Fixed AI Difficulty
	.lvl_addr       (lvl_wa),
	.lvl_val        (lvl_val),

	.snd_wr         (snd_wr),
	.snd_data       (snd_data),
	.snd_rd         (snd_rd),
	.snd_status     (snd_status),
	.snd_rdata      (snd_rdata),

	.cpu_sd_addr    (cpu_sd_addr),
	.cpu_sd_req     (cpu_sd_req),
	.cpu_sd_ack     (cpu_sd_ack),
	.cpu_sd_data    (cpu_sd_data),

	.dma_sd_addr    (dma_sd_addr),
	.dma_sd_req     (dma_sd_req),
	.dma_sd_ack     (dma_sd_ack),
	.dma_sd_data    (dma_sd_data),

	.ram_wr_addr    (ram_wr_addr),
	.ram_wr_data    (ram_wr_data),
	.ram_wr_req     (ram_wr_req),
	.ram_wr_ack     (ram_wr_ack),

	.ddr_busy       (DDRAM_BUSY),
	.ddr_burstcnt   (DDRAM_BURSTCNT),
	.ddr_addr       (DDRAM_ADDR),
	.ddr_dout       (DDRAM_DOUT),
	.ddr_dout_ready (DDRAM_DOUT_READY),
	.ddr_rd         (DDRAM_RD),
	.ddr_din        (DDRAM_DIN),
	.ddr_be         (DDRAM_BE),
	.ddr_we         (DDRAM_WE),

	.nv_addr        (nv_addr),
	.nv_we          (nv_we),
	.nv_din         (nv_din),
	.nv_dout        (nv_dout),
	.cmos_write     (cmos_write),

	.ce_pix         (ce_pix),
	.vid_r          (brd_r),
	.vid_g          (brd_g),
	.vid_b          (brd_b),
	.vid_hs         (brd_hs),
	.vid_vs         (brd_vs),
	.vid_hb         (brd_hb),
	.vid_vb         (brd_vb),

	.dbg_pc         (),
	.dbg_retire     (),
	.dbg_blit_busy  (),
	.dbg_wr         (cpu_wr),
	.dbg_rd         (cpu_rd),
	.dbg_wa         (cpu_wa),
	.dbg_wdata      (cpu_wd),
	.dbg_rdata      ()
);

assign DDRAM_CLK = clk_sys;

//////////////////////////////////////////////////////////////////
// Sound boards
//
// ADPCM board (MK, NBA Jam / TE, Judge Dredd): MAME's sound_w hands it
// data & 0xff with bit 8 as the reset line, so bit 9 (the IRQ strobe on
// other boards) is always low and every command interrupts. The 34010
// never reads it back (MAME fakes the status).
//
// DCS board (MK2): command, status and data through the board's mailboxes.
// The two boards share SDRAM channel 0 for their ROMs; the one not in use
// is held in reset.
//////////////////////////////////////////////////////////////////

wire signed [15:0] adpcm_audio, dcs_audio;

wire [24:3] dcs_sd_addr;
wire        dcs_sd_req;

williams_adpcm sound
(
	.clk        (clk_sys),
	.reset      (reset | cfg_dcs),
	.pause      (pause),

	.prot_start (cfg_sprot_start),
	.prot_end   (cfg_sprot_end),

	.cmd_wr     (snd_wr & ~cfg_dcs),
	.cmd_data   ({snd_data[15:10], 1'b0, snd_data[8:0]}),
	.irq_state  (),

	.rom_addr   (snd_sd_addr),
	.rom_req    (snd_sd_req),
	.rom_ack    (snd_sd_ack),
	.rom_data   (snd_sd_data),

	.oki_addr   (oki_sd_addr),
	.oki_req    (oki_sd_req),
	.oki_ack    (oki_sd_ack),
	.oki_data   (oki_sd_data),

	.audio      (adpcm_audio)
);

tunit_dcs dcs
(
	.clk        (clk_sys),
	.reset      (reset | ~cfg_dcs),
	.pause      (pause),

	.cmd_wr     (snd_wr & cfg_dcs),
	.cmd_data   (snd_data),
	.data_rd    (snd_rd & cfg_dcs),
	.status     (snd_status),
	.rdata      (snd_rdata),

	.rom_addr   (dcs_sd_addr),
	.rom_req    (dcs_sd_req),
	.rom_ack    (snd_sd_ack),
	.rom_data   (snd_sd_data),

	.audio      (dcs_audio)
);

wire signed [15:0] audio = cfg_dcs ? dcs_audio : adpcm_audio;

assign AUDIO_L   = audio;
assign AUDIO_R   = audio;
assign AUDIO_S   = 1'b1;
assign AUDIO_MIX = 2'd0;

//////////////////////////////////////////////////////////////////
// SDRAM: sound CPU first (it cannot wait long), then the 34010, its main
// RAM writes, the blitter and the OKI; ROM downloads use the write port
//////////////////////////////////////////////////////////////////

// The SDRAM write channel serves two clients with their own req/ack
// toggles: ROM downloads and the board's main RAM write queue. This
// arbiter owns the channel's toggle and hands each acknowledge back to
// the client it served.
reg  [24:1] sd_wr_addr;
reg  [15:0] sd_wr_data;
reg         sd_wr_req = 1'b0;
reg         sd_wr_busy = 1'b0;
reg         sd_wr_src;              // 0: download, 1: board

always @(posedge clk_sys) begin
	if (sd_wr_busy) begin
		if (sd_wr_ack == sd_wr_req) begin
			sd_wr_busy <= 1'b0;
			if (sd_wr_src) ram_wr_ack <= ram_wr_req;
			else           dl_wr_ack  <= dl_wr_req;
		end
	end
	else if (dl_wr_req != dl_wr_ack) begin
		sd_wr_addr <= dl_wr_addr;
		sd_wr_data <= dl_wr_data;
		sd_wr_req  <= ~sd_wr_req;
		sd_wr_src  <= 1'b0;
		sd_wr_busy <= 1'b1;
	end
	else if (ram_wr_req != ram_wr_ack) begin
		sd_wr_addr <= ram_wr_addr;
		sd_wr_data <= ram_wr_data;
		sd_wr_req  <= ~sd_wr_req;
		sd_wr_src  <= 1'b1;
		sd_wr_busy <= 1'b1;
	end
end

sdram sdram
(
	.init        (~pll_locked),
	.clk         (clk_sys),

	.SDRAM_DQ    (SDRAM_DQ),
	.SDRAM_A     (SDRAM_A),
	.SDRAM_DQML  (SDRAM_DQML),
	.SDRAM_DQMH  (SDRAM_DQMH),
	.SDRAM_BA    (SDRAM_BA),
	.SDRAM_nCS   (SDRAM_nCS),
	.SDRAM_nWE   (SDRAM_nWE),
	.SDRAM_nRAS  (SDRAM_nRAS),
	.SDRAM_nCAS  (SDRAM_nCAS),
	.SDRAM_CKE   (SDRAM_CKE),
	.SDRAM_CLK   (SDRAM_CLK),

	.ch0_addr    (cfg_dcs ? dcs_sd_addr : snd_sd_addr),
	.ch0_req     (cfg_dcs ? dcs_sd_req  : snd_sd_req),
	.ch0_ack     (snd_sd_ack),
	.ch0_dout    (snd_sd_data),

	.ch1_addr    (cpu_sd_addr),
	.ch1_req     (cpu_sd_req),
	.ch1_ack     (cpu_sd_ack),
	.ch1_dout    (cpu_sd_data),

	.ch2_addr    (dma_sd_addr),
	.ch2_req     (dma_sd_req),
	.ch2_ack     (dma_sd_ack),
	.ch2_dout    (dma_sd_data),

	.ch3_addr    (oki_sd_addr),
	.ch3_req     (oki_sd_req),
	.ch3_ack     (oki_sd_ack),
	.ch3_dout    (oki_sd_data),

	.wr_addr     (sd_wr_addr),
	.wr_data     (sd_wr_data),
	.wr_be       (2'b11),
	.wr_req      (sd_wr_req),
	.wr_ack      (sd_wr_ack)
);

//////////////////////////////////////////////////////////////////
// Video
//////////////////////////////////////////////////////////////////

// ---- Information window (rtl/tunit_window.sv) ----
//
// View Secret Players (NBA Jam, TE; O[67:65]: Off, Page 1-n: the players,
// then the cheat codes) and Move List (MK, MK2; O[64:61]: Off, MK List 1 /
// List 2 with several fighters to a page, MK2 a fighter) draw a page over
// the game's dimmed title screen in place of the picture; the game waits
// meanwhile (pause above). The first page and page count of each list:
// rtl/tunit_window_pages.svh.

wire [4:0] list_p0  = menu_te ? WIN_NBAJAMTE : menu_nj ? WIN_NBAJAM : menu_mk2 ? WIN_MK2 : WIN_MK;
wire [4:0] win_page = list_p0 + {1'b0, list_sel} - 5'd1;
wire [1:0] win_game = menu_nj ? 2'd0 : menu_te ? 2'd1 : menu_mk2 ? 2'd3 : 2'd2;

tunit_window tunit_window
(
	.clk     (clk_sys),
	.ce_pix  (ce_pix),
	.enable  ((splist_on | movelist_on) & ~load_black),
	.page    (win_page),
	.game    (win_game),

	.r_in    (load_black ? 8'd0 : brd_r),
	.g_in    (load_black ? 8'd0 : brd_g),
	.b_in    (load_black ? 8'd0 : brd_b),
	.hb_in   (core_hb),
	.vb_in   (core_vb),

	.r_out   (core_r),
	.g_out   (core_g),
	.b_out   (core_b)
);

// ---- analog CRT stage: centred sync, CRT V-Size, CRT Adjust, Auto-Width (rtl/video/tunit_crt.sv) ----
//
// The analog sync is always the centred one (picture in the middle of a
// standard 15 kHz line and frame); HDMI sees the same picture either way.
// CRT Adjust is off while a scandoubler effect is on (its read rate assumes
// native 15 kHz).

wire scandoubler = (status[5:3] != 3'd0) || forced_scandoubler;

wire       c_hs, c_vs;
wire       crt_on, rd_ce, de_osd;
wire [7:0] str_r, str_g, str_b;
wire       str_hs, str_vs;

tunit_crt tunit_crt
(
	.clk         (clk_sys),
	.ce_pix      (ce_pix),

	.crt_en      (status[101]),
	.autow       (status[102]),
	.scandoubler (scandoubler),
	.hsize_osd   (status[100:96]),
	.hpos_osd    (status[85:79]),
	.vshift_osd  (status[78:74]),
	.vsize_osd   (status[107:104]),
	.vsmode_osd  (status[108]),

	.r_in        (core_r),
	.g_in        (core_g),
	.b_in        (core_b),
	.hs_in       (core_hs),
	.vs_in       (core_vs),
	.hb_in       (core_hb),
	.vb_in       (core_vb),

	.c_hs        (c_hs),
	.c_vs        (c_vs),

	.crt_on      (crt_on),
	.rd_ce       (rd_ce),
	.r_out       (str_r),
	.g_out       (str_g),
	.b_out       (str_b),
	.hs_out      (str_hs),
	.vs_out      (str_vs),
	.de_osd      (de_osd),

	.centred     (),
	.pic_dots    (),
	.h_eff       (),
	.str_act     ()
);

// ---- scandoubler / gamma (native stream) ----

wire [7:0] mix_r, mix_g, mix_b;
wire       mix_hs, mix_vs, mix_de;
wire [1:0] mix_sl;
wire       mix_ce;

arcade_video #(.WIDTH(512), .DW(24), .GAMMA(1)) arcade_video
(
	.clk_video          (clk_sys),
	.ce_pix             (ce_pix),

	.RGB_in             ({core_r, core_g, core_b}),
	.HBlank             (core_hb),
	.VBlank             (core_vb),
	.HSync              (c_hs),               // centred sync
	.VSync              (c_vs),

	.CLK_VIDEO          (CLK_VIDEO),
	.CE_PIXEL           (mix_ce),
	.VGA_R              (mix_r),
	.VGA_G              (mix_g),
	.VGA_B              (mix_b),
	.VGA_HS             (mix_hs),
	.VGA_VS             (mix_vs),
	.VGA_DE             (mix_de),
	.VGA_SL             (mix_sl),

	.fx                 (status[5:3]),
	.forced_scandoubler (forced_scandoubler),
	.gamma_bus          (gamma_bus)
);

assign CE_PIXEL = crt_on ? rd_ce  : mix_ce;
assign VGA_R    = crt_on ? str_r  : mix_r;
assign VGA_G    = crt_on ? str_g  : mix_g;
assign VGA_B    = crt_on ? str_b  : mix_b;
assign VGA_HS   = crt_on ? str_hs : mix_hs;
assign VGA_VS   = crt_on ? str_vs : mix_vs;
assign VGA_SL   = crt_on ? 2'd0   : mix_sl;

wire [1:0] ar = status[2:1];

video_freak video_freak
(
	.CLK_VIDEO   (CLK_VIDEO),
	.CE_PIXEL    (CE_PIXEL),
	.VGA_VS      (VGA_VS),
	.HDMI_WIDTH  (HDMI_WIDTH),
	.HDMI_HEIGHT (HDMI_HEIGHT),
	.VGA_DE      (VGA_DE),
	.VIDEO_ARX   (VIDEO_ARX),
	.VIDEO_ARY   (VIDEO_ARY),

	.VGA_DE_IN   (crt_on ? de_osd : mix_de),
	.ARX         ((ar == 2'd0) ? 12'd4 : ({10'd0, ar} - 12'd1)),
	.ARY         ((ar == 2'd0) ? 12'd3 : 12'd0),
	.CROP_SIZE   (12'd0),
	.CROP_OFF    (5'd0),
	.SCALE       ({1'b0, status[7:6]})
);

//////////////////////////////////////////////////////////////////

reg [26:0] act_cnt;
always @(posedge clk_sys) act_cnt <= act_cnt + 1'd1;
assign LED_USER = rom_download ? act_cnt[23] : 1'b0;

endmodule

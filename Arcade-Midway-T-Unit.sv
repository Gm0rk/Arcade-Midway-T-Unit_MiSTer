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
	"P1O[101],CRT Adjust,Off,On;",
	"H1P1O[102],CRT Auto-Width,Off,On;",
	"H1P1O[100:96],CRT H-Size,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14,+15,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[85:79],CRT H-Position,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14,+15,+16,+17,+18,+19,+20,+21,+22,+23,+24,+25,+26,+27,+28,+29,+30,+31,+32,+33,+34,+35,+36,+37,+38,+39,+40,+41,+42,+43,+44,+45,+46,+47,+48,-48,-47,-46,-45,-44,-43,-42,-41,-40,-39,-38,-37,-36,-35,-34,-33,-32,-31,-30,-29,-28,-27,-26,-25,-24,-23,-22,-21,-20,-19,-18,-17,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[78:74],CRT V-Shift,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14,+15,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[107:104],CRT V-Size,0,+1,+2,+3,+4,+5,+6,+7,-7,-6,-5,-4,-3,-2,-1;",
	"H1P1O[108],CRT V-Size Mode,PVM,Cabinet;",
	"P2,Controls;",
	"P2-;",
	"P2O[9],Service Mode,Off,On;",
	"P2T[12],Service Credit;",
	"P2T[13],Tilt;",
	"h2P3,Secrets;",
	"P3-;",
	"h3P3R[14],EJB Menu;",
	"h4P3R[15],EJB Menu (Copyright Screen);",
	"h5P3O[16],Security Screen,Off,On;",
	"h5P3O[17],Hitboxes,Off,On;",
	"h5P3O[18],Pong at Battle 250,Off,On;",
	"h5P3O[19],Noob Saibot Fight,Off,On;",
	"h5P3O[20],Jade Fight,Off,On;",
	"h5P3O[21],Smoke Fight,Off,On;",
	"h6P3R[14],Secret Menu;",
	`NBA_OSD,
	"h7P3R[14],Secret Audits;",
	"h7P3R[15],Secret Audits + Credits;",
	"P3-;",
	"P3-,Codes work in attract mode;",
	`FMOVES_OSD,
	"-;",
	"DIP;",
	"-;",
	"O[8],Pause when OSD is open,On,Off;",
	"-;",
	"R[0],Reset;",
	"J1,B1,B2,B3,B4,B5,B6,Start,Coin,Test,Pause;",
	"jn,A,B,X,Y,L,R,Start,Select,,;",
	`CORE_INFO,
	"V,v",`BUILD_DATE
};

// OSD menu mask bits (assigned in "Game configuration"): which secrets the
// loaded game has; bits 8-11 the fighter picked on the Finishing Moves and
// Move List pages; bits 12 and 13 NBA Jam and TE (their own Secrets lines,
// rtl/tunit_secrets_osd.svh)
wire        menu_secrets, menu_ejb, menu_mk, menu_mk2, menu_nba, menu_jd, menu_nj, menu_te;
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
	.status_menumask     ({2'd0, menu_te, menu_nj, fm_line, menu_jd, menu_nba, menu_mk2, menu_mk, menu_ejb, menu_secrets, ~status[101], 1'b0}),
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
// reset for half a second after any download so the game never boots on an
// empty CMOS that is about to be replaced.
reg  [25:0] boot_hold;
always @(posedge clk_sys) begin
	if (ioctl_download)
		boot_hold <= 26'd48_000_000;
	else if (boot_hold != 26'd0)
		boot_hold <= boot_hold - 26'd1;
end

wire reset = RESET | status[0] | buttons[1] | rom_download | ~rom_loaded | (boot_hold != 26'd0);

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

// OSD Secrets page items for the loaded game (status_menumask bits 2-7)
assign menu_secrets = (game_id <= G_JDREDDP);
assign menu_ejb     = (game_id == G_MK) || (game_id == G_MKTURBO) || (game_id == G_MK2);
assign menu_mk      = (game_id == G_MK) || (game_id == G_MKTURBO);
assign menu_mk2     = (game_id == G_MK2);
assign menu_nba     = (game_id == G_NBAJAM) || (game_id == G_NBAJAMTE);
assign menu_nj      = (game_id == G_NBAJAM);
assign menu_te      = (game_id == G_NBAJAMTE);
assign menu_jd      = (game_id == G_JDREDDP);

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
	if (ioctl_wr && ioctl_index == 16'd1 && ioctl_addr == 27'd0)
		game_id <= ioctl_dout[2:0];
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
// 13 Pause. B1-B6 are MAME's BUTTON1-BUTTON6 of each game. Ports are active
// low; the layouts follow MAME's input ports (midtunit.cpp).
//
// Service Credit and Tilt are not on the controllers: they are OSD items
// (Controls page), handled in "OSD service credit and tilt" below.
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

// secrets code player (OSD Secrets page): while it plays a code it replaces
// IN0 and holds the start buttons it needs
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
			// B1 high punch, B2 block, B3 high kick, B4 low punch, B5 low kick, B6 block 2
			in0[3:0]   = udlr(joy0);  in0[6:4]   = joy0[6:4];
			in0[11:8]  = udlr(joy1);  in0[14:12] = joy1[6:4];
			in1[11:9]  = joy1[9:7];
			in1[13:12] = joy0[8:7];
			in1[15]    = joy0[9];
		end
		L_MK2: begin
			in0[3:0]   = udlr(joy0);  in0[6:4]   = joy0[6:4];
			in0[11:8]  = udlr(joy1);  in0[14:12] = joy1[6:4];
			in2[2:0]   = joy0[9:7];
			in2[6:4]   = joy1[9:7];
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

// the Move List window (see Video) holds the game too
wire movelist_on = menu_ejb & status[44];
wire pause = pause_toggle | (OSD_STATUS & ~status[8]) | movelist_on;

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
wire  [7:0] core_r, core_g, core_b;       // with the information window
wire        core_hs, core_vs, core_hb, core_vb;

//////////////////////////////////////////////////////////////////
// OSD service credit and tilt
//
// Each OSD item is a trigger: the HPS sets its status bit briefly when it
// is selected. The matching cabinet switch is then held closed for 8
// frames (about 150 ms), long enough for the game's switch scan to accept
// it, like a real coin or slam switch. Frames are counted only while the
// game runs, so with "Pause when OSD is open" the switch closes when the
// OSD is shut.
//////////////////////////////////////////////////////////////////

reg  [1:0] osd_sw_d;
reg        osd_vb_d;
wire       osd_frame = core_vb & ~osd_vb_d & ~pause;   // start of a running frame

always @(posedge clk_sys) begin
	osd_sw_d <= status[13:12];
	osd_vb_d <= core_vb;

	if (reset) begin
		svc_cnt  <= 4'd0;
		tilt_cnt <= 4'd0;
	end
	else begin
		if (status[12] & ~osd_sw_d[0])   svc_cnt  <= 4'd8;
		else if (osd_frame && svc_sw)    svc_cnt  <= svc_cnt - 4'd1;

		if (status[13] & ~osd_sw_d[1])   tilt_cnt <= 4'd8;
		else if (osd_frame && tilt_sw)   tilt_cnt <= tilt_cnt - 4'd1;
	end
end

//////////////////////////////////////////////////////////////////
// OSD secrets (Secrets page)
//
// R[14] / R[15] play the loaded set's code 1 / code 2 (hidden menus, entered
// on the controls during the attract mode); the options switch its read
// patches through the option slots of rtl/tunit_secrets.sv (MK2, O[21:16]:
// security screen, hitboxes, Pong at battle 250, Noob Saibot, Jade and
// Smoke fights; NBA Jam and TE, O[55:48]: the power-ups, slots in the
// order of tools/tunit_secrets.py's NJ_* / TE_* codes). The codes and
// patch addresses come with the MRA (ROM index 1), found per revision by
// tools/tunit_secrets.py.
// Frames are counted while the game runs, so with "Pause when OSD is open"
// a code starts when the OSD closes.
//////////////////////////////////////////////////////////////////

wire  [1:0] te_head  = status[49:48];          // TE Head Size: Normal, Big, Huge
wire [10:0] sec_opt  = menu_mk2 ? {5'd0, status[21:16]} :
                       menu_nj  ? {6'd0, status[53], status[52], status[51], status[50], status[48]} :
                       menu_te  ? {3'd0, status[53], status[52], status[50], status[51], status[55],
                                   status[54], te_head == 2'd2, te_head != 2'd0} :
                                  11'd0;
wire [10:0] opt_avail;

wire [223:0] pt_addr;
wire [127:0] pt_data;
wire   [7:0] pt_en;
wire         cpu_rd;             // the board's completed CPU reads (a code's success)
wire         cpu_wr;             // and writes (the finishing-move player follows the fight)
wire  [27:0] cpu_wa;
wire  [15:0] cpu_wd;
wire         code_ok, code_fail;

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
	.opt_avail  (opt_avail),

	.pt_addr    (pt_addr),
	.pt_data    (pt_data),
	.pt_en      (pt_en)
);

//////////////////////////////////////////////////////////////////
// Finishing moves (MK, MK2)
//
// The Finishing Moves page picks a fighter (O[30:28] MK, O[27:24] MK2; the
// menu mask's bits 8-11 show that fighter's lines) and one of its moves
// (R[32]-R[39], the fighter's lines in order; R[40] clears the set move).
// The Move List page (P5) has the same Fighter option and shows that
// fighter's special moves as text lines; nothing in the core acts on it.
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
	.game_mk2  (menu_mk2),

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
// The finishing-move player's, the secrets' codes (their menu opened, or
// not) and the Secrets page's options turned on (looked at when the OSD
// closes: what an MK2 option does, that an NBA Jam / TE power-up is on for
// all players, or that this revision does not have it). Main_MiSTer shows a message for 2 s, and only with the OSD
// closed: messages wait in a set (lowest number first) and go out one
// every 2.2 s, starting 0.3 s after the OSD closes.
//////////////////////////////////////////////////////////////////

localparam [27:0] MSG_GAP   = 28'd211_200_000;     // 2.2 s at 96 MHz
localparam [27:0] MSG_DELAY = 28'd28_800_000;      // 0.3 s

reg  [31:1] msg_pend;
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

integer mi, si;
always @(*) begin
	msg_num = 5'd0;
	for (mi = 31; mi >= 1; mi = mi - 1)
		if (msg_pend[mi]) msg_num = mi[4:0];
end

always @(posedge clk_sys) begin
	osd_was <= OSD_STATUS;
	msg_out <= 1'b0;

	if (OSD_STATUS & ~osd_was) sec_open <= sec_opt;

	if (fm_msg_req) msg_pend[fm_msg] <= 1'b1;
	if (code_ok)    msg_pend[MSG_CODE_OK] <= 1'b1;
	if (code_fail)  msg_pend[MSG_CODE_FAIL] <= 1'b1;
	if (~OSD_STATUS & osd_was) begin
		for (si = 0; si < 11; si = si + 1)
			if (sec_opt[si] & ~sec_open[si])
				msg_pend[~opt_avail[si] ? MSG_NOT_HERE : menu_mk2 ? sec_msg_mk2(si) :
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
	.vid_hs         (core_hs),
	.vid_vs         (core_vs),
	.vid_hb         (core_hb),
	.vid_vb         (core_vb),

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
// The Secrets page's Secret Player List (NBA Jam, TE; O[43:41]: NBA Jam Off /
// On, TE Off / Page 1-n) and the Move List page's Show Move List (MK, MK2;
// O[44], the page of the fighter picked under Fighter: O[30:28] MK, several
// fighters to a page, O[27:24] MK2) draw a page over the game's dimmed title
// screen in place of the picture. The game runs on behind the Secret Player
// List and waits behind the Move List (pause above). The first page of each
// list and the MK fighters' pages: rtl/tunit_window_pages.svh.

wire [2:0] splist_sel = status[43:41];
wire       splist_on  = menu_nba && splist_sel != 3'd0 && (menu_te || splist_sel == 3'd1);

wire [4:0] win_page = menu_te  ? WIN_NBAJAMTE + {2'd0, splist_sel} - 5'd1 :
                      menu_nj  ? WIN_NBAJAM :
                      menu_mk2 ? WIN_MK2 + {1'b0, status[27:24]} :
                                 win_mk_page(status[30:28]);
wire [1:0] win_game = menu_nj ? 2'd0 : menu_te ? 2'd1 : menu_mk2 ? 2'd3 : 2'd2;

tunit_window tunit_window
(
	.clk     (clk_sys),
	.ce_pix  (ce_pix),
	.enable  (splist_on | movelist_on),
	.page    (win_page),
	.game    (win_game),

	.r_in    (brd_r),
	.g_in    (brd_g),
	.b_in    (brd_b),
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

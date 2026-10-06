//============================================================================
//  T-Unit protection tables (MAME midtunit_m.cpp), included by midway_tunit
//
//  Generated from the tables in MAME 0.289's midtunit_m.cpp; the values
//  read back are these bytes shifted left 9 bits.
//
//  Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
//============================================================================

// MK: mk_prot_values (57 entries, 0xFF last)
function automatic [7:0] mk_val(input [5:0] i);
	case (i)
		6'd0: mk_val = 8'h13; 6'd1: mk_val = 8'h27; 6'd2: mk_val = 8'h0F; 6'd3: mk_val = 8'h1F; 6'd4: mk_val = 8'h3E; 6'd5: mk_val = 8'h3D; 6'd6: mk_val = 8'h3B; 6'd7: mk_val = 8'h37;
		6'd8: mk_val = 8'h2E; 6'd9: mk_val = 8'h1C; 6'd10: mk_val = 8'h38; 6'd11: mk_val = 8'h31; 6'd12: mk_val = 8'h22; 6'd13: mk_val = 8'h05; 6'd14: mk_val = 8'h0A; 6'd15: mk_val = 8'h15;
		6'd16: mk_val = 8'h2B; 6'd17: mk_val = 8'h16; 6'd18: mk_val = 8'h2D; 6'd19: mk_val = 8'h1A; 6'd20: mk_val = 8'h34; 6'd21: mk_val = 8'h28; 6'd22: mk_val = 8'h10; 6'd23: mk_val = 8'h21;
		6'd24: mk_val = 8'h03; 6'd25: mk_val = 8'h06; 6'd26: mk_val = 8'h0C; 6'd27: mk_val = 8'h19; 6'd28: mk_val = 8'h32; 6'd29: mk_val = 8'h24; 6'd30: mk_val = 8'h09; 6'd31: mk_val = 8'h13;
		6'd32: mk_val = 8'h27; 6'd33: mk_val = 8'h0F; 6'd34: mk_val = 8'h1F; 6'd35: mk_val = 8'h3E; 6'd36: mk_val = 8'h3D; 6'd37: mk_val = 8'h3B; 6'd38: mk_val = 8'h37; 6'd39: mk_val = 8'h2E;
		6'd40: mk_val = 8'h1C; 6'd41: mk_val = 8'h38; 6'd42: mk_val = 8'h31; 6'd43: mk_val = 8'h22; 6'd44: mk_val = 8'h05; 6'd45: mk_val = 8'h0A; 6'd46: mk_val = 8'h15; 6'd47: mk_val = 8'h2B;
		6'd48: mk_val = 8'h16; 6'd49: mk_val = 8'h2D; 6'd50: mk_val = 8'h1A; 6'd51: mk_val = 8'h34; 6'd52: mk_val = 8'h28; 6'd53: mk_val = 8'h10; 6'd54: mk_val = 8'h21; 6'd55: mk_val = 8'h03;
		6'd56: mk_val = 8'hFF;
		default: mk_val = 8'h00;
	endcase
endfunction

// MK: index of the first entry equal to a written value (0 if none)
function automatic [5:0] mk_first(input [5:0] v);
	case (v)
		6'h03: mk_first = 6'd24; 6'h05: mk_first = 6'd13; 6'h06: mk_first = 6'd25; 6'h09: mk_first = 6'd30; 6'h0A: mk_first = 6'd14; 6'h0C: mk_first = 6'd26;
		6'h0F: mk_first = 6'd2; 6'h10: mk_first = 6'd22; 6'h13: mk_first = 6'd0; 6'h15: mk_first = 6'd15; 6'h16: mk_first = 6'd17; 6'h19: mk_first = 6'd27;
		6'h1A: mk_first = 6'd19; 6'h1C: mk_first = 6'd9; 6'h1F: mk_first = 6'd3; 6'h21: mk_first = 6'd23; 6'h22: mk_first = 6'd12; 6'h24: mk_first = 6'd29;
		6'h27: mk_first = 6'd1; 6'h28: mk_first = 6'd21; 6'h2B: mk_first = 6'd16; 6'h2D: mk_first = 6'd18; 6'h2E: mk_first = 6'd8; 6'h31: mk_first = 6'd11;
		6'h32: mk_first = 6'd28; 6'h34: mk_first = 6'd20; 6'h37: mk_first = 6'd7; 6'h38: mk_first = 6'd10; 6'h3B: mk_first = 6'd6; 6'h3D: mk_first = 6'd5;
		6'h3E: mk_first = 6'd4;
		default: mk_first = 6'd0;
	endcase
endfunction

// NBA Jam / NBA Jam TE: nbajam_prot_values, nbajamte_prot_values
// (index: {te, table index})
function automatic [31:0] nba_val(input [7:0] i);
	case (i)
		8'h00: nba_val = 32'h21283B3B; 8'h01: nba_val = 32'h2439383B; 8'h02: nba_val = 32'h31283B3B; 8'h03: nba_val = 32'h302B3938;
		8'h04: nba_val = 32'h31283B3B; 8'h05: nba_val = 32'h302B3938; 8'h06: nba_val = 32'h232F2F2F; 8'h07: nba_val = 32'h26383B3B;
		8'h08: nba_val = 32'h21283B3B; 8'h09: nba_val = 32'h2439383B; 8'h0A: nba_val = 32'h312A1224; 8'h0B: nba_val = 32'h302B1120;
		8'h0C: nba_val = 32'h312A1224; 8'h0D: nba_val = 32'h302B1120; 8'h0E: nba_val = 32'h232D283B; 8'h0F: nba_val = 32'h26383B3B;
		8'h10: nba_val = 32'h2B3B3B3B; 8'h11: nba_val = 32'h2E2E2E2E; 8'h12: nba_val = 32'h39383B1B; 8'h13: nba_val = 32'h383B3B1B;
		8'h14: nba_val = 32'h3B3B3B1B; 8'h15: nba_val = 32'h3A3A3A1A; 8'h16: nba_val = 32'h2B3B3B3B; 8'h17: nba_val = 32'h2E2E2E2E;
		8'h18: nba_val = 32'h2B39383B; 8'h19: nba_val = 32'h2E2E2E2E; 8'h1A: nba_val = 32'h393A1A18; 8'h1B: nba_val = 32'h383B1B1B;
		8'h1C: nba_val = 32'h3B3B1B1B; 8'h1D: nba_val = 32'h3A3A1A18; 8'h1E: nba_val = 32'h2B39383B; 8'h1F: nba_val = 32'h2E2E2E2E;
		8'h20: nba_val = 32'h01202B3B; 8'h21: nba_val = 32'h0431283B; 8'h22: nba_val = 32'h11202B3B; 8'h23: nba_val = 32'h1021283B;
		8'h24: nba_val = 32'h11202B3B; 8'h25: nba_val = 32'h1021283B; 8'h26: nba_val = 32'h03273B3B; 8'h27: nba_val = 32'h06302B39;
		8'h28: nba_val = 32'h09302B39; 8'h29: nba_val = 32'h0C232F2F; 8'h2A: nba_val = 32'h19322E06; 8'h2B: nba_val = 32'h18312A12;
		8'h2C: nba_val = 32'h19322E06; 8'h2D: nba_val = 32'h18312A12; 8'h2E: nba_val = 32'h0B31283B; 8'h2F: nba_val = 32'h0E26383B;
		8'h30: nba_val = 32'h03273B3B; 8'h31: nba_val = 32'h06302B39; 8'h32: nba_val = 32'h11202B3B; 8'h33: nba_val = 32'h1021283B;
		8'h34: nba_val = 32'h13273938; 8'h35: nba_val = 32'h12243938; 8'h36: nba_val = 32'h03273B3B; 8'h37: nba_val = 32'h06302B39;
		8'h38: nba_val = 32'h0B31283B; 8'h39: nba_val = 32'h0E26383B; 8'h3A: nba_val = 32'h19322E06; 8'h3B: nba_val = 32'h18312A12;
		8'h3C: nba_val = 32'h1B332F05; 8'h3D: nba_val = 32'h1A302B11; 8'h3E: nba_val = 32'h0B31283B; 8'h3F: nba_val = 32'h0E26383B;
		8'h40: nba_val = 32'h21283B3B; 8'h41: nba_val = 32'h2439383B; 8'h42: nba_val = 32'h31283B3B; 8'h43: nba_val = 32'h302B3938;
		8'h44: nba_val = 32'h31283B3B; 8'h45: nba_val = 32'h302B3938; 8'h46: nba_val = 32'h232F2F2F; 8'h47: nba_val = 32'h26383B3B;
		8'h48: nba_val = 32'h21283B3B; 8'h49: nba_val = 32'h2439383B; 8'h4A: nba_val = 32'h312A1224; 8'h4B: nba_val = 32'h302B1120;
		8'h4C: nba_val = 32'h312A1224; 8'h4D: nba_val = 32'h302B1120; 8'h4E: nba_val = 32'h232D283B; 8'h4F: nba_val = 32'h26383B3B;
		8'h50: nba_val = 32'h2B3B3B3B; 8'h51: nba_val = 32'h2E2E2E2E; 8'h52: nba_val = 32'h39383B1B; 8'h53: nba_val = 32'h383B3B1B;
		8'h54: nba_val = 32'h3B3B3B1B; 8'h55: nba_val = 32'h3A3A3A1A; 8'h56: nba_val = 32'h2B3B3B3B; 8'h57: nba_val = 32'h2E2E2E2E;
		8'h58: nba_val = 32'h2B39383B; 8'h59: nba_val = 32'h2E2E2E2E; 8'h5A: nba_val = 32'h393A1A18; 8'h5B: nba_val = 32'h383B1B1B;
		8'h5C: nba_val = 32'h3B3B1B1B; 8'h5D: nba_val = 32'h3A3A1A18; 8'h5E: nba_val = 32'h2B39383B; 8'h5F: nba_val = 32'h2E2E2E2E;
		8'h60: nba_val = 32'h01202B3B; 8'h61: nba_val = 32'h0431283B; 8'h62: nba_val = 32'h11202B3B; 8'h63: nba_val = 32'h1021283B;
		8'h64: nba_val = 32'h11202B3B; 8'h65: nba_val = 32'h1021283B; 8'h66: nba_val = 32'h03273B3B; 8'h67: nba_val = 32'h06302B39;
		8'h68: nba_val = 32'h09302B39; 8'h69: nba_val = 32'h0C232F2F; 8'h6A: nba_val = 32'h19322E06; 8'h6B: nba_val = 32'h18312A12;
		8'h6C: nba_val = 32'h19322E06; 8'h6D: nba_val = 32'h18312A12; 8'h6E: nba_val = 32'h0B31283B; 8'h6F: nba_val = 32'h0E26383B;
		8'h70: nba_val = 32'h03273B3B; 8'h71: nba_val = 32'h06302B39; 8'h72: nba_val = 32'h11202B3B; 8'h73: nba_val = 32'h1021283B;
		8'h74: nba_val = 32'h13273938; 8'h75: nba_val = 32'h12243938; 8'h76: nba_val = 32'h03273B3B; 8'h77: nba_val = 32'h06302B39;
		8'h78: nba_val = 32'h0B31283B; 8'h79: nba_val = 32'h0E26383B; 8'h7A: nba_val = 32'h19322E06; 8'h7B: nba_val = 32'h18312A12;
		8'h7C: nba_val = 32'h1B332F05; 8'h7D: nba_val = 32'h1A302B11; 8'h7E: nba_val = 32'h0B31283B; 8'h7F: nba_val = 32'h0E26383B;
		8'h80: nba_val = 32'h00000000; 8'h81: nba_val = 32'h04081020; 8'h82: nba_val = 32'h08102000; 8'h83: nba_val = 32'h0C183122;
		8'h84: nba_val = 32'h10200000; 8'h85: nba_val = 32'h14281020; 8'h86: nba_val = 32'h18312204; 8'h87: nba_val = 32'h1C393326;
		8'h88: nba_val = 32'h20000001; 8'h89: nba_val = 32'h24081021; 8'h8A: nba_val = 32'h28102000; 8'h8B: nba_val = 32'h2C183122;
		8'h8C: nba_val = 32'h30200001; 8'h8D: nba_val = 32'h34281021; 8'h8E: nba_val = 32'h38312204; 8'h8F: nba_val = 32'h3C393326;
		8'h90: nba_val = 32'h00000102; 8'h91: nba_val = 32'h04081122; 8'h92: nba_val = 32'h08102102; 8'h93: nba_val = 32'h0C183122;
		8'h94: nba_val = 32'h10200000; 8'h95: nba_val = 32'h14281020; 8'h96: nba_val = 32'h18312204; 8'h97: nba_val = 32'h1C393326;
		8'h98: nba_val = 32'h20000103; 8'h99: nba_val = 32'h24081123; 8'h9A: nba_val = 32'h28102102; 8'h9B: nba_val = 32'h2C183122;
		8'h9C: nba_val = 32'h30200001; 8'h9D: nba_val = 32'h34281021; 8'h9E: nba_val = 32'h38312204; 8'h9F: nba_val = 32'h3C393326;
		8'hA0: nba_val = 32'h00010204; 8'hA1: nba_val = 32'h04091224; 8'hA2: nba_val = 32'h08112204; 8'hA3: nba_val = 32'h0C193326;
		8'hA4: nba_val = 32'h10210204; 8'hA5: nba_val = 32'h14291224; 8'hA6: nba_val = 32'h18312204; 8'hA7: nba_val = 32'h1C393326;
		8'hA8: nba_val = 32'h20000001; 8'hA9: nba_val = 32'h24081021; 8'hAA: nba_val = 32'h28102000; 8'hAB: nba_val = 32'h2C183122;
		8'hAC: nba_val = 32'h30200001; 8'hAD: nba_val = 32'h34281021; 8'hAE: nba_val = 32'h38312204; 8'hAF: nba_val = 32'h3C393326;
		8'hB0: nba_val = 32'h00010306; 8'hB1: nba_val = 32'h04091326; 8'hB2: nba_val = 32'h08112306; 8'hB3: nba_val = 32'h0C193326;
		8'hB4: nba_val = 32'h10210204; 8'hB5: nba_val = 32'h14291224; 8'hB6: nba_val = 32'h18312204; 8'hB7: nba_val = 32'h1C393326;
		8'hB8: nba_val = 32'h20000103; 8'hB9: nba_val = 32'h24081123; 8'hBA: nba_val = 32'h28102102; 8'hBB: nba_val = 32'h2C183122;
		8'hBC: nba_val = 32'h30200001; 8'hBD: nba_val = 32'h34281021; 8'hBE: nba_val = 32'h38312204; 8'hBF: nba_val = 32'h3C393326;
		8'hC0: nba_val = 32'h00000000; 8'hC1: nba_val = 32'h01201028; 8'hC2: nba_val = 32'h02213018; 8'hC3: nba_val = 32'h03012030;
		8'hC4: nba_val = 32'h04223138; 8'hC5: nba_val = 32'h05022110; 8'hC6: nba_val = 32'h06030120; 8'hC7: nba_val = 32'h07231108;
		8'hC8: nba_val = 32'h08042231; 8'hC9: nba_val = 32'h09243219; 8'hCA: nba_val = 32'h0A251229; 8'hCB: nba_val = 32'h0B050201;
		8'hCC: nba_val = 32'h0C261309; 8'hCD: nba_val = 32'h0D060321; 8'hCE: nba_val = 32'h0E072311; 8'hCF: nba_val = 32'h0F273339;
		8'hD0: nba_val = 32'h10080422; 8'hD1: nba_val = 32'h1128140A; 8'hD2: nba_val = 32'h1229343A; 8'hD3: nba_val = 32'h13092412;
		8'hD4: nba_val = 32'h142A351A; 8'hD5: nba_val = 32'h150A2532; 8'hD6: nba_val = 32'h160B0502; 8'hD7: nba_val = 32'h172B152A;
		8'hD8: nba_val = 32'h180C2613; 8'hD9: nba_val = 32'h192C363B; 8'hDA: nba_val = 32'h1A2D160B; 8'hDB: nba_val = 32'h1B0D0623;
		8'hDC: nba_val = 32'h1C2E172B; 8'hDD: nba_val = 32'h1D0E0703; 8'hDE: nba_val = 32'h1E0F2733; 8'hDF: nba_val = 32'h1F2F371B;
		8'hE0: nba_val = 32'h20100804; 8'hE1: nba_val = 32'h2130182C; 8'hE2: nba_val = 32'h2231381C; 8'hE3: nba_val = 32'h23112834;
		8'hE4: nba_val = 32'h2432393C; 8'hE5: nba_val = 32'h25122914; 8'hE6: nba_val = 32'h26130924; 8'hE7: nba_val = 32'h2733190C;
		8'hE8: nba_val = 32'h28142A35; 8'hE9: nba_val = 32'h29343A1D; 8'hEA: nba_val = 32'h2A351A2D; 8'hEB: nba_val = 32'h2B150A05;
		8'hEC: nba_val = 32'h2C361B0D; 8'hED: nba_val = 32'h2D160B25; 8'hEE: nba_val = 32'h2E172B15; 8'hEF: nba_val = 32'h2F373B3D;
		8'hF0: nba_val = 32'h30180C26; 8'hF1: nba_val = 32'h31381C0E; 8'hF2: nba_val = 32'h32393C3E; 8'hF3: nba_val = 32'h33192C16;
		8'hF4: nba_val = 32'h343A3D1E; 8'hF5: nba_val = 32'h351A2D36; 8'hF6: nba_val = 32'h361B0D06; 8'hF7: nba_val = 32'h373B1D2E;
		8'hF8: nba_val = 32'h381C2E17; 8'hF9: nba_val = 32'h393C3E3F; 8'hFA: nba_val = 32'h3A3D1E0F; 8'hFB: nba_val = 32'h3B1D0E27;
		8'hFC: nba_val = 32'h3C3E1F2F; 8'hFD: nba_val = 32'h3D1E0F07; 8'hFE: nba_val = 32'h3E1F2F37; 8'hFF: nba_val = 32'h3F3F3F1F;
		default: nba_val = 32'h00000000;
	endcase
endfunction

// Judge Dredd: the five jdredd_prot_values tables, one after the other
//   10740: entries 0-45
//   13240: entries 46-46
//   76540: entries 47-48
//   77760: entries 49-139
//   80020: entries 140-155
function automatic [5:0] jd_val(input [7:0] i);
	case (i)
		8'd0: jd_val = 6'h14; 8'd1: jd_val = 6'h2A; 8'd2: jd_val = 6'h15; 8'd3: jd_val = 6'h0A; 8'd4: jd_val = 6'h25; 8'd5: jd_val = 6'h32; 8'd6: jd_val = 6'h39; 8'd7: jd_val = 6'h1C;
		8'd8: jd_val = 6'h2E; 8'd9: jd_val = 6'h37; 8'd10: jd_val = 6'h3B; 8'd11: jd_val = 6'h1D; 8'd12: jd_val = 6'h2E; 8'd13: jd_val = 6'h37; 8'd14: jd_val = 6'h1B; 8'd15: jd_val = 6'h0D;
		8'd16: jd_val = 6'h26; 8'd17: jd_val = 6'h33; 8'd18: jd_val = 6'h39; 8'd19: jd_val = 6'h3C; 8'd20: jd_val = 6'h1E; 8'd21: jd_val = 6'h2F; 8'd22: jd_val = 6'h37; 8'd23: jd_val = 6'h3B;
		8'd24: jd_val = 6'h3D; 8'd25: jd_val = 6'h3E; 8'd26: jd_val = 6'h3F; 8'd27: jd_val = 6'h1F; 8'd28: jd_val = 6'h2F; 8'd29: jd_val = 6'h17; 8'd30: jd_val = 6'h0B; 8'd31: jd_val = 6'h25;
		8'd32: jd_val = 6'h32; 8'd33: jd_val = 6'h19; 8'd34: jd_val = 6'h0C; 8'd35: jd_val = 6'h26; 8'd36: jd_val = 6'h33; 8'd37: jd_val = 6'h19; 8'd38: jd_val = 6'h2C; 8'd39: jd_val = 6'h16;
		8'd40: jd_val = 6'h2B; 8'd41: jd_val = 6'h15; 8'd42: jd_val = 6'h0A; 8'd43: jd_val = 6'h05; 8'd44: jd_val = 6'h22; 8'd45: jd_val = 6'h00; 8'd46: jd_val = 6'h28; 8'd47: jd_val = 6'h04;
		8'd48: jd_val = 6'h08; 8'd49: jd_val = 6'h14; 8'd50: jd_val = 6'h2A; 8'd51: jd_val = 6'h14; 8'd52: jd_val = 6'h2A; 8'd53: jd_val = 6'h35; 8'd54: jd_val = 6'h2A; 8'd55: jd_val = 6'h35;
		8'd56: jd_val = 6'h1A; 8'd57: jd_val = 6'h35; 8'd58: jd_val = 6'h1A; 8'd59: jd_val = 6'h2D; 8'd60: jd_val = 6'h1A; 8'd61: jd_val = 6'h2D; 8'd62: jd_val = 6'h36; 8'd63: jd_val = 6'h2D;
		8'd64: jd_val = 6'h36; 8'd65: jd_val = 6'h1B; 8'd66: jd_val = 6'h36; 8'd67: jd_val = 6'h1B; 8'd68: jd_val = 6'h36; 8'd69: jd_val = 6'h2C; 8'd70: jd_val = 6'h36; 8'd71: jd_val = 6'h2C;
		8'd72: jd_val = 6'h18; 8'd73: jd_val = 6'h2C; 8'd74: jd_val = 6'h18; 8'd75: jd_val = 6'h31; 8'd76: jd_val = 6'h18; 8'd77: jd_val = 6'h31; 8'd78: jd_val = 6'h22; 8'd79: jd_val = 6'h31;
		8'd80: jd_val = 6'h22; 8'd81: jd_val = 6'h04; 8'd82: jd_val = 6'h22; 8'd83: jd_val = 6'h04; 8'd84: jd_val = 6'h08; 8'd85: jd_val = 6'h04; 8'd86: jd_val = 6'h08; 8'd87: jd_val = 6'h10;
		8'd88: jd_val = 6'h08; 8'd89: jd_val = 6'h10; 8'd90: jd_val = 6'h20; 8'd91: jd_val = 6'h10; 8'd92: jd_val = 6'h20; 8'd93: jd_val = 6'h00; 8'd94: jd_val = 6'h20; 8'd95: jd_val = 6'h00;
		8'd96: jd_val = 6'h00; 8'd97: jd_val = 6'h00; 8'd98: jd_val = 6'h00; 8'd99: jd_val = 6'h01; 8'd100: jd_val = 6'h00; 8'd101: jd_val = 6'h01; 8'd102: jd_val = 6'h02; 8'd103: jd_val = 6'h01;
		8'd104: jd_val = 6'h02; 8'd105: jd_val = 6'h05; 8'd106: jd_val = 6'h02; 8'd107: jd_val = 6'h05; 8'd108: jd_val = 6'h0B; 8'd109: jd_val = 6'h05; 8'd110: jd_val = 6'h0B; 8'd111: jd_val = 6'h16;
		8'd112: jd_val = 6'h0B; 8'd113: jd_val = 6'h16; 8'd114: jd_val = 6'h2C; 8'd115: jd_val = 6'h16; 8'd116: jd_val = 6'h2C; 8'd117: jd_val = 6'h18; 8'd118: jd_val = 6'h2C; 8'd119: jd_val = 6'h18;
		8'd120: jd_val = 6'h31; 8'd121: jd_val = 6'h18; 8'd122: jd_val = 6'h31; 8'd123: jd_val = 6'h22; 8'd124: jd_val = 6'h31; 8'd125: jd_val = 6'h22; 8'd126: jd_val = 6'h04; 8'd127: jd_val = 6'h22;
		8'd128: jd_val = 6'h04; 8'd129: jd_val = 6'h08; 8'd130: jd_val = 6'h04; 8'd131: jd_val = 6'h08; 8'd132: jd_val = 6'h10; 8'd133: jd_val = 6'h08; 8'd134: jd_val = 6'h10; 8'd135: jd_val = 6'h20;
		8'd136: jd_val = 6'h10; 8'd137: jd_val = 6'h20; 8'd138: jd_val = 6'h00; 8'd139: jd_val = 6'h00; 8'd140: jd_val = 6'h3A; 8'd141: jd_val = 6'h1D; 8'd142: jd_val = 6'h2E; 8'd143: jd_val = 6'h37;
		8'd144: jd_val = 6'h00; 8'd145: jd_val = 6'h00; 8'd146: jd_val = 6'h2C; 8'd147: jd_val = 6'h1C; 8'd148: jd_val = 6'h39; 8'd149: jd_val = 6'h33; 8'd150: jd_val = 6'h00; 8'd151: jd_val = 6'h00;
		8'd152: jd_val = 6'h00; 8'd153: jd_val = 6'h00; 8'd154: jd_val = 6'h00; 8'd155: jd_val = 6'h00;
		default: jd_val = 6'h00;
	endcase
endfunction

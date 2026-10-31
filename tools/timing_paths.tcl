# --------------------------------------------------------------------------
#
# timing_paths.tcl - list the worst setup paths of the last compilation
#
# Run automatically after every compilation by post_flow.tcl (the project's
# post-flow script, set in Arcade-Midway-T-Unit.qsf). By hand, from the project
# folder and without recompiling:
#   quartus_sta -t tools/timing_paths.tcl
# (quartus_sta is in the Quartus bin64 folder, e.g.
#  C:\intelFPGA_lite\17.0\quartus\bin64\quartus_sta.exe)
#
# Writes output_files/Arcade-Midway-T-Unit.paths.txt: a one-line summary of the
# 100 worst setup paths of every clock, then the full detail of the 10 worst,
# then (from Build 48) up to 600 worst paths of the core clock in summary form.
# The compilation's own .sta.rpt also shows the worst path of each clock now
# (TIMEQUEST_DO_REPORT_TIMING in Arcade-Midway-T-Unit.qsf).
#
# --------------------------------------------------------------------------

set project  "Arcade-Midway-T-Unit"
set out_file "output_files/$project.paths.txt"

project_open $project -revision $project
create_timing_netlist
read_sdc
update_timing_netlist

file delete -force $out_file
foreach_in_collection clk [all_clocks] {
	set name [get_clock_info -name $clk]
	report_timing -setup -to_clock $name -npaths 100 -detail summary -file $out_file -append
}
report_timing -setup -npaths 10 -detail full_path -file $out_file -append

# The 100 worst paths of a clock can be 100 paths into a handful of registers
# (Build 47: 29 endpoints, over half of the TNS), so the end of the file has up to
# 600 paths of the core clock, in summary form, as MiSTer-CoreSkill's sta_all_fail.tcl:
# if the list ends in positive slack, every failing path is in it.
set core_clk {emu|pll|pll_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk}
set fh [open $out_file a]
puts $fh "\n===== Core clock (clk_sys): up to 600 worst setup paths ====="
close $fh
report_timing -setup -to_clock $core_clk -npaths 600 -detail summary -file $out_file -append

delete_timing_netlist
project_close
puts "timing_paths.tcl: wrote $out_file"

# ----------------------------------------------------------------------------
#
# timing_paths.tcl - list the worst setup paths of a finished compilation
#
#   quartus_sta -t tools/timing_paths.tcl [npaths]
#
# Run from the project folder after a full compilation (no recompile). Opens
# the Arcade-Midway-T-Unit revision, reads the SDC and writes the worst
# setup paths (100 by default) of every clock, slowest corner, to
# output_files/timing_paths.txt, with each path's slack, source and
# destination, so a failing path can be found without opening the GUI.
#
# Copyright (C) 2026 Gm0rk - GPL-3.0-or-later
#
# ----------------------------------------------------------------------------

set revision "Arcade-Midway-T-Unit"
set npaths   100
if {[llength $quartus(args)] > 0} {
	set npaths [lindex $quartus(args) 0]
}
set out "output_files/timing_paths.txt"

project_open $revision -revision $revision
create_timing_netlist -model slow
read_sdc
update_timing_netlist

file delete -force $out
foreach_in_collection clk [get_clocks] {
	set name [get_clock_info -name $clk]
	report_timing -setup -npaths $npaths -to_clock $name -detail summary \
		-panel_name "Worst setup paths to $name" -file $out -append
}
report_clock_fmax_summary -file $out -append

delete_timing_netlist
project_close
puts "timing_paths.tcl: wrote $out"

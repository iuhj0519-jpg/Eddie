# Read-only DCP diagnostics. No RTL generation, placement or routing.
set checkpoint [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
file mkdir $out
open_checkpoint $checkpoint
report_utilization -file "$out/utilization.rpt"
report_utilization -hierarchical -file "$out/utilization_hierarchical.rpt"
report_ram_utilization -file "$out/ram_utilization.rpt"
report_route_status -file "$out/route_status.rpt"
report_timing_summary -delay_type min_max -max_paths 20 -file "$out/timing_summary.rpt"
report_timing -delay_type max -max_paths 20 -file "$out/critical_paths.rpt"
report_high_fanout_nets -timing -max_nets 50 -file "$out/high_fanout_nets.rpt"
report_drc -file "$out/drc.rpt"
report_power -file "$out/power.rpt"
exit

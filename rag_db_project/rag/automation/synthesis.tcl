# Run only from the isolated target workspace. Preserve memory relative paths.
set out [file normalize [lindex $argv 0]]
file mkdir $out
set_param general.maxThreads 4
read_verilog -sv [glob rtl/*.sv]
set_property include_dirs [list [file normalize rtl]] [current_fileset]
synth_design -top zyNet -part xc7z020clg400-1
create_clock -name s_axi_aclk -period 10.000 [get_ports s_axi_aclk]
report_utilization -file "$out/utilization.rpt"
report_utilization -hierarchical -file "$out/utilization_hierarchical.rpt"
report_ram_utilization -file "$out/ram_utilization.rpt"
report_timing_summary -delay_type min_max -max_paths 20 -file "$out/timing_summary.rpt"
report_timing -delay_type max -max_paths 20 -file "$out/critical_paths.rpt"
report_high_fanout_nets -timing -max_nets 50 -file "$out/high_fanout_nets.rpt"
report_drc -file "$out/drc.rpt"
report_power -file "$out/power.rpt"
write_checkpoint "$out/post_synthesis.dcp"
exit

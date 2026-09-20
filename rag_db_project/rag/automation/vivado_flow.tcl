# Local, isolated Vivado flow. No bitstream, board programming or RTL edits.
proc reports {out} {
    report_utilization -file "$out/utilization.rpt"
    report_utilization -hierarchical -file "$out/utilization_hierarchical.rpt"
    report_ram_utilization -file "$out/ram_utilization.rpt"
    report_timing_summary -delay_type min_max -max_paths 20 -file "$out/timing_summary.rpt"
    report_timing -delay_type max -max_paths 20 -file "$out/critical_paths.rpt"
    report_high_fanout_nets -timing -max_nets 50 -file "$out/high_fanout_nets.rpt"
    report_drc -file "$out/drc.rpt"
}
proc main {stage out} {
    set work [pwd]
    set flow "$work/.vivado_flow"
    file mkdir $flow $out
    set project "$flow/project/accelerator.xpr"
    set_param general.maxThreads 4
    if {$stage eq "compile"} {
        if {[file exists $project]} { error "Fresh isolated project required" }
        create_project accelerator "$flow/project" -part xc7z020clg400-1
        add_files -norecurse [glob "$work/rtl/*.sv"]
        set headers [glob -nocomplain "$work/rtl/*.svh"]
        if {[llength $headers]} { add_files -norecurse $headers }
        add_files -fileset sim_1 -norecurse "$work/tb/top_sim.sv"
        set_property top zyNet [get_filesets sources_1]
        set_property top top_sim [get_filesets sim_1]
        set_property include_dirs [list "$work/rtl"] [get_filesets sources_1]
        set_property include_dirs [list "$work/rtl"] [get_filesets sim_1]
        set_property used_in_synthesis false [get_files *top_sim.sv]
        set_property target_simulator XSim [current_project]
        set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
        update_compile_order -fileset sources_1
        update_compile_order -fileset sim_1
        launch_simulation -step compile
        close_project
    } elseif {$stage eq "simulation"} {
        open_project $project
        launch_simulation -noclean_dir
        restart
        set observed [get_objects -r /top_sim/device_under_test/*]
        if {![llength $observed]} { error "DUT scope missing" }
        open_saif "$flow/activity.saif"
        log_saif $observed
        run all
        close_saif
        close_sim
        close_project
        file copy -force "$flow/activity.saif" "$out/activity.saif"
    } elseif {$stage eq "synthesis"} {
        create_project -in_memory -part xc7z020clg400-1
        set_property include_dirs [list "$work/rtl"] [current_fileset]
        read_verilog -sv [glob "$work/rtl/*.sv"]
        # Board/I/O constraints are used only when present in approved source.
        foreach xdc [glob -nocomplain "$work/constraints/*.xdc"] { read_xdc $xdc }
        synth_design -top zyNet -part xc7z020clg400-1
        if {![llength [get_clocks -quiet -of_objects [get_ports s_axi_aclk]]]} {
            create_clock -name s_axi_aclk -period 10.000 [get_ports s_axi_aclk]
        }
        reports $out
        report_power -file "$out/power.rpt"
        write_checkpoint "$flow/post_synthesis.dcp"
        file copy "$flow/post_synthesis.dcp" "$out/post_synthesis.dcp"
    } elseif {$stage eq "implementation"} {
        open_checkpoint "$flow/post_synthesis.dcp"
        opt_design
        place_design
        phys_opt_design
        route_design
        reports $out
        report_route_status -file "$out/route_status.rpt"
        report_clocks -file "$out/clocks.rpt"
        write_checkpoint "$flow/post_route.dcp"
        file copy "$flow/post_route.dcp" "$out/post_route.dcp"
        # Timing/DRC failures are findings, not hidden by successful route execution.
    } elseif {$stage eq "power"} {
        open_checkpoint "$flow/post_route.dcp"
        reset_switching_activity [get_nets -hierarchical]
        if {[llength [get_ports]]} { reset_switching_activity [get_ports] }
        read_saif -strip_path top_sim/device_under_test -out_file "$out/saif_mapping.rpt" "$flow/activity.saif"
        report_power -name power_saif -file "$out/power_post_route.rpt"
        report_switching_activity -signal_rate -static_probability -file "$out/switching_activity.rpt" [get_nets -hierarchical]
    } else { error "Unsupported stage: $stage" }
}
if {[catch {main [lindex $argv 0] [file normalize [lindex $argv 1]]} problem]} {
    puts stderr "AUTOMATION_STAGE_FAILED: $problem"
    exit 1
}
exit 0

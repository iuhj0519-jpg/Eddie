transcript file reports/modelsim_transcript.log
if {[file exists work]} {vdel -lib work -all}
vlib work
vmap work work
vlog -sv +incdir+rtl rtl/*.sv tb/top_sim.sv
vsim -c -t 1ps work.top_sim
run -all
quit -f

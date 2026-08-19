//This is for the 1:4 demux module.

module one_to_four_demux_dataflow_module (a, s0, s1, out1, out2, out3, out4);
	input a;
	input s0, s1;	
	output out1, out2, out3, out4;

	//Fill this out
    assign out1 = (a && !s1 && !s0);
    assign out2 = (a && !s1 && s0);
    assign out3 = (a && s1 && !s0);
    assign out4 = (a && s1 && s0);
    
endmodule

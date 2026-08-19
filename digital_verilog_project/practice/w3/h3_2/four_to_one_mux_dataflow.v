//This is for the 4:1 mux module.

module four_to_one_mux_dataflow_module (a, b, c, d, s0, s1, out);
	input a, b, c, d;
	input s0, s1;	
	output out;
	
	//Fill this out
    assign out = (!s1 && !s0 && a) || (!s1 && s0 && b) || (s1 && !s0 && c) || (s1 && s0 && d);
endmodule
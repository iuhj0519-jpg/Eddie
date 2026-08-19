module xnor_dataflow_gate (a, b, out); 
	
	input a, b;

	output out;

	//Fill this out
    assign out = (a && b) || (!a && !b);

endmodule
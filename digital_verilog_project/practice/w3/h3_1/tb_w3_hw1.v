module tb_w3_hw1;
	reg A, B;

	//This is for the example of nor gate implementations.
	wire OUT_NOR_D, OUT_NOR_G, OUT_NOR_B;
	
	//Use the following wires for your homework.
	//Each one is for the output ports for your modules 
	//with dataflow modeling, gate-level modeling, 
	//and behavioral modeling, respectively.
	wire OUT_XNOR_D, OUT_XNOR_G, OUT_XNOR_B;
	
	//This is the example of nor gate implementations.
	//Refer to this part while implementing yours.
	nor_dataflow_gate nor_dataflow_module(.a(A), .b(B), .out(OUT_NOR_D));
	nor_behavioral_gate nor_behavioral_module(.a(A), .b(B), .out(OUT_NOR_B));
	nor_gatelevel_gate nor_gatelevel_module(.a(A), .b(B), .out(OUT_NOR_G));
		
	//Fill this out (Instantiation of your modules)
	xnor_dataflow_gate xnor_dataflow_module(.a(A), .b(B), .out(OUT_XNOR_D));
	xnor_behavioral_gate xnor_behavioral_module(.a(A), .b(B), .out(OUT_XNOR_B));
	xnor_gatelevel_gate xnor_gatelevel_module(.a(A), .b(B), .out(OUT_XNOR_G));

	//Test pattern
	initial 
	begin
		 A = 0; B = 0;		 
	     #10 A = 0; B = 0;
		 #10 A = 0; B = 1;
		 #10 A = 1; B = 0;
		 #10 A = 1; B = 1;
	end
	
	
endmodule
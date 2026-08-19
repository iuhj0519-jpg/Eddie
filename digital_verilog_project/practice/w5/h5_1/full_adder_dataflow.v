
//This is for the 1-bit full adder module.

module full_adder_dataflow_module (a, b, cin, sum, cout);
	input a, b, cin;
	output sum, cout;
	
	//sum
	//Fill this out
    assign sum = (a ^ b ^ cin);

	//cout
	//Fill this out
	assign cout = (a && b) || ((a ^ b) && cin);
	
endmodule
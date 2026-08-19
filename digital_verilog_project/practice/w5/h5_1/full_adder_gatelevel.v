//This is for the 1-bit full adder module.

module full_adder_gatelevel_module (a, b, cin, sum, cout);
	input a, b, cin;
	output sum, cout;

	wire xor_out_1;
	wire xnor_out_1, xnor_out_2;
	wire not_out_1;

	wire and_out_1, and_out_2, and_out_3;
	wire or_out_1;

	//sum
	//Fill this out
	xnor_gatelevel_gate xnor_1 (.a(a), .b(b), .out(xnor_out_1));
	not_gate not_1 (.a(xnor_out_1), .out(not_out_1));
	xnor_gatelevel_gate xnor_2 (.a(not_out_1), .b(cin), .out(xnor_out_2));
	not_gate not_2 (.a(xnor_out_2), .out(sum));

	//cout
	//Fill this out
    and_gate and_1 (.a(a), .b(b), .out(and_1_out));
    and_gate and_2 (.a(a), .b(cin), .out(and_2_out));
    and_gate and_3 (.a(b), .b(cin), .out(and_3_out));
    or_gate or_1 (.a(and_1_out), .b(and_2_out), .out(or_1_out));
    or_gate or_2 (.a(and_3_out), .b(or_1_out), .out(cout));
    
endmodule
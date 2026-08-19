`timescale 1ns/1ns

module tb_w5_hw1;
	reg A, B;

	//input for full adders
	reg IN_FA_CIN;
 
	//output for half adders
	wire OUT_HA_D_SUM, OUT_HA_D_CARRY; //dataflow modeling
	wire OUT_HA_B_SUM, OUT_HA_B_CARRY; //behavioral modeling
	wire OUT_HA_G_SUM, OUT_HA_G_CARRY; //gate-level modeling

	//wires for full adders
	wire OUT_FA_B_SUM, OUT_FA_B_COUT; //behavioral modeling
	wire OUT_FA_D_SUM, OUT_FA_D_COUT; //dataflow modeling
	wire OUT_FA_G_SUM, OUT_FA_G_COUT; //gate-level modeling

	//input for four bit full adder
	reg [3:0] A_4BIT, B_4BIT;
	reg ZERO;
	
	//output for four bit full adder
	wire [3:0] OUT_FA_SUM;
	wire OUT_FA_COUT;
	
	integer count;
	
	
	half_adder_dataflow_module half_adder_dataflow(.a(A), .b(B), .sum(OUT_HA_D_SUM), .carry(OUT_HA_D_CARRY));
	half_adder_behavioral_module half_adder_behavioral(.a(A), .b(B), .sum(OUT_HA_B_SUM), .carry(OUT_HA_B_CARRY));
	half_adder_gatelevel_module half_adder_gatelevel(.a(A), .b(B), .sum(OUT_HA_G_SUM), .carry(OUT_HA_G_CARRY));

	full_adder_behavioral_module full_adder_behavioral(.a(A), .b(B), .cin(IN_FA_CIN), .sum(OUT_FA_B_SUM), .cout(OUT_FA_B_COUT));
	full_adder_dataflow_module full_adder_dataflow(.a(A), .b(B), .cin(IN_FA_CIN), .sum(OUT_FA_D_SUM), .cout(OUT_FA_D_COUT));
	full_adder_gatelevel_module full_adder_gatelevel(.a(A), .b(B), .cin(IN_FA_CIN), .sum(OUT_FA_G_SUM), .cout(OUT_FA_G_COUT));

	four_bit_full_adder_module four_bit_full_adder (.a(A_4BIT), .b(B_4BIT), .cin(ZERO), .sum(OUT_FA_SUM), .cout(OUT_FA_COUT));

	initial
	begin
		//Fill this out
		 for (count = 0; count <8; count = count +1)
			#10 {A,B,IN_FA_CIN} <= count;
		 
		 ZERO = 0;
		 for (count = 0; count <256; count = count +1)
			#10 {A_4BIT, B_4BIT} <= count;
	end

endmodule
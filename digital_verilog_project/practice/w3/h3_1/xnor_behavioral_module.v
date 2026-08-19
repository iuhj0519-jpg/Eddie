module xnor_behavioral_gate (a, b, out); 
	
	input a, b;

	output out;
	reg out;
	
	always @ (a or b)
	begin

		//Fill this out
    if (a ==1'b0 && b == 1'b0)
        out <= 1'b1;
    else if (a == 1'b1 && b == 1'b1)
        out <= 1'b1;
    else
        out <= 1'b0;
	end

endmodule
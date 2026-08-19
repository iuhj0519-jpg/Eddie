module binary_to_BCD_converter_structural_module (
    input [3:0] four_bit_binary,
    output [9:0] BCD_code
);
    wire [10:0] t;

    assign BCD_code[0] = four_bit_binary[0];
    
    // Fill this out
    submodule_dataflow_module mod_1(.in({0,0,0,four_bit_binary[3]}), .out({t[3],t[2],t[1],t[0]}));
    submodule_dataflow_module mod_2(.in({0,0,0,t[3]}), .out({BCD_code[9],t[10],t[9],t[8]}));
    submodule_dataflow_module mod_3(.in({t[2],t[1],t[0],four_bit_binary[2]}), .out({t[7],t[6],t[5],t[4]}));
    submodule_dataflow_module mod_4(.in({t[10],t[9],t[8],t[7]}), .out({BCD_code[8],BCD_code[7],BCD_code[6],BCD_code[5]}));
    submodule_dataflow_module mod_5(.in({t[6],t[5],t[4],four_bit_binary[1]}), .out({BCD_code[4],BCD_code[3],BCD_code[2],BCD_code[1]}));

endmodule
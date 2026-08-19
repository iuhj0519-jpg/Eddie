`timescale 1ns/1ns

module tb_w5_hw2 ();

    // Input and output of modules to test
    reg [3:0] IN;
    wire [3:0] OUT_B, OUT_D;
    
    reg IN3, IN2, IN1, IN0;
    wire OUT3, OUT2, OUT1, OUT0;

    reg [3:0] FOUR_BIT_BINARY;
    wire [9:0] BCD_CODE_B, BCD_CODE_S;

    // Modules instantiation to test
    submodule_behavioral_module submodule_b(.in(IN), .out(OUT_B));
    submodule_dataflow_module submodule_d(.in(IN), .out(OUT_D));
    submodule_gatelevel_module submodule_g(.in3(IN3), .in2(IN2), .in1(IN1), .in0(IN0), .out3(OUT3), .out2(OUT2), .out1(OUT1), .out0(OUT0));
    
    binary_to_BCD_converter_behavioral_module converter_b(.four_bit_binary(FOUR_BIT_BINARY), .BCD_code(BCD_CODE_B));
    binary_to_BCD_converter_structural_module converter_s(.four_bit_binary(FOUR_BIT_BINARY), .BCD_code(BCD_CODE_S));

    // Test pattern
    integer cnt;
    
    initial begin
        // Signal initialization
        IN = 4'b0000;
        IN3 = 1'b0; IN2 = 1'b0; IN1 = 1'b0; IN0 = 1'b0;
        FOUR_BIT_BINARY = 4'b0000;

        // Submodule behavioral/dataflow
        for (cnt = 0; cnt<16 ; cnt = cnt+1) begin
            #10 IN <= cnt;
        end

        // Submodule gatelevel
        // Fill this out
        for (cnt = 0; cnt<16 ; cnt = cnt+1) begin
            #10 {IN3,IN2,IN1,IN0} = cnt;
        end

        // Binary-to-BCD converter
        // Fill this out
        for (cnt = 0; cnt<16 ; cnt = cnt+1) begin
            #10 FOUR_BIT_BINARY <= cnt;
        end
    end
endmodule
`timescale 1ns/1ps
`include "systolic_parameters.svh"

module processing_element (
    input  wire                              clock,
    input  wire                              reset,
    input  wire                              clear_accumulator,
    input  wire signed [`DATA_WIDTH-1:0]      input_data,
    input  wire                              input_valid,
    input  wire signed [`DATA_WIDTH-1:0]      weight_data,
    input  wire                              weight_valid,
    output reg  signed [`DATA_WIDTH-1:0]      forwarded_input,
    output reg                               forwarded_input_valid,
    output reg  signed [`DATA_WIDTH-1:0]      forwarded_weight,
    output reg                               forwarded_weight_valid,
    output reg  signed [`ACCUMULATOR_WIDTH-1:0] partial_sum
);
    wire signed [15:0] product = input_data * weight_data;

    always @(posedge clock) begin
        if (reset || clear_accumulator) begin
            forwarded_input        <= 8'sd0;
            forwarded_input_valid  <= 1'b0;
            forwarded_weight       <= 8'sd0;
            forwarded_weight_valid <= 1'b0;
            partial_sum            <= 26'sd0;
        end else begin
            forwarded_input        <= input_data;
            forwarded_input_valid  <= input_valid;
            forwarded_weight       <= weight_data;
            forwarded_weight_valid <= weight_valid;
            if (input_valid && weight_valid)
                partial_sum <= partial_sum + {{10{product[15]}}, product};
        end
    end
endmodule

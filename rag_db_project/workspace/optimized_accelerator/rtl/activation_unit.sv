`timescale 1ns/1ps
`include "systolic_parameters.svh"

module activation_unit (
    input  wire                              clock,
    input  wire                              reset,
    input  wire                              start,
    input  wire signed [5*`ACCUMULATOR_WIDTH-1:0] accumulator_data,
    input  wire signed [7:0]                 bias_data,
    output reg  [39:0]                       activation_data,
    output reg                               activation_valid
);
    localparam signed [25:0] POSITIVE_Q5_5_LIMIT_RAW = 26'sd32704;
    localparam signed [25:0] NEGATIVE_Q5_5_LIMIT_RAW = -26'sd32768;
    reg [7:0] sigmoid_memory [0:1023];
    integer lane_index;
    reg signed [25:0] biased_accumulator;
    reg signed [9:0] saturated_q5_5;

    initial $readmemb("memory/sigContent.mif", sigmoid_memory);

    always @(posedge clock) begin
        if (reset) begin
            activation_valid <= 1'b0;
            activation_data  <= 40'd0;
        end else begin
            activation_valid <= start;
            if (start) begin
                for (lane_index = 0; lane_index < 5; lane_index = lane_index + 1) begin
                    biased_accumulator = $signed(accumulator_data[lane_index*26 +: 26])
                                       + ($signed({{18{bias_data[7]}}, bias_data}) <<< 8);
                    if (biased_accumulator > POSITIVE_Q5_5_LIMIT_RAW)
                        saturated_q5_5 = 10'sd511;
                    else if (biased_accumulator < NEGATIVE_Q5_5_LIMIT_RAW)
                        saturated_q5_5 = -10'sd512;
                    else
                        saturated_q5_5 = biased_accumulator >>> 6;
                    activation_data[lane_index*8 +: 8] <= sigmoid_memory[saturated_q5_5 + 10'd512];
                end
            end
        end
    end
endmodule

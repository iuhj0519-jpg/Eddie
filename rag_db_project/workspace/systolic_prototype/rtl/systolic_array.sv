`timescale 1ns/1ps
`include "systolic_parameters.svh"

module systolic_array (
    input  wire                       clock,
    input  wire                       reset,
    input  wire                       clear_accumulators,
    input  wire signed [39:0]         row_input_data,
    input  wire [4:0]                 row_input_valid,
    input  wire signed [39:0]         column_weight_data,
    input  wire [4:0]                 column_weight_valid,
    output wire signed [649:0]        partial_sums
);
    wire signed [7:0] input_path [0:4][0:5];
    wire              input_valid_path [0:4][0:5];
    wire signed [7:0] weight_path [0:5][0:4];
    wire              weight_valid_path [0:5][0:4];

    genvar row_index;
    genvar column_index;
    generate
        for (row_index = 0; row_index < 5; row_index = row_index + 1) begin : ROW_INPUTS
            assign input_path[row_index][0] = row_input_data[row_index*8 +: 8];
            assign input_valid_path[row_index][0] = row_input_valid[row_index];
        end
        for (column_index = 0; column_index < 5; column_index = column_index + 1) begin : COLUMN_INPUTS
            assign weight_path[0][column_index] = column_weight_data[column_index*8 +: 8];
            assign weight_valid_path[0][column_index] = column_weight_valid[column_index];
        end
        for (row_index = 0; row_index < 5; row_index = row_index + 1) begin : ARRAY_ROWS
            for (column_index = 0; column_index < 5; column_index = column_index + 1) begin : ARRAY_COLUMNS
                processing_element processing_element_instance (
                    .clock(clock),
                    .reset(reset),
                    .clear_accumulator(clear_accumulators),
                    .input_data(input_path[row_index][column_index]),
                    .input_valid(input_valid_path[row_index][column_index]),
                    .weight_data(weight_path[row_index][column_index]),
                    .weight_valid(weight_valid_path[row_index][column_index]),
                    .forwarded_input(input_path[row_index][column_index+1]),
                    .forwarded_input_valid(input_valid_path[row_index][column_index+1]),
                    .forwarded_weight(weight_path[row_index+1][column_index]),
                    .forwarded_weight_valid(weight_valid_path[row_index+1][column_index]),
                    .partial_sum(partial_sums[(row_index*5+column_index)*26 +: 26])
                );
            end
        end
    endgenerate
endmodule

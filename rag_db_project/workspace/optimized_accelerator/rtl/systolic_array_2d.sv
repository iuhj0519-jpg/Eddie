`timescale 1ns/1ps

module systolic_array_2d #(
    parameter integer DATA_W = 8,
    parameter integer ACC_W  = 26,
    parameter integer ROWS   = 5,
    parameter integer COLS   = 5
) (
    input  wire                                clk,
    input  wire                                rst_n,
    input  wire                                clr,
    input  wire                                en,
    input  wire signed [(ROWS*DATA_W)-1:0]     a_in_row,
    input  wire [ROWS-1:0]                     a_in_valid,
    input  wire signed [(COLS*DATA_W)-1:0]     b_in_col,
    input  wire [COLS-1:0]                     b_in_valid,
    output wire signed [(ROWS*COLS*ACC_W)-1:0] pe_acc_sum
);
    wire signed [DATA_W-1:0] a_connection [0:ROWS-1][0:COLS];
    wire                     a_valid_connection [0:ROWS-1][0:COLS];
    wire signed [DATA_W-1:0] b_connection [0:ROWS][0:COLS-1];
    wire                     b_valid_connection [0:ROWS][0:COLS-1];

    genvar row_index;
    genvar column_index;
    generate
        for (row_index = 0; row_index < ROWS; row_index = row_index + 1) begin : ROW_INPUT_BIND
            assign a_connection[row_index][0] = a_in_row[row_index*DATA_W +: DATA_W];
            assign a_valid_connection[row_index][0] = a_in_valid[row_index];
        end
        for (column_index = 0; column_index < COLS; column_index = column_index + 1) begin : COLUMN_INPUT_BIND
            assign b_connection[0][column_index] = b_in_col[column_index*DATA_W +: DATA_W];
            assign b_valid_connection[0][column_index] = b_in_valid[column_index];
        end
        for (row_index = 0; row_index < ROWS; row_index = row_index + 1) begin : ARRAY_ROWS
            for (column_index = 0; column_index < COLS; column_index = column_index + 1) begin : ARRAY_COLUMNS
                wire signed [ACC_W-1:0] unused_product;
                pe_systolic_cell #(
                    .DATA_W(DATA_W),
                    .ACC_W(ACC_W)
                ) pe_systolic_cell_instance (
                    .clk(clk),
                    .rst_n(rst_n),
                    .clr(clr),
                    .en(en),
                    .a_in(a_connection[row_index][column_index]),
                    .a_in_valid(a_valid_connection[row_index][column_index]),
                    .b_in(b_connection[row_index][column_index]),
                    .b_in_valid(b_valid_connection[row_index][column_index]),
                    .a_out(a_connection[row_index][column_index+1]),
                    .a_out_valid(a_valid_connection[row_index][column_index+1]),
                    .b_out(b_connection[row_index+1][column_index]),
                    .b_out_valid(b_valid_connection[row_index+1][column_index]),
                    .mul(unused_product),
                    .acc_sum(pe_acc_sum[((row_index*COLS)+column_index)*ACC_W +: ACC_W])
                );
            end
        end
    endgenerate
endmodule

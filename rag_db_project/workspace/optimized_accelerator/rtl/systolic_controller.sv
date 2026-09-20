`timescale 1ns/1ps
`include "systolic_parameters.svh"

module systolic_controller #(
    parameter integer DATA_W = `DATA_WIDTH,
    parameter integer ACC_W  = `ACCUMULATOR_WIDTH,
    parameter integer ROWS   = `ARRAY_ROWS,
    parameter integer COLS   = `ARRAY_COLUMNS
) (
    input  wire                                clk,
    input  wire                                rst_n,
    input  wire                                i_start,
    input  wire [9:0]                          reduction_length,
    output wire                                o_done,
    output wire                                o_busy,
    output reg  [(ROWS*10)-1:0]                operand_read_address,
    output reg  [ROWS-1:0]                     operand_read_enable,
    output reg  [(COLS*10)-1:0]                weight_read_address,
    output reg  [COLS-1:0]                     weight_read_enable,
    input  wire signed [(ROWS*DATA_W)-1:0]     operand_read_data,
    input  wire [ROWS-1:0]                     operand_read_valid,
    input  wire signed [(COLS*DATA_W)-1:0]     weight_read_data,
    input  wire [COLS-1:0]                     weight_read_valid,
    output wire signed [(ROWS*COLS*ACC_W)-1:0] o_mat_c,
    output wire [9:0]                          run_cycle
);
    localparam [1:0] IDLE       = 2'd0;
    localparam [1:0] RUN        = 2'd1;
    localparam [1:0] DONE_STATE = 2'd2;
    localparam [9:0] PIPELINE_AND_MEMORY_OVERHEAD = 10'd13;

    reg [1:0] state;
    reg [1:0] next_state;
    reg [9:0] cycle_count;
    reg [9:0] target_cycle_count;
    integer row_index;
    integer column_index;
    integer reduction_index;

    assign o_busy    = (state == RUN);
    assign o_done    = (state == DONE_STATE);
    assign run_cycle = cycle_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state              <= IDLE;
            cycle_count        <= 10'd0;
            target_cycle_count <= 10'd0;
        end else begin
            state <= next_state;
            if (state == RUN)
                cycle_count <= cycle_count + 1'b1;
            else
                cycle_count <= 10'd0;
            if ((state == IDLE) && i_start)
                target_cycle_count <= reduction_length + PIPELINE_AND_MEMORY_OVERHEAD;
        end
    end

    always @(*) begin
        next_state = state;
        case (state)
            IDLE: if (i_start) next_state = RUN;
            RUN: if (cycle_count >= target_cycle_count - 2) next_state = DONE_STATE;
            DONE_STATE: if (!i_start) next_state = IDLE;
            default: next_state = IDLE;
        endcase
    end

    always @(*) begin
        operand_read_address = {(ROWS*10){1'b0}};
        operand_read_enable  = {ROWS{1'b0}};
        weight_read_address  = {(COLS*10){1'b0}};
        weight_read_enable   = {COLS{1'b0}};

        for (row_index = 0; row_index < ROWS; row_index = row_index + 1) begin
            reduction_index = cycle_count - row_index;
            if ((state == RUN) && (cycle_count >= row_index) &&
                (reduction_index < reduction_length)) begin
                operand_read_address[row_index*10 +: 10] = reduction_index[9:0];
                operand_read_enable[row_index] = 1'b1;
            end
        end

        for (column_index = 0; column_index < COLS; column_index = column_index + 1) begin
            reduction_index = cycle_count - column_index;
            if ((state == RUN) && (cycle_count >= column_index) &&
                (reduction_index < reduction_length)) begin
                weight_read_address[column_index*10 +: 10] = reduction_index[9:0];
                weight_read_enable[column_index] = 1'b1;
            end
        end
    end

    systolic_array_2d #(
        .DATA_W(DATA_W),
        .ACC_W(ACC_W),
        .ROWS(ROWS),
        .COLS(COLS)
    ) systolic_array_2d_instance (
        .clk(clk),
        .rst_n(rst_n),
        .clr((state == IDLE) && i_start),
        .en(state == RUN),
        .a_in_row(operand_read_data),
        .a_in_valid(operand_read_valid),
        .b_in_col(weight_read_data),
        .b_in_valid(weight_read_valid),
        .pe_acc_sum(o_mat_c)
    );
endmodule

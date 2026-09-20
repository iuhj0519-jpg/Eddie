`timescale 1ns/1ps

module pe_systolic_cell #(
    parameter integer DATA_W = 8,
    parameter integer ACC_W  = 26
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         clr,
    input  wire                         en,
    input  wire signed [DATA_W-1:0]     a_in,
    input  wire                         a_in_valid,
    input  wire signed [DATA_W-1:0]     b_in,
    input  wire                         b_in_valid,
    output wire signed [DATA_W-1:0]     a_out,
    output wire                         a_out_valid,
    output wire signed [DATA_W-1:0]     b_out,
    output wire                         b_out_valid,
    output wire signed [ACC_W-1:0]      mul,
    output wire signed [ACC_W-1:0]      acc_sum
);
    reg signed [DATA_W-1:0] a_register;
    reg signed [DATA_W-1:0] b_register;
    reg                     a_valid_register;
    reg                     b_valid_register;

    assign a_out       = a_register;
    assign b_out       = b_register;
    assign a_out_valid = a_valid_register;
    assign b_out_valid = b_valid_register;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_register       <= {DATA_W{1'b0}};
            b_register       <= {DATA_W{1'b0}};
            a_valid_register <= 1'b0;
            b_valid_register <= 1'b0;
        end else if (clr) begin
            a_valid_register <= 1'b0;
            b_valid_register <= 1'b0;
        end else if (en) begin
            a_register       <= a_in;
            b_register       <= b_in;
            a_valid_register <= a_in_valid;
            b_valid_register <= b_in_valid;
        end
    end

    mac_pe #(
        .DATA_W(DATA_W),
        .ACC_W(ACC_W)
    ) mac_pe_instance (
        .clk(clk),
        .rst_n(rst_n),
        .clr(clr),
        .en(en && a_valid_register && b_valid_register),
        .a(a_register),
        .b(b_register),
        .mul(mul),
        .acc_sum(acc_sum)
    );
endmodule

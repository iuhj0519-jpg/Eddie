`timescale 1ns/1ps

module mac_pe #(
    parameter integer DATA_W = 8,
    parameter integer ACC_W  = 26
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         clr,
    input  wire                         en,
    input  wire signed [DATA_W-1:0]     a,
    input  wire signed [DATA_W-1:0]     b,
    output wire signed [ACC_W-1:0]      mul,
    output reg  signed [ACC_W-1:0]      acc_sum
);
    wire signed [(2*DATA_W)-1:0] product = $signed(a) * $signed(b);
    assign mul = {{(ACC_W-(2*DATA_W)){product[(2*DATA_W)-1]}}, product};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            acc_sum <= {ACC_W{1'b0}};
        else if (clr)
            acc_sum <= {ACC_W{1'b0}};
        else if (en)
            acc_sum <= acc_sum + mul;
    end
endmodule

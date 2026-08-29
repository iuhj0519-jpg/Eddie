`timescale 1ns/1ps
`include "systolic_parameters.svh"

module global_buffer (
    input  wire               clock,
    input  wire               reset,
    input  wire               read_region,
    input  wire [24:0]        read_address,
    input  wire [4:0]         read_enable,
    output reg  signed [39:0] read_data,
    output reg  [4:0]         read_valid,
    input  wire               write_region,
    input  wire [4:0]         write_address,
    input  wire [39:0]        write_data,
    input  wire               write_enable
);
    localparam integer DEPTH = `GLOBAL_BUFFER_DEPTH;
    reg signed [7:0] region_a_bank_0 [0:DEPTH-1];
    reg signed [7:0] region_a_bank_1 [0:DEPTH-1];
    reg signed [7:0] region_a_bank_2 [0:DEPTH-1];
    reg signed [7:0] region_a_bank_3 [0:DEPTH-1];
    reg signed [7:0] region_a_bank_4 [0:DEPTH-1];
    reg signed [7:0] region_b_bank_0 [0:DEPTH-1];
    reg signed [7:0] region_b_bank_1 [0:DEPTH-1];
    reg signed [7:0] region_b_bank_2 [0:DEPTH-1];
    reg signed [7:0] region_b_bank_3 [0:DEPTH-1];
    reg signed [7:0] region_b_bank_4 [0:DEPTH-1];

    always @(posedge clock) begin
        if (reset) begin
            read_valid <= 5'd0;
        end else begin
            read_valid <= read_enable;
            if (!read_region) begin
                if (read_enable[0]) read_data[0 +: 8]  <= region_a_bank_0[read_address[0 +: 5]];
                if (read_enable[1]) read_data[8 +: 8]  <= region_a_bank_1[read_address[5 +: 5]];
                if (read_enable[2]) read_data[16 +: 8] <= region_a_bank_2[read_address[10 +: 5]];
                if (read_enable[3]) read_data[24 +: 8] <= region_a_bank_3[read_address[15 +: 5]];
                if (read_enable[4]) read_data[32 +: 8] <= region_a_bank_4[read_address[20 +: 5]];
            end else begin
                if (read_enable[0]) read_data[0 +: 8]  <= region_b_bank_0[read_address[0 +: 5]];
                if (read_enable[1]) read_data[8 +: 8]  <= region_b_bank_1[read_address[5 +: 5]];
                if (read_enable[2]) read_data[16 +: 8] <= region_b_bank_2[read_address[10 +: 5]];
                if (read_enable[3]) read_data[24 +: 8] <= region_b_bank_3[read_address[15 +: 5]];
                if (read_enable[4]) read_data[32 +: 8] <= region_b_bank_4[read_address[20 +: 5]];
            end

            if (write_enable && !write_region) begin
                region_a_bank_0[write_address] <= write_data[0 +: 8];
                region_a_bank_1[write_address] <= write_data[8 +: 8];
                region_a_bank_2[write_address] <= write_data[16 +: 8];
                region_a_bank_3[write_address] <= write_data[24 +: 8];
                region_a_bank_4[write_address] <= write_data[32 +: 8];
            end else if (write_enable) begin
                region_b_bank_0[write_address] <= write_data[0 +: 8];
                region_b_bank_1[write_address] <= write_data[8 +: 8];
                region_b_bank_2[write_address] <= write_data[16 +: 8];
                region_b_bank_3[write_address] <= write_data[24 +: 8];
                region_b_bank_4[write_address] <= write_data[32 +: 8];
            end
        end
    end
endmodule

`timescale 1ns/1ps
`include "systolic_parameters.svh"

module input_buffer (
    input  wire                         clock,
    input  wire                         reset,
    input  wire                         clear_batch,
    input  wire signed [`DATA_WIDTH-1:0] stream_data,
    input  wire                         stream_valid,
    input  wire [49:0]                  read_address,
    input  wire [4:0]                   read_enable,
    output reg  signed [39:0]           read_data,
    output reg  [4:0]                   read_valid,
    output reg                          batch_loaded
);
    localparam integer FEATURE_COUNT = `INPUT_FEATURE_COUNT;

    reg signed [`DATA_WIDTH-1:0] memory_bank_0 [0:FEATURE_COUNT-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_1 [0:FEATURE_COUNT-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_2 [0:FEATURE_COUNT-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_3 [0:FEATURE_COUNT-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_4 [0:FEATURE_COUNT-1];
    reg [9:0] feature_count;
    reg [2:0] image_count;

    always @(posedge clock) begin
        if (reset || clear_batch) begin
            feature_count <= 10'd0;
            image_count   <= 3'd0;
            batch_loaded  <= 1'b0;
        end else if (stream_valid && !batch_loaded) begin
            case (image_count)
                3'd0: memory_bank_0[feature_count] <= stream_data;
                3'd1: memory_bank_1[feature_count] <= stream_data;
                3'd2: memory_bank_2[feature_count] <= stream_data;
                3'd3: memory_bank_3[feature_count] <= stream_data;
                default: memory_bank_4[feature_count] <= stream_data;
            endcase
            if (feature_count == FEATURE_COUNT-1) begin
                feature_count <= 10'd0;
                if (image_count == 3'd4) begin
                    image_count  <= 3'd0;
                    batch_loaded <= 1'b1;
                end else begin
                    image_count <= image_count + 1'b1;
                end
            end else begin
                feature_count <= feature_count + 1'b1;
            end
        end
    end

    always @(posedge clock) begin
        read_valid <= read_enable;
        if (read_enable[0]) read_data[0 +: 8]  <= memory_bank_0[read_address[0 +: 10]];
        if (read_enable[1]) read_data[8 +: 8]  <= memory_bank_1[read_address[10 +: 10]];
        if (read_enable[2]) read_data[16 +: 8] <= memory_bank_2[read_address[20 +: 10]];
        if (read_enable[3]) read_data[24 +: 8] <= memory_bank_3[read_address[30 +: 10]];
        if (read_enable[4]) read_data[32 +: 8] <= memory_bank_4[read_address[40 +: 10]];
    end
endmodule

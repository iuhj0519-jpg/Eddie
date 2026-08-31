`timescale 1ns/1ps

module maxFinder (
    input  wire        i_clk,
    input  wire        reset,
    input  wire        clear_results,
    input  wire        score_column_valid,
    input  wire [2:0]  group_index,
    input  wire [2:0]  column_index,
    input  wire [39:0] score_column,
    output reg  [19:0] result_classes,
    output reg         results_ready
);
    reg [7:0] maximum_score [0:4];
    integer image_index;

    always @(posedge i_clk) begin
        if (reset || clear_results) begin
            results_ready  <= 1'b0;
            result_classes <= 20'd0;
            for (image_index = 0; image_index < 5; image_index = image_index + 1)
                maximum_score[image_index] <= 8'd0;
        end else if (score_column_valid) begin
            for (image_index = 0; image_index < 5; image_index = image_index + 1) begin
                if ((group_index == 0) && (column_index == 0)) begin
                    maximum_score[image_index] <= score_column[image_index*8 +: 8];
                    result_classes[image_index*4 +: 4] <= 4'd0;
                end else if (score_column[image_index*8 +: 8] > maximum_score[image_index]) begin
                    maximum_score[image_index] <= score_column[image_index*8 +: 8];
                    result_classes[image_index*4 +: 4] <= group_index*5 + column_index;
                end
            end
            if ((group_index == 1) && (column_index == 4))
                results_ready <= 1'b1;
        end
    end
endmodule

`timescale 1ns/1ps

module dnn_scheduler (
    input  wire       clock,
    input  wire       reset,
    input  wire       batch_start,
    input  wire       batch_loaded,
    input  wire       controller_done,
    input  wire       activation_valid,
    input  wire       maxfinder_ready,
    input  wire       results_consumed,
    output reg  [1:0] layer_index,
    output reg  [2:0] group_index,
    output reg  [2:0] activation_column,
    output reg        controller_start,
    output reg        activation_start,
    output reg        global_write_enable,
    output reg        score_column_valid,
    output reg        clear_batch,
    output reg        clear_results,
    output reg        intr,
    output reg  [3:0] scheduler_state
);
    localparam [3:0] IDLE             = 4'd0;
    localparam [3:0] INPUT_LOAD       = 4'd1;
    localparam [3:0] LAYER_SETUP      = 4'd2;
    localparam [3:0] TILE_START       = 4'd3;
    localparam [3:0] TILE_WAIT        = 4'd4;
    localparam [3:0] ACTIVATION_WRITE = 4'd5;
    localparam [3:0] GROUP_CHECK      = 4'd6;
    localparam [3:0] LAYER_CHECK      = 4'd7;
    localparam [3:0] OUTPUT_LOAD      = 4'd8;
    localparam [3:0] MAXFINDER_START  = 4'd9;
    localparam [3:0] MAXFINDER_WAIT   = 4'd10;
    localparam [3:0] RESULT_VALID     = 4'd11;

    reg activation_pending;
    wire unused_batch_start = batch_start;

    function [2:0] last_group;
        input [1:0] selected_layer;
        begin
            case (selected_layer)
                2'd1: last_group = 3'd5;
                2'd2: last_group = 3'd3;
                default: last_group = 3'd1;
            endcase
        end
    endfunction

    always @(posedge clock) begin
        if (reset) begin
            scheduler_state      <= IDLE;
            layer_index          <= 2'd1;
            group_index          <= 3'd0;
            activation_column    <= 3'd0;
            activation_pending   <= 1'b0;
            controller_start     <= 1'b0;
            activation_start     <= 1'b0;
            global_write_enable  <= 1'b0;
            score_column_valid   <= 1'b0;
            clear_batch          <= 1'b0;
            clear_results        <= 1'b0;
            intr                 <= 1'b0;
        end else begin
            controller_start    <= 1'b0;
            activation_start    <= 1'b0;
            global_write_enable <= 1'b0;
            score_column_valid  <= 1'b0;
            clear_batch         <= 1'b0;
            clear_results       <= 1'b0;
            intr                <= 1'b0;

            case (scheduler_state)
                IDLE: begin
                    layer_index <= 2'd1;
                    group_index <= 3'd0;
                    if (batch_loaded)
                        scheduler_state <= INPUT_LOAD;
                end
                INPUT_LOAD: begin
                    if (batch_loaded)
                        scheduler_state <= LAYER_SETUP;
                end
                LAYER_SETUP: begin
                    layer_index     <= 2'd1;
                    group_index     <= 3'd0;
                    scheduler_state <= TILE_START;
                end
                TILE_START: begin
                    controller_start <= 1'b1;
                    scheduler_state  <= TILE_WAIT;
                end
                TILE_WAIT: begin
                    if (controller_done) begin
                        activation_column  <= 3'd0;
                        activation_pending <= 1'b0;
                        scheduler_state    <= ACTIVATION_WRITE;
                    end
                end
                ACTIVATION_WRITE: begin
                    if (!activation_pending) begin
                        activation_start   <= 1'b1;
                        activation_pending <= 1'b1;
                    end
                    if (activation_valid) begin
                        if (layer_index < 3)
                            global_write_enable <= 1'b1;
                        else
                            score_column_valid <= 1'b1;
                        activation_pending <= 1'b0;
                        if (activation_column == 3'd4)
                            scheduler_state <= GROUP_CHECK;
                        else
                            activation_column <= activation_column + 1'b1;
                    end
                end
                GROUP_CHECK: begin
                    if (group_index < last_group(layer_index)) begin
                        group_index     <= group_index + 1'b1;
                        scheduler_state <= TILE_START;
                    end else begin
                        scheduler_state <= LAYER_CHECK;
                    end
                end
                LAYER_CHECK: begin
                    if (layer_index < 3) begin
                        layer_index     <= layer_index + 1'b1;
                        group_index     <= 3'd0;
                        scheduler_state <= TILE_START;
                    end else begin
                        scheduler_state <= OUTPUT_LOAD;
                    end
                end
                OUTPUT_LOAD: scheduler_state <= MAXFINDER_START;
                MAXFINDER_START: scheduler_state <= MAXFINDER_WAIT;
                MAXFINDER_WAIT: begin
                    if (maxfinder_ready) begin
                        intr            <= 1'b1;
                        scheduler_state <= RESULT_VALID;
                    end
                end
                RESULT_VALID: begin
                    if (results_consumed) begin
                        clear_batch     <= 1'b1;
                        clear_results   <= 1'b1;
                        scheduler_state <= IDLE;
                    end
                end
                default: scheduler_state <= IDLE;
            endcase
        end
    end
endmodule

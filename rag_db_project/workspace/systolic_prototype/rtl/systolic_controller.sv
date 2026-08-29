`timescale 1ns/1ps

module systolic_controller (
    input  wire        clock,
    input  wire        reset,
    input  wire        i_start,
    input  wire [9:0]  reduction_length,
    output wire        o_busy,
    output wire        o_done,
    output wire        array_clear,
    output wire [9:0]  run_cycle
);
    localparam [1:0] IDLE       = 2'd0;
    localparam [1:0] RUN        = 2'd1;
    localparam [1:0] DONE_STATE = 2'd2;
    localparam [9:0] PIPELINE_AND_MEMORY_OVERHEAD = 10'd13;

    reg [1:0] state;
    reg [9:0] cycle_count;
    reg [9:0] target_cycle_count;

    assign o_busy = (state == RUN);
    assign o_done = (state == DONE_STATE);
    assign array_clear = (state == IDLE) && i_start;
    assign run_cycle = cycle_count;

    always @(posedge clock) begin
        if (reset) begin
            state              <= IDLE;
            cycle_count        <= 10'd0;
            target_cycle_count <= 10'd0;
        end else begin
            case (state)
                IDLE: begin
                    cycle_count <= 10'd0;
                    if (i_start) begin
                        target_cycle_count <= reduction_length + PIPELINE_AND_MEMORY_OVERHEAD;
                        state <= RUN;
                    end
                end
                RUN: begin
                    if (cycle_count == target_cycle_count - 2'b10)
                        state <= DONE_STATE;
                    else
                        cycle_count <= cycle_count + 1'b1;
                end
                DONE_STATE: state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule

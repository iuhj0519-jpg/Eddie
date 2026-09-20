`timescale 1ns/1ps
`include "systolic_parameters.svh"

module zyNet #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5
) (
    input wire s_axi_aclk, input wire s_axi_aresetn,
    input wire [`DATA_WIDTH-1:0] axis_in_data, input wire axis_in_data_valid,
    output wire axis_in_data_ready,
    input wire [C_S_AXI_ADDR_WIDTH-1:0] s_axi_awaddr, input wire [2:0] s_axi_awprot,
    input wire s_axi_awvalid, output wire s_axi_awready,
    input wire [C_S_AXI_DATA_WIDTH-1:0] s_axi_wdata,
    input wire [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
    input wire s_axi_wvalid, output wire s_axi_wready,
    output wire [1:0] s_axi_bresp, output wire s_axi_bvalid, input wire s_axi_bready,
    input wire [C_S_AXI_ADDR_WIDTH-1:0] s_axi_araddr, input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid, output wire s_axi_arready,
    output wire [C_S_AXI_DATA_WIDTH-1:0] s_axi_rdata,
    output wire [1:0] s_axi_rresp, output wire s_axi_rvalid, input wire s_axi_rready,
    output wire intr
);
    wire reset = !s_axi_aresetn;
    wire batch_start = axis_in_data_valid && axis_in_data_ready;
    wire batch_loaded;
    wire next_batch_loaded;
    wire clear_batch;
    wire clear_results;
    wire results_consumed;
    wire [1:0] layer_index;
    wire [2:0] group_index;
    wire [2:0] activation_column;
    wire controller_start;
    wire controller_busy;
    wire controller_done;
    wire [9:0] run_cycle;
    wire [9:0] reduction_length = (layer_index == 2'd1) ? 10'd784 :
                                  (layer_index == 2'd2) ? 10'd30  : 10'd20;
    wire [49:0] operand_read_address;
    wire [4:0] operand_read_enable;
    wire [49:0] weight_read_address;
    wire [4:0] weight_read_enable;
    wire signed [39:0] operand_read_data;
    wire [4:0] operand_read_valid;
    wire global_write_enable;
    reg [2:0] activation_column_pipeline;
    wire [4:0] activation_write_address = group_index*5 + activation_column_pipeline;
    wire [39:0] activation_data;

    unified_buffer unified_buffer_instance (
        .clock(s_axi_aclk), .reset(reset),
        .stream_data(axis_in_data), .stream_valid(axis_in_data_valid),
        .stream_ready(axis_in_data_ready), .advance_batch(clear_batch),
        .read_input_region(layer_index == 2'd1),
        .read_secondary_region(layer_index == 2'd3),
        .release_input_address((layer_index == 2'd1) && (group_index == 3'd5)),
        .read_address(operand_read_address), .read_enable(operand_read_enable),
        .read_data(operand_read_data), .read_valid(operand_read_valid),
        .activation_write_address(activation_write_address),
        .write_secondary_region(layer_index == 2'd2),
        .activation_write_data(activation_data),
        .activation_write_enable(global_write_enable),
        .current_batch_loaded(batch_loaded), .next_batch_loaded(next_batch_loaded)
    );

    wire signed [39:0] weight_read_data;
    wire [4:0] weight_read_valid;
    weight_sram weight_sram_instance (
        .clock(s_axi_aclk), .layer_index(layer_index), .group_index(group_index),
        .read_address(weight_read_address), .read_enable(weight_read_enable),
        .read_data(weight_read_data), .read_valid(weight_read_valid)
    );

    wire signed [649:0] partial_sums;
    systolic_controller systolic_controller_instance (
        .clk(s_axi_aclk), .rst_n(s_axi_aresetn), .i_start(controller_start),
        .reduction_length(reduction_length), .o_done(controller_done), .o_busy(controller_busy),
        .operand_read_address(operand_read_address), .operand_read_enable(operand_read_enable),
        .weight_read_address(weight_read_address), .weight_read_enable(weight_read_enable),
        .operand_read_data(operand_read_data), .operand_read_valid(operand_read_valid),
        .weight_read_data(weight_read_data), .weight_read_valid(weight_read_valid),
        .o_mat_c(partial_sums), .run_cycle(run_cycle)
    );

    wire signed [39:0] bias_data;
    bias_sram bias_sram_instance (
        .clock(s_axi_aclk), .layer_index(layer_index), .group_index(group_index), .bias_data(bias_data)
    );

    integer lane_index;
    reg signed [129:0] selected_accumulators;
    always @(*) begin
        for (lane_index = 0; lane_index < 5; lane_index = lane_index + 1)
            selected_accumulators[lane_index*26 +: 26] =
                partial_sums[(lane_index*5+activation_column)*26 +: 26];
    end

    wire activation_start;
    wire activation_valid;
    activation_unit activation_unit_instance (
        .clock(s_axi_aclk), .reset(reset), .start(activation_start),
        .accumulator_data(selected_accumulators),
        .bias_data(bias_data[activation_column*8 +: 8]),
        .activation_data(activation_data), .activation_valid(activation_valid)
    );

    always @(posedge s_axi_aclk) begin
        if (reset)
            activation_column_pipeline <= 3'd0;
        else if (activation_start)
            activation_column_pipeline <= activation_column;
    end

    wire score_column_valid;
    wire [19:0] result_classes;
    wire results_ready;
    maxFinder maxFinder_instance (
        .i_clk(s_axi_aclk), .reset(reset), .clear_results(clear_results),
        .score_column_valid(score_column_valid), .group_index(group_index),
        .column_index(activation_column_pipeline), .score_column(activation_data),
        .result_classes(result_classes), .results_ready(results_ready)
    );

    wire [3:0] scheduler_state;
    dnn_scheduler dnn_scheduler_instance (
        .clock(s_axi_aclk), .reset(reset), .batch_start(batch_start), .batch_loaded(batch_loaded),
        .controller_done(controller_done), .activation_valid(activation_valid),
        .maxfinder_ready(results_ready), .results_consumed(results_consumed),
        .layer_index(layer_index), .group_index(group_index), .activation_column(activation_column),
        .controller_start(controller_start), .activation_start(activation_start),
        .global_write_enable(global_write_enable), .score_column_valid(score_column_valid),
        .clear_batch(clear_batch), .clear_results(clear_results), .intr(intr),
        .scheduler_state(scheduler_state)
    );

    axi_lite_wrapper #(
        .C_S_AXI_DATA_WIDTH(C_S_AXI_DATA_WIDTH), .C_S_AXI_ADDR_WIDTH(C_S_AXI_ADDR_WIDTH)
    ) axi_lite_wrapper_instance (
        .S_AXI_ACLK(s_axi_aclk), .S_AXI_ARESETN(s_axi_aresetn),
        .S_AXI_AWADDR(s_axi_awaddr), .S_AXI_AWPROT(s_axi_awprot),
        .S_AXI_AWVALID(s_axi_awvalid), .S_AXI_AWREADY(s_axi_awready),
        .S_AXI_WDATA(s_axi_wdata), .S_AXI_WSTRB(s_axi_wstrb),
        .S_AXI_WVALID(s_axi_wvalid), .S_AXI_WREADY(s_axi_wready),
        .S_AXI_BRESP(s_axi_bresp), .S_AXI_BVALID(s_axi_bvalid), .S_AXI_BREADY(s_axi_bready),
        .S_AXI_ARADDR(s_axi_araddr), .S_AXI_ARPROT(s_axi_arprot),
        .S_AXI_ARVALID(s_axi_arvalid), .S_AXI_ARREADY(s_axi_arready),
        .S_AXI_RDATA(s_axi_rdata), .S_AXI_RRESP(s_axi_rresp),
        .S_AXI_RVALID(s_axi_rvalid), .S_AXI_RREADY(s_axi_rready),
        .result_classes(result_classes), .results_ready(results_ready),
        .results_consumed(results_consumed)
    );
endmodule

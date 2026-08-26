`timescale 1ns / 1ps

module zyNet #(
  parameter int C_S_AXI_DATA_WIDTH = 32,
  parameter int C_S_AXI_ADDR_WIDTH = 5,
  parameter int DATA_W = 8,
  parameter int BATCH_SIZE = 5
)(
  //Clock and Reset
  input  logic s_axi_aclk,
  input  logic s_axi_aresetn,

  //AXI Stream Interface
  input  logic signed [DATA_W-1:0] axis_in_data,
  input  logic axis_in_data_valid,
  output logic axis_in_data_ready,

  //AXI Lite Interface
  input  logic [C_S_AXI_ADDR_WIDTH-1:0] s_axi_awaddr,
  input  logic [2:0] s_axi_awprot,
  input  logic s_axi_awvalid,
  output logic s_axi_awready,
  input  logic [C_S_AXI_DATA_WIDTH-1:0] s_axi_wdata,
  input  logic [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
  input  logic s_axi_wvalid,
  output logic s_axi_wready,
  output logic [1:0] s_axi_bresp,
  output logic s_axi_bvalid,
  input  logic s_axi_bready,
  input  logic [C_S_AXI_ADDR_WIDTH-1:0] s_axi_araddr,
  input  logic [2:0] s_axi_arprot,
  input  logic s_axi_arvalid,
  output logic s_axi_arready,
  output logic [C_S_AXI_DATA_WIDTH-1:0] s_axi_rdata,
  output logic [1:0] s_axi_rresp,
  output logic s_axi_rvalid,
  input  logic s_axi_rready,

  //Interrupt Interface
  output logic intr
);

  logic [31:0] image_batch_result [0:BATCH_SIZE-1];
  logic image_batch_result_valid;
  logic image_batch_result_ready;
  logic image_batch_complete;
  logic image_batch_start;
  logic softReset;
  logic npu_rst_n;

  // 기존의 axi_lite_wrapper interface에서 사용된 포트
  // SRAM 기반의 architecture에서는 사용하지 않음
  /*
  logic [31:0] unused_layer_number;
  logic [31:0] unused_neuron_number;
  logic unused_weight_valid;
  logic unused_bias_valid;
  logic [31:0] unused_weight_value;
  logic [31:0] unused_bias_value;
  logic unused_axi_read_enable;
  */

  assign npu_rst_n = s_axi_aresetn && !softReset;
  assign intr = image_batch_result_valid;

  axi_lite_wrapper #(
    .C_S_AXI_DATA_WIDTH(C_S_AXI_DATA_WIDTH),
    .C_S_AXI_ADDR_WIDTH(C_S_AXI_ADDR_WIDTH),
    .BATCH_SIZE(BATCH_SIZE)
  ) u_axi_lite_wrapper (
    .S_AXI_ACLK(s_axi_aclk),
    .S_AXI_ARESETN(s_axi_aresetn),
    .S_AXI_AWADDR(s_axi_awaddr),
    .S_AXI_AWPROT(s_axi_awprot),
    .S_AXI_AWVALID(s_axi_awvalid),
    .S_AXI_AWREADY(s_axi_awready),
    .S_AXI_WDATA(s_axi_wdata),
    .S_AXI_WSTRB(s_axi_wstrb),
    .S_AXI_WVALID(s_axi_wvalid),
    .S_AXI_WREADY(s_axi_wready),
    .S_AXI_BRESP(s_axi_bresp),
    .S_AXI_BVALID(s_axi_bvalid),
    .S_AXI_BREADY(s_axi_bready),
    .S_AXI_ARADDR(s_axi_araddr),
    .S_AXI_ARPROT(s_axi_arprot),
    .S_AXI_ARVALID(s_axi_arvalid),
    .S_AXI_ARREADY(s_axi_arready),
    .S_AXI_RDATA(s_axi_rdata),
    .S_AXI_RRESP(s_axi_rresp),
    .S_AXI_RVALID(s_axi_rvalid),
    .S_AXI_RREADY(s_axi_rready),

    /*
    .layerNumber(unused_layer_number),
    .neuronNumber(unused_neuron_number),
    .weightValid(unused_weight_valid),
    .biasValid(unused_bias_valid),
    .weightValue(unused_weight_value),
    .biasValue(unused_bias_value),
    */
    .nnOut(image_batch_result),
    .nnOut_valid(image_batch_result_valid),
    .image_batch_start(image_batch_start),
    .image_batch_result_ready(image_batch_result_ready),
    /* 
    .axi_rd_en(unused_axi_read_enable),
    .axi_rd_data(32'd0),
    */
    .softReset(softReset)
  );

  NPU_Top #(
    .DATA_W(DATA_W),
    .BATCH_SIZE(BATCH_SIZE)
  ) u_npu_top (
    .clk(s_axi_aclk),
    .rst_n(npu_rst_n),
    .input_data(axis_in_data),
    .input_data_valid(axis_in_data_valid),
    .input_data_ready(axis_in_data_ready),
    .image_batch_start(image_batch_start),
    .image_batch_result(image_batch_result),
    .image_batch_result_valid(image_batch_result_valid),
    .image_batch_result_ready(image_batch_result_ready),
    .image_batch_complete(image_batch_complete)
  );
endmodule

`timescale 1ns/1ps

module axi_lite_result_interface #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5
) (
    input  wire                              clock,
    input  wire                              reset_n,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    input  wire [2:0]                        s_axi_awprot,
    input  wire                              s_axi_awvalid,
    output wire                              s_axi_awready,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
    input  wire                              s_axi_wvalid,
    output wire                              s_axi_wready,
    output wire [1:0]                        s_axi_bresp,
    output reg                               s_axi_bvalid,
    input  wire                              s_axi_bready,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    input  wire [2:0]                        s_axi_arprot,
    input  wire                              s_axi_arvalid,
    output wire                              s_axi_arready,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    output wire [1:0]                        s_axi_rresp,
    output reg                               s_axi_rvalid,
    input  wire                              s_axi_rready,
    input  wire [19:0]                       result_classes,
    input  wire                              results_ready,
    output reg                               results_consumed
);
    localparam [C_S_AXI_ADDR_WIDTH-1:0] RESULT_ADDRESS = 5'h08;
    localparam [C_S_AXI_ADDR_WIDTH-1:0] STATUS_ADDRESS = 5'h18;
    reg [C_S_AXI_ADDR_WIDTH-1:0] latched_read_address;
    reg [2:0] result_read_index;

    assign s_axi_awready = !s_axi_bvalid && s_axi_awvalid && s_axi_wvalid;
    assign s_axi_wready  = s_axi_awready;
    assign s_axi_bresp   = 2'b00;
    assign s_axi_arready = !s_axi_rvalid;
    assign s_axi_rresp   = 2'b00;

    always @(posedge clock) begin
        if (!reset_n) begin
            s_axi_bvalid       <= 1'b0;
            s_axi_rvalid       <= 1'b0;
            s_axi_rdata        <= 32'd0;
            latched_read_address <= 5'd0;
            result_read_index  <= 3'd0;
            results_consumed   <= 1'b0;
        end else begin
            results_consumed <= 1'b0;
            if (s_axi_awready)
                s_axi_bvalid <= 1'b1;
            else if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (s_axi_arvalid && s_axi_arready) begin
                latched_read_address <= s_axi_araddr;
                s_axi_rvalid <= 1'b1;
                case (s_axi_araddr)
                    RESULT_ADDRESS: s_axi_rdata <= {{28{1'b0}}, result_classes[result_read_index*4 +: 4]};
                    STATUS_ADDRESS: s_axi_rdata <= {{31{1'b0}}, results_ready};
                    default: s_axi_rdata <= 32'd0;
                endcase
            end else if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
                if (latched_read_address == RESULT_ADDRESS) begin
                    if (result_read_index == 3'd4) begin
                        result_read_index <= 3'd0;
                        results_consumed  <= 1'b1;
                    end else begin
                        result_read_index <= result_read_index + 1'b1;
                    end
                end
            end
        end
    end
endmodule

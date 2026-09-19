`timescale 1ns/1ps

module axi_lite_wrapper #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5
) (
    input  wire                              S_AXI_ACLK,
    input  wire                              S_AXI_ARESETN,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     S_AXI_AWADDR,
    input  wire [2:0]                        S_AXI_AWPROT,
    input  wire                              S_AXI_AWVALID,
    output wire                              S_AXI_AWREADY,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]     S_AXI_WDATA,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] S_AXI_WSTRB,
    input  wire                              S_AXI_WVALID,
    output wire                              S_AXI_WREADY,
    output wire [1:0]                        S_AXI_BRESP,
    output reg                               S_AXI_BVALID,
    input  wire                              S_AXI_BREADY,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     S_AXI_ARADDR,
    input  wire [2:0]                        S_AXI_ARPROT,
    input  wire                              S_AXI_ARVALID,
    output wire                              S_AXI_ARREADY,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]     S_AXI_RDATA,
    output wire [1:0]                        S_AXI_RRESP,
    output reg                               S_AXI_RVALID,
    input  wire                              S_AXI_RREADY,
    input  wire [19:0]                       result_classes,
    input  wire                              results_ready,
    output reg                               results_consumed
);
    localparam [C_S_AXI_ADDR_WIDTH-1:0] RESULT_ADDRESS = 5'h08;
    localparam [C_S_AXI_ADDR_WIDTH-1:0] STATUS_ADDRESS = 5'h18;
    reg [C_S_AXI_ADDR_WIDTH-1:0] accepted_read_address;
    reg [2:0] result_read_index;

    assign S_AXI_AWREADY = !S_AXI_BVALID && S_AXI_AWVALID && S_AXI_WVALID;
    assign S_AXI_WREADY  = S_AXI_AWREADY;
    assign S_AXI_BRESP   = 2'b00;
    assign S_AXI_ARREADY = !S_AXI_RVALID;
    assign S_AXI_RRESP   = 2'b00;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_BVALID        <= 1'b0;
            S_AXI_RVALID        <= 1'b0;
            S_AXI_RDATA         <= {C_S_AXI_DATA_WIDTH{1'b0}};
            accepted_read_address <= {C_S_AXI_ADDR_WIDTH{1'b0}};
            result_read_index   <= 3'd0;
            results_consumed    <= 1'b0;
        end else begin
            results_consumed <= 1'b0;

            if (S_AXI_AWREADY)
                S_AXI_BVALID <= 1'b1;
            else if (S_AXI_BVALID && S_AXI_BREADY)
                S_AXI_BVALID <= 1'b0;

            if (S_AXI_ARVALID && S_AXI_ARREADY) begin
                accepted_read_address <= S_AXI_ARADDR;
                S_AXI_RVALID <= 1'b1;
                case (S_AXI_ARADDR)
                    RESULT_ADDRESS: S_AXI_RDATA <= {{(C_S_AXI_DATA_WIDTH-4){1'b0}},
                                                     result_classes[result_read_index*4 +: 4]};
                    STATUS_ADDRESS: S_AXI_RDATA <= {{(C_S_AXI_DATA_WIDTH-1){1'b0}}, results_ready};
                    default: S_AXI_RDATA <= {C_S_AXI_DATA_WIDTH{1'b0}};
                endcase
            end else if (S_AXI_RVALID && S_AXI_RREADY) begin
                S_AXI_RVALID <= 1'b0;
                if (accepted_read_address == RESULT_ADDRESS) begin
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

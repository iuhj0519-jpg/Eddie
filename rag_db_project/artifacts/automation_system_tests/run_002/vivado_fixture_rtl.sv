module zyNet(input s_axi_aclk, input s_axi_aresetn, input [7:0] data_in, output reg [7:0] data_out);
always @(posedge s_axi_aclk) if (!s_axi_aresetn) data_out <= 0; else data_out <= data_in + 1;
endmodule

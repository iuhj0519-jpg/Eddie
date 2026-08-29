module mac_pe #(
  parameter int DATA_W = 8,
  parameter int ACC_W  = 2*DATA_W
)(
  input  logic                  clk,
  input  logic                  rst_n,

  input  logic                  clr,      // ?? ???
  input  logic                  en,       // ?? enable

  input  logic [DATA_W-1:0]     a,        // operand 1
  input  logic [DATA_W-1:0]     b,        // operand 2

  output logic [ACC_W-1:0]      mul,      // a*b ??
  output logic [ACC_W-1:0]      acc_sum   // ?? ??
);

  // ???: ?? ??
  always_comb begin
    mul = a * b;
  end

  // ???: acc_sum <= acc_sum + mul
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      acc_sum <= '0;
    end
    else begin
      if (clr) begin
        acc_sum <= '0;
      end
      else if (en) begin
        acc_sum <= acc_sum + mul;
      end
      // en=0?? acc_sum ??
    end
  end

endmodule

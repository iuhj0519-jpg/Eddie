module mac_pe #(
  parameter int DATA_W = 8,
  parameter int ACC_W  = 2*DATA_W
)(
  input  logic                  clk,
  input  logic                  rst_n,

  input  logic                  clr,      // 누산 초기화
  input  logic                  en,       // 연산 enable

  input  logic signed [DATA_W-1:0] a,     // signed operand 1
  input  logic signed [DATA_W-1:0] b,     // signed operand 2

  output logic signed [ACC_W-1:0] mul,     // signed a*b
  output logic signed [ACC_W-1:0] acc_sum // accumulated result
);

  // 곱셈기 : 조합 논리
  always_comb begin
    mul = $signed(a) * $signed(b);
  end

  // 누산기: acc_sum <= acc_sum + mul
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
      // en=0이면 acc_sum 유지
    end
  end

endmodule

module pe_systolic_cell #(
  parameter int DATA_W = 8,
  parameter int ACC_W  = 2*DATA_W
)(
  input  logic                 clk,
  input  logic                 rst_n,
  input  logic                 clr,
  input  logic                 en,

  input  logic signed [DATA_W-1:0] a_in,
  input  logic signed [DATA_W-1:0] b_in,
  output logic signed [DATA_W-1:0] a_out,
  output logic signed [DATA_W-1:0] b_out,

  output logic signed [ACC_W-1:0] mul,
  output logic signed [ACC_W-1:0] acc_sum
);

  // a, b? ? ? ????? ?? ?/??? ??
  logic signed [DATA_W-1:0] a_reg, b_reg;

  assign a_out = a_reg;
  assign b_out = b_reg;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      a_reg <= '0;
      b_reg <= '0;
    //end else if (clr) begin
    //clr? ???(mac_pe)? ??? ????? ????, ??? ??(a_reg, b_reg)? ???? ?? ?? ???? ??
    end else if (en) begin //debugging point
      a_reg <= a_in;
      b_reg <= b_in;
    end
    // en=0 ?? ? ?? (Stall)
  end

  // ?? MAC ??: a_reg * b_reg ??
  mac_pe #(
    .DATA_W (DATA_W),
    .ACC_W  (ACC_W)
  ) u_mac_pe (
    .clk     (clk),
    .rst_n   (rst_n),
    .clr     (clr),
    .en      (en),
    .a       (a_reg),
    .b       (b_reg),
    .mul     (mul),
    .acc_sum (acc_sum)
  );

endmodule

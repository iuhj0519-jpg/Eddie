//============================================================
// 2??: 1D PE Chain
// - ?? ?? ???(in_data)? NUM_PE?? mac_pe? ??
// - ? PE? ?? weight? ??? MAC ?? ??
//============================================================
module pe_chain_1d #(
  parameter int DATA_W = 8,
  parameter int ACC_W  = 2*DATA_W,
  parameter int NUM_PE = 4
)(
  input                       clk,
  input                       rst_n,

  input                       clr,       // ?? ?? ???
  input                       en,        // ?? ?? enable

  input   [DATA_W-1:0]        in_data,
  output  [DATA_W-1:0]        out_data,

  // ? PE? weight ?? (TB?? ??)
  input   [DATA_W-1:0]        weight [0:NUM_PE-1],

  // Watchpoint? ?? (mul/acc_sum ???)
  output  [ACC_W-1:0]         pe_mul     [0:NUM_PE-1],
  output  [ACC_W-1:0]         pe_acc_sum [0:NUM_PE-1]
);

  // ??? ?????: data_pipe[0]? in_data, ???? out_data
  reg [DATA_W-1:0] data_pipe [0:NUM_PE-1];

  assign out_data     = data_pipe[NUM_PE-1];

  // ??? ????? ????
  generate
  for (genvar i = 0; i < NUM_PE; i++) begin
    if (i==0) begin
      always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
          data_pipe[i] <= 0;
        end else begin
          data_pipe[0] <= in_data;
        end
      end
    end else begin
      always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
          data_pipe[i] <= 0;
        end else begin
          data_pipe[i] <= data_pipe[i-1];
        end
      end      
    end
  end
  endgenerate

  // ? stage? mac_pe ????
  generate
  for (genvar i = 0; i < NUM_PE; i++) begin
    mac_pe #(
      .DATA_W (DATA_W),
      .ACC_W  (ACC_W)
    ) u_mac_pe (
      .clk     (clk),
      .rst_n   (rst_n),
      .clr     (clr),
      .en      (en),
      .a       (data_pipe[i]),
      .b       (weight[i]),
      .mul     (pe_mul[i]),
      .acc_sum (pe_acc_sum[i])
    );
  end
  endgenerate

endmodule

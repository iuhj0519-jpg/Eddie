//============================================================
// 3??: 2D Systolic PE Array
// - 2x2 ?? ?? (ROWS, COLS ????? ?? ??)
//============================================================
module systolic_array_2d #(
  parameter int DATA_W = 8,
  parameter int ACC_W  = 2*DATA_W,
  parameter int ROWS   = 2,
  parameter int COLS   = 2
)(
  input  logic                      clk,
  input  logic                      rst_n,

  input  logic                      clr,
  input  logic                      en,

  // ???? ???? A ?? ??? (? ??? ?? ??)
  input  logic [DATA_W-1:0]         a_in_row [0:ROWS-1],
  // ???? ???? B ?? ??? (? ??? ?? ??)
  input  logic [DATA_W-1:0]         b_in_col [0:COLS-1],

  // Watchpoint? ?? (? PE? mul / acc_sum)
  output logic [ACC_W-1:0]          pe_mul    [0:ROWS-1][0:COLS-1],
  output logic [ACC_W-1:0]          pe_acc_sum[0:ROWS-1][0:COLS-1]
);

  // ?? a/b ?? ??
  logic [DATA_W-1:0] a_sig [0:ROWS-1][0:COLS-1];
  logic [DATA_W-1:0] b_sig [0:ROWS-1][0:COLS-1];

//  genvar r, c;
//  generate
//    for (r = 0; r < ROWS; r++) begin : G_ROW
//      for (c = 0; c < COLS; c++) begin : G_COL
//
//        logic [DATA_W-1:0] a_in_cell;
//        logic [DATA_W-1:0] b_in_cell;
//
//        // ???? ???? a
//        assign a_in_cell = (c == 0) ? a_in_row[r] : a_sig[r][c-1];
//        //r0c0 assign a_in_cell = a_in_row[0]
//        //r0c1 assign a_in_cell = a_sig[0][0]
//        //r1c0 assign a_in_cell = a_in_row[1]
//        //r1c1 assign a_in_cell = a_sig[1][0];
//
//        // ???? ???? b
//        assign b_in_cell = (r == 0) ? b_in_col[c] : b_sig[r-1][c];
//
//        pe_systolic_cell #(
//          .DATA_W (DATA_W),
//          .ACC_W  (ACC_W)
//        ) u_cell (
//          .clk     (clk),
//          .rst_n   (rst_n),
//          .clr     (clr),
//          .en      (en),
//
//          .a_in    (a_in_cell),
//          .b_in    (b_in_cell),
//          .a_out   (a_sig[r][c]),
//          .b_out   (b_sig[r][c]),
//
//          .mul     (pe_mul[r][c]),
//          .acc_sum (pe_acc_sum[r][c])
//        );
//
//      end
//    end
//  endgenerate

// [?? ??? 1] ?? ???? (?? + 1)?? ??
  // a_conn[r][c] : r? c? "?"? ?? ??? (??)
  // a_conn[r][c+1] : r? c? "?"? ?? ??? (??)
  logic [DATA_W-1:0] a_conn [0:ROWS-1][0:COLS];   // ?? ??: 0 ~ COLS
  logic [DATA_W-1:0] b_conn [0:ROWS][0:COLS-1];   // ?? ??: 0 ~ ROWS

genvar r, c;

  // [?? ??? 2] ?? ??? 0? ??? ???? ??
  generate
    for (r = 0; r < ROWS; r++) begin : A_INPUT_BIND
      assign a_conn[r][0] = a_in_row[r];
    end

    for (c = 0; c < COLS; c++) begin : B_INPUT_BIND
      assign b_conn[0][c] = b_in_col[c];
    end
  endgenerate

// [?? ??? 3] ??? ??? ?? ???? (??? ??)
  generate
    for (r = 0; r < ROWS; r++) begin : G_ROW
      for (c = 0; c < COLS; c++) begin : G_COL
        
        pe_systolic_cell #(
          .DATA_W (DATA_W),
          .ACC_W  (ACC_W)
        ) u_cell (
          .clk     (clk),
          .rst_n   (rst_n),
          .clr     (clr),
          .en      (en),

          // ?? ??(c)?? ??? -> ?? ??(c+1)? ??
          .a_in    (a_conn[r][c]),
          .a_out   (a_conn[r][c+1]),

          // ?? ??(r)?? ??? -> ?? ??(r+1)? ??
          .b_in    (b_conn[r][c]),
          .b_out   (b_conn[r+1][c]),

          .mul     (pe_mul[r][c]),
          .acc_sum (pe_acc_sum[r][c])
        );

      end
    end
  endgenerate

endmodule

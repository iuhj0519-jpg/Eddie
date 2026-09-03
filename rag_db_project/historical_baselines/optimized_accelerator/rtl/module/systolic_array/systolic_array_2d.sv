//============================================================
// 3단계: 2D Systolic PE Array
// - 2x2 타일 예제 (ROWS, COLS 파라미터로 확장 가능)
//============================================================
module systolic_array_2d #(
  parameter int DATA_W = 8,
  parameter int ACC_W  = 2*DATA_W,
  parameter int ROWS   = 5,
  parameter int COLS   = 5
)(
  input  logic                      clk,
  input  logic                      rst_n,

  input  logic                      clr,
  input  logic                      en,

  // 왼쪽에서 들어오는 A 행렬 스트림 (각 행마다 입력 하나)
  input  logic signed [DATA_W-1:0]  a_in_row [0:ROWS-1],
  // 위쪽에서 들어오는 B 행렬 스트림 (각 열마다 입력 하나)
  input  logic signed [DATA_W-1:0]  b_in_col [0:COLS-1],

  // Watchpoint용 출력 (각 PE의 mul / acc_sum)
  output logic signed [ACC_W-1:0]   pe_mul    [0:ROWS-1][0:COLS-1],
  output logic signed [ACC_W-1:0]   pe_acc_sum[0:ROWS-1][0:COLS-1]
);

  // 내부 a/b 전달 신호
  /*
  logic signed [DATA_W-1:0] a_sig [0:ROWS-1][0:COLS-1];
  logic signed [DATA_W-1:0] b_sig [0:ROWS-1][0:COLS-1];
  */

//  genvar r, c;
//  generate
//    for (r = 0; r < ROWS; r++) begin : G_ROW
//      for (c = 0; c < COLS; c++) begin : G_COL
//
//        logic [DATA_W-1:0] a_in_cell;
//        logic [DATA_W-1:0] b_in_cell;
//
//        // 왼쪽에서 들어오는 a
//        assign a_in_cell = (c == 0) ? a_in_row[r] : a_sig[r][c-1];
//        //r0c0 assign a_in_cell = a_in_row[0]
//        //r0c1 assign a_in_cell = a_sig[0][0]
//        //r1c0 assign a_in_cell = a_in_row[1]
//        //r1c1 assign a_in_cell = a_sig[1][0];
//
//        // 위쪽에서 들어오는 b
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

// [개선 포인트 1] 연결 와이어를 (개수 + 1)만큼 선언
  // a_conn[r][c] : r행 c열 "앞"에 있는 와이어 (입력)
  // a_conn[r][c+1] : r행 c열 "뒤"에 있는 와이어 (출력)
  logic signed [DATA_W-1:0] a_conn [0:ROWS-1][0:COLS];
  logic signed [DATA_W-1:0] b_conn [0:ROWS][0:COLS-1];

genvar r, c;

  // [개선 포인트 2] 외부 입력을 0번 인덱스 와이어에 연결
  generate
    for (r = 0; r < ROWS; r++) begin : A_INPUT_BIND
      assign a_conn[r][0] = a_in_row[r];
    end

    for (c = 0; c < COLS; c++) begin : B_INPUT_BIND
      assign b_conn[0][c] = b_in_col[c];
    end
  endgenerate

// [개선 포인트 3] 반복문 내부가 아주 단순해짐 (조건문 삭제)
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

          // 현재 위치(c)에서 받아서 -> 다음 위치(c+1)로 전달
          .a_in    (a_conn[r][c]),
          .a_out   (a_conn[r][c+1]),

          // 현재 위치(r)에서 받아서 -> 다음 위치(r+1)로 전달
          .b_in    (b_conn[r][c]),
          .b_out   (b_conn[r+1][c]),

          .mul     (pe_mul[r][c]),
          .acc_sum (pe_acc_sum[r][c])
        );

      end
    end
  endgenerate

endmodule

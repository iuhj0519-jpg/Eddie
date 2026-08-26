module systolic_controller #(
  parameter int DATA_W = 8,
  // parameter int K_DIM  = 5,
  parameter int ROWS   = 5,
  parameter int COLS   = 5,
  parameter int COUNTER_WIDTH = 10,
  parameter int SRAM_READ_LATENCY = 1,
  
  parameter int ACC_W  = 2 * DATA_W + $clog2(784)
)(
  input  logic                      clk,
  input  logic                      rst_n,

  // --- Control Interface ---
  input  logic                      i_start,
  output logic                      o_done,
  output logic                      o_busy,

  // 새롭게 추가된 신호들
  input  logic [COUNTER_WIDTH-1:0]  current_common_dimension_length,
  output logic                      input_feature_read_enable [0:ROWS-1],
  output logic [COUNTER_WIDTH-1:0]  input_feature_read_address[0:ROWS-1],
  input  logic signed [DATA_W-1:0]  input_feature_read_data   [0:ROWS-1],
  input  logic                      input_feature_read_valid  [0:ROWS-1],
  output logic                      weight_sram_read_enable   [0:COLS-1],
  output logic [COUNTER_WIDTH-1:0]  weight_sram_read_address  [0:COLS-1],
  input  logic signed [DATA_W-1:0]  weight_sram_read_data     [0:COLS-1],
  input  logic                      weight_sram_read_valid    [0:COLS-1],

 
  /*
  input  logic signed [DATA_W-1:0]  i_mat_a [0:ROWS-1][0:K_DIM-1],
  input  logic signed [DATA_W-1:0]  i_mat_b [0:K_DIM-1][0:COLS-1],
  */
  output logic signed [ACC_W-1:0]   o_mat_c [0:ROWS-1][0:COLS-1]
);

  //==========================================================
  // 1. 내부 상태 및 버퍼 정의
  //==========================================================
  typedef enum logic [1:0] {
    IDLE,
    RUN,
    DONE_STATE
  } state_t;

  state_t state, next_state;
  logic [COUNTER_WIDTH-1:0] cnt;

  // Input Buffer(SRAM)가 역할을 대신하기 때문에 주석 처리
  /*
  logic signed [DATA_W-1:0] latched_mat_a [0:ROWS-1][0:K_DIM-1];
  logic signed [DATA_W-1:0] latched_mat_b [0:K_DIM-1][0:COLS-1];
  */

  // Array Interface: 실제 Systolic Array로 들어가는 신호
  logic signed [DATA_W-1:0] array_a_in [0:ROWS-1];
  logic signed [DATA_W-1:0] array_b_in [0:COLS-1];
  logic              array_en;
  logic              array_clr; 

  // 연산 완료까지 걸리는 시간
  // 데이터 주입 완료(ROWS + K_DIM) + 파이프라인 통과(COLS) + 여유

  // localparam int CALC_CYCLES = ROWS + COLS + K_DIM + 2;
  logic [COUNTER_WIDTH-1:0] CALC_CYCLES;

  always_comb begin
    CALC_CYCLES = current_common_dimension_length
                + ROWS + COLS + SRAM_READ_LATENCY + 2;
  end

  //==========================================================
  // 2. FSM & Counter
  //==========================================================
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state <= IDLE;
      cnt   <= 0;
    end else begin
      state <= next_state;
      if (state == RUN) cnt <= cnt + 1;
      else              cnt <= 0;
    end
  end

  always_comb begin
    next_state = state;
    case (state)
      IDLE: begin
        if (i_start) next_state = RUN;
      end
      RUN: begin
        if (cnt >= CALC_CYCLES) next_state = DONE_STATE;
      end
      DONE_STATE: begin
        if (!i_start) next_state = IDLE;
      end
    endcase
  end

  // Output Assignments
  assign o_busy   = (state == RUN);
  assign o_done   = (state == DONE_STATE);
  
  // Array Control Signals
  assign array_en = (state == RUN);
  
  // IDLE 상태에서 start가 들어오는 순산 Clear 수행 (Accumulator 초기화)
  // 이렇게 하면 PE 내부의 acc_sum이 0으로 리셋되고 새 연산을 시작합니다.
  assign array_clr = (state == IDLE) && i_start;

  //==========================================================
  // 3. Legacy Static Matrix Input Latching
  //==========================================================
  /*
  always_ff @(posedge clk) begin
    if (state == IDLE && i_start) begin
      latched_mat_a <= i_mat_a;
      latched_mat_b <= i_mat_b;
    end
  end
  */

  //==========================================================
  // 4. Legacy Static Matrix Skewing Logic
  //==========================================================
  /*
  genvar r, c;
  generate
    // Row Input Control (Matrix A -> Row Input)
    for (r = 0; r < ROWS; r++) begin : GEN_SKEW_A
      always_comb begin
        array_a_in[r] = '0; // Default 0 padding
        if (state == RUN) begin
          // Timing Logic: time(cnt) - row_index(r) = col_index(k)
          int k;
          k = cnt - r;
          if (k >= 0 && k < K_DIM) begin
            array_a_in[r] = latched_mat_a[r][k];
          end
        end
      end
    end

    // Column Input Control (Matrix B -> Col Input)
    for (c = 0; c < COLS; c++) begin : GEN_SKEW_B
      always_comb begin
        array_b_in[c] = '0; // Default 0 padding
        if (state == RUN) begin
          // Timing Logic: time(cnt) - col_index(c) = row_index(k)
          int k;
          k = cnt - c;
          if (k >= 0 && k < K_DIM) begin
            array_b_in[c] = latched_mat_b[k][c];
          end
        end
      end
    end
  endgenerate
  */

  //==========================================================
  // 4. SRAM/Buffer Read and Array Feed(=Skewing)
  //==========================================================
  genvar r, c;
  generate
    for (r = 0; r < ROWS; r++) begin : GEN_MEMORY_A
      always_comb begin
        input_feature_read_enable[r]  = 1'b0;
        input_feature_read_address[r] = '0;
        array_a_in[r]                  = '0;

        if (state == RUN) begin
          if ((cnt >= r) && ((cnt - r) < current_common_dimension_length)) begin
            input_feature_read_enable[r]  = 1'b1;
            input_feature_read_address[r] = cnt - r;
          end
          if (input_feature_read_valid[r]) begin
            array_a_in[r] = input_feature_read_data[r];
          end
        end
      end
    end

    for (c = 0; c < COLS; c++) begin : GEN_MEMORY_B
      always_comb begin
        weight_sram_read_enable[c]  = 1'b0;
        weight_sram_read_address[c] = '0;
        array_b_in[c]                = '0;

        if (state == RUN) begin
          if ((cnt >= c) && ((cnt - c) < current_common_dimension_length)) begin
            weight_sram_read_enable[c]  = 1'b1;
            weight_sram_read_address[c] = cnt - c;
          end
          if (weight_sram_read_valid[c]) begin
            array_b_in[c] = weight_sram_read_data[c];
          end
        end
      end
    end
  endgenerate

  //==========================================================
  // 5. Systolic Array Instantiation
  //==========================================================
  systolic_array_2d #(
    .DATA_W (DATA_W),
    .ACC_W  (ACC_W),
    .ROWS   (ROWS),
    .COLS   (COLS)
  ) u_core_array (
    .clk        (clk),
    .rst_n      (rst_n),
    .clr        (array_clr),
    .en         (array_en),
    .a_in_row   (array_a_in),
    .b_in_col   (array_b_in),
    .pe_mul     (),        // Unused monitor port
    .pe_acc_sum (o_mat_c)  // Final Result
  );

endmodule

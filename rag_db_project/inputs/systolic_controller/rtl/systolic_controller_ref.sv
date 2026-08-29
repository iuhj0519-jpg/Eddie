module systolic_controller #(
  parameter int DATA_W = 4,
  parameter int K_DIM  = 2, //Common dimension
  parameter int ROWS   = 2,
  parameter int COLS   = 2,
  // ?? ????
  parameter int ACC_W  = 2*DATA_W + $clog2(K_DIM)
)(
  input  logic                      clk,
  input  logic                      rst_n,

  // --- Control Interface ---
  input  logic                      i_start,
  output logic                      o_done,
  output logic                      o_busy,

  // --- Data Interface ---
  input  logic [DATA_W-1:0]         i_mat_a [0:ROWS-1][0:K_DIM-1],
  input  logic [DATA_W-1:0]         i_mat_b [0:K_DIM-1][0:COLS-1],
  output logic [ACC_W-1:0]          o_mat_c [0:ROWS-1][0:COLS-1]
);

  //==========================================================
  // 1. ?? ?? ? ?? ??
  //==========================================================
  typedef enum logic [1:0] {
    IDLE,
    RUN,
    DONE_STATE
  } state_t;

  state_t state, next_state;
  logic [7:0] cnt; 

  // Input Buffer: ?? ???? ??(Latch)??? ??
  logic [DATA_W-1:0] latched_mat_a [0:ROWS-1][0:K_DIM-1];
  logic [DATA_W-1:0] latched_mat_b [0:K_DIM-1][0:COLS-1];

  // Array Interface: ?? Systolic Array? ???? ??
  logic [DATA_W-1:0] array_a_in [0:ROWS-1];
  logic [DATA_W-1:0] array_b_in [0:COLS-1];
  logic              array_en;
  logic              array_clr; 

  // ?? ???? ??? ?? ??
  // ??? ?? ??(ROWS + K_DIM) + ????? ??(COLS) + ??
  localparam int CALC_CYCLES = ROWS + COLS + K_DIM + 2;

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
  
  // IDLE ???? start? ???? ?? Clear ?? (Accumulator ???)
  // ??? ?? PE ??? acc_sum? 0?? ???? ? ??? ?????.
  assign array_clr = (state == IDLE) && i_start;

  //==========================================================
  // 3. Input Buffer Latching
  //==========================================================
  // ?? ?? ???? ???? ?? ??? ??? ??? ??
  always_ff @(posedge clk) begin
    if (state == IDLE && i_start) begin
      latched_mat_a <= i_mat_a;
      latched_mat_b <= i_mat_b;
    end
  end

  //==========================================================
  // 4. Data Skewing Logic
  //==========================================================
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

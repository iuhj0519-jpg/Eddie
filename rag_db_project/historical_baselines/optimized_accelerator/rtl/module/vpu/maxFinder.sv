module maxFinder #(
  parameter int numInput   = 10,
  parameter int inputWidth = 16
)(
  input  logic                  i_clk,
  input  logic                  i_clear,
  input  logic [inputWidth-1:0] i_score,
  input  logic                  i_score_valid,
  output logic [31:0]           o_data,
  output logic                  o_data_valid
);
  localparam int CLASS_INDEX_WIDTH = (numInput <= 1) ? 1 : $clog2(numInput);

  logic [inputWidth-1:0] maxValue;
  logic [CLASS_INDEX_WIDTH-1:0] class_index;
  logic search_active;

  /* 
  수정한 부분 : 
  class가 항상 0부터 9까지 순서대로 들어오기 때문에 
  외부 score index와 packed input register를 제거하고 
  내부 class_index로 입력 순서를 추적
  */
  always_ff @(posedge i_clk) begin
    if (i_clear) begin
      maxValue      <= '0;
      class_index   <= '0;
      search_active <= 1'b0;
      o_data        <= '0;
      o_data_valid  <= 1'b0;
    end else if (i_score_valid && !o_data_valid) begin
      if (!search_active) begin
        // 첫 입력은 class 0의 score (score 0)
        maxValue      <= i_score;
        o_data        <= 32'd0;
        search_active <= 1'b1;
        if (numInput == 1) begin
          o_data_valid <= 1'b1;
        end else begin
          class_index <= {{(CLASS_INDEX_WIDTH-1){1'b0}}, 1'b1};
        end
      end else begin
        if (i_score > maxValue) begin
          maxValue <= i_score;
          o_data   <= {{(32-CLASS_INDEX_WIDTH){1'b0}}, class_index};
        end

        if (class_index == numInput-1) begin
          search_active <= 1'b0;
          o_data_valid  <= 1'b1;
        end else begin
          class_index <= class_index + 1'b1;
        end
      end
    end
  end
endmodule

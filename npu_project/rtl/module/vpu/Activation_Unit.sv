module Activation_Unit #(
  parameter int DATA_W = 8,
  parameter int ACC_W = 2 * DATA_W + $clog2(784),
  parameter int SIGMOID_ADDRESS_WIDTH = 10
)(
  input  logic clk,
  input  logic rst_n,
  input  logic activation_input_valid,
  input  logic signed [ACC_W-1:0] activation_partial_sum_input,
  input  logic signed [DATA_W-1:0] activation_bias_input,
  output logic signed [DATA_W-1:0] activation_output_data,
  output logic activation_output_valid
);
  logic signed [ACC_W-1:0] bias_addition_result;
  logic signed [ACC_W-1:0] scaled_bias;
  // saturated_activation_input을 아래에서 16-bit 정의하는 것으로 수정
  logic [SIGMOID_ADDRESS_WIDTH-1:0] sigmoid_rom_address;
  logic [DATA_W-1:0] sigmoid_rom_data;

  // 추가 : MAC 누산 폭과 기존 Sig_ROM 입력 형식을 분리
  localparam int ACTIVATION_INPUT_WIDTH = 2 * DATA_W; // ACC_W가 확장되어도 Sig_ROM에는 기존 16비트 형식을 사용

  // 추가 : partial-sum과 bias의 합을 안전하게 계산하기 위한 확장 신호
  logic signed [ACTIVATION_INPUT_WIDTH-1:0] saturated_activation_input;

  // 추가 : 기존 16-bit Activation 입력의 signed 최대/최소값
  localparam logic signed [ACTIVATION_INPUT_WIDTH-1:0] ACTIVATION_MAX =
      {1'b0, {(ACTIVATION_INPUT_WIDTH-1){1'b1}}};
  localparam logic signed [ACTIVATION_INPUT_WIDTH-1:0] ACTIVATION_MIN =
      {1'b1, {(ACTIVATION_INPUT_WIDTH-1){1'b0}}};

  // The reference neuron stores an 8-bit bias with DATA_W fractional bits.
  // Therefore it is sign-extended and shifted left before addition.
  always_comb begin
    scaled_bias = $signed({{(ACC_W-DATA_W){activation_bias_input[DATA_W-1]}},
                           activation_bias_input}) <<< DATA_W;
    bias_addition_result = activation_partial_sum_input + scaled_bias;


    // Signed Saturation : Overflow 발생 시 생기는 문제 방지
    // ACC_W 확장 시 Sig_ROM 주소 위치가 [15:6]에서 [25:16]으로 이동하므로 기존 경로를 주석 처리
    /*
    if (!activation_partial_sum_input[ACC_W-1] && !scaled_bias[ACC_W-1] &&
        bias_addition_result[ACC_W-1])
      saturated_activation_input = {1'b0, {(ACC_W-1){1'b1}}};
    else if (activation_partial_sum_input[ACC_W-1] && scaled_bias[ACC_W-1] &&
             !bias_addition_result[ACC_W-1])
      saturated_activation_input = {1'b1, {(ACC_W-1){1'b0}}};
    else
      saturated_activation_input = bias_addition_result;

    sigmoid_rom_address = saturated_activation_input
                          [ACC_W-1 -: SIGMOID_ADDRESS_WIDTH];
    */

    // 수정: 확장된 합을 기존 16비트 Activation 범위로 saturation
    if (bias_addition_result >
        $signed({{(ACC_W-ACTIVATION_INPUT_WIDTH){1'b0}}, ACTIVATION_MAX})) begin
      saturated_activation_input = ACTIVATION_MAX;
    end
    else if (bias_addition_result <
             $signed({{(ACC_W-ACTIVATION_INPUT_WIDTH){1'b1}}, ACTIVATION_MIN})) begin
      saturated_activation_input = ACTIVATION_MIN;
    end
    else begin
      saturated_activation_input =
          bias_addition_result[ACTIVATION_INPUT_WIDTH-1:0];
    end

    // 수정: 기존 16비트 고정소수점 형식의 [15:6]을 Sig_ROM 주소로 사용
    sigmoid_rom_address = saturated_activation_input
                          [ACTIVATION_INPUT_WIDTH-1 -: SIGMOID_ADDRESS_WIDTH];
  end

  // 기존의 Sig_ROM 그대로 적용
  Sig_ROM #(
    .inWidth (SIGMOID_ADDRESS_WIDTH),
    .dataWidth(DATA_W)
  ) sigmoid_lookup_table (
    .clk(clk),
    .x  (sigmoid_rom_address),
    .out(sigmoid_rom_data)
  );

  assign activation_output_data = $signed(sigmoid_rom_data);

  // Activation_Unit 리셋 및 완료 신호 인가
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      activation_output_valid <= 1'b0;
    else
      activation_output_valid <= activation_input_valid;
  end
endmodule

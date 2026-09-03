module NPU_Top #(
  parameter int DATA_W = 8,
  parameter int ACC_W = 2 * DATA_W + $clog2(784),
  parameter int BATCH_SIZE = 5,
  parameter int ARRAY_SIZE = 5,
  parameter int INPUT_DATA_SIZE = 784,
  parameter int OUTPUT_CLASS_COUNT = 10,
  parameter int LAYER1_OUTPUT_SIZE = 30,
  parameter int LAYER2_OUTPUT_SIZE = 20,
  parameter int LAYER3_OUTPUT_SIZE = 10,
  parameter int UNIFIED_BUFFER_COMPUTE_DEPTH =
      (LAYER1_OUTPUT_SIZE > LAYER2_OUTPUT_SIZE) ?
      LAYER1_OUTPUT_SIZE : LAYER2_OUTPUT_SIZE,
  parameter int UNIFIED_BUFFER_AREA_DEPTH =
      INPUT_DATA_SIZE + UNIFIED_BUFFER_COMPUTE_DEPTH,
  parameter int COUNTER_WIDTH = 10,
  parameter int SRAM_READ_LATENCY = 1,
  parameter int SIGMOID_ADDRESS_WIDTH = 10
)(
  input  logic clk,
  input  logic rst_n,
  input  logic signed [DATA_W-1:0] input_data,
  input  logic input_data_valid,
  output logic input_data_ready,
  input  logic image_batch_start,
  output logic [31:0] image_batch_result [0:BATCH_SIZE-1],
  output logic image_batch_result_valid,
  input  logic image_batch_result_ready,
  output logic image_batch_start_ready,
  output logic input_loader_busy,
  output logic prefetch_batch_ready
  // output logic image_batch_complete
);
  localparam int IMAGE_INDEX_WIDTH = $clog2(BATCH_SIZE);
  localparam int UNIFIED_BUFFER_ADDRESS_WIDTH =
      $clog2(UNIFIED_BUFFER_AREA_DEPTH);
  localparam int COMPUTE_REGION_BASE_ADDRESS = INPUT_DATA_SIZE;
  localparam int GROUP_INDEX_WIDTH = 3;
  localparam int COLUMN_INDEX_WIDTH = $clog2(ARRAY_SIZE);

  // 수정: AXI 입력 로더와 DNN 연산 스케줄러를 독립 FSM으로 분리
  typedef enum logic [1:0] {
    LOAD_IDLE,
    LOAD_STREAM,
    LOAD_COMPLETE
  } loader_state_t;

  typedef enum logic [3:0] {
    IDLE,
    LAYER_SETUP,
    TILE_START,
    TILE_WAIT,
    ACTIVATION_WRITE,
    GROUP_CHECK,
    LAYER_CHECK,
    MAXFINDER_WAIT,
    RESULT_VALID
  } dnn_state_t;

  loader_state_t loader_state, next_loader_state;
  dnn_state_t dnn_state, next_dnn_state;

  logic [1:0] current_layer_index;
  logic [GROUP_INDEX_WIDTH-1:0] neuron_group_index;
  logic [COLUMN_INDEX_WIDTH-1:0] activation_column_index;
  logic [COUNTER_WIDTH-1:0] current_common_dimension_length;
  logic [GROUP_INDEX_WIDTH-1:0] current_layer_group_count;

  // Unified Buffer의 제어 신호
  logic [IMAGE_INDEX_WIDTH-1:0] prefetch_image_index;
  logic [UNIFIED_BUFFER_ADDRESS_WIDTH-1:0] prefetch_pixel_index;
  logic prefetch_area_select;
  logic compute_area_select;
  logic compute_batch_start;
  logic prefetch_write_enable;
  logic prefetch_write_ready;

  logic compute_read_area_select;
  logic compute_write_area_select;
  logic compute_read_enable [0:BATCH_SIZE-1];
  logic [UNIFIED_BUFFER_ADDRESS_WIDTH-1:0]
      compute_read_address [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0]
      compute_read_data [0:BATCH_SIZE-1];
  logic compute_read_valid [0:BATCH_SIZE-1];
  logic compute_write_enable [0:BATCH_SIZE-1];
  logic [UNIFIED_BUFFER_ADDRESS_WIDTH-1:0]
      compute_write_address [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0]
      compute_write_data [0:BATCH_SIZE-1];

  // Systolic Controller의 제어 신호
  logic controller_input_read_enable [0:ARRAY_SIZE-1];
  logic [COUNTER_WIDTH-1:0]
      controller_input_read_address [0:ARRAY_SIZE-1];
  logic signed [DATA_W-1:0]
      controller_input_read_data [0:ARRAY_SIZE-1];
  logic controller_input_read_valid [0:ARRAY_SIZE-1];
  logic weight_sram_read_enable [0:ARRAY_SIZE-1];
  logic [COUNTER_WIDTH-1:0]
      weight_sram_read_address [0:ARRAY_SIZE-1];
  logic signed [DATA_W-1:0]
      weight_sram_read_data [0:ARRAY_SIZE-1];
  logic weight_sram_read_valid [0:ARRAY_SIZE-1];
  logic bias_sram_read_enable [0:ARRAY_SIZE-1];
  logic signed [DATA_W-1:0] bias_sram_read_data [0:ARRAY_SIZE-1];
  logic bias_sram_read_valid [0:ARRAY_SIZE-1];

  logic array_controller_start;
  logic array_controller_busy;
  logic array_controller_done;
  logic signed [ACC_W-1:0]
      array_result [0:BATCH_SIZE-1][0:ARRAY_SIZE-1];
  logic signed [ACC_W-1:0]
      partial_sum_capture_register [0:BATCH_SIZE-1][0:ARRAY_SIZE-1]; // Capture Register

  // Activation Unit의 제어 신호
  logic activation_input_valid [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0] activation_output_data [0:BATCH_SIZE-1];
  logic activation_output_valid [0:BATCH_SIZE-1];
  logic activation_input_issued;
  logic activation_launch;
  logic activation_all_valid;
  logic activation_write_complete;

  // maxFinder 제어 신호
  logic maxfinder_clear;
  logic [31:0] maxfinder_output_data [0:BATCH_SIZE-1];
  logic maxfinder_output_valid [0:BATCH_SIZE-1];
  logic maxfinder_all_complete;

  logic more_neuron_groups;
  logic more_layers;
  integer unified_buffer_port_index;
  integer bias_unit_index;
  integer activation_unit_index;
  integer image_batch_index;

  // Layer별 K 길이. Unified Buffer의 영역 선택은 Source MUX를 제거하고 Selection Bit로 처리
  always_comb begin
    case (current_layer_index)
      2'd1: begin
        current_common_dimension_length = INPUT_DATA_SIZE;
        current_layer_group_count = LAYER1_OUTPUT_SIZE / ARRAY_SIZE;
        compute_read_area_select = compute_area_select;
        compute_write_area_select = ~compute_area_select;
      end
      2'd2: begin
        current_common_dimension_length = LAYER1_OUTPUT_SIZE;
        current_layer_group_count = LAYER2_OUTPUT_SIZE / ARRAY_SIZE;
        compute_read_area_select = ~compute_area_select;
        compute_write_area_select = compute_area_select;
      end
      default: begin
        current_common_dimension_length = LAYER2_OUTPUT_SIZE;
        current_layer_group_count = LAYER3_OUTPUT_SIZE / ARRAY_SIZE;
        compute_read_area_select = compute_area_select;
        compute_write_area_select = ~compute_area_select;
      end
    endcase
  end

  assign image_batch_start_ready = (loader_state == LOAD_IDLE);
  assign input_loader_busy = (loader_state == LOAD_STREAM);
  assign prefetch_batch_ready = (loader_state == LOAD_COMPLETE); // prefetch가 완료되어 DNN으로 보낼 준비가 되었다는 신호
  assign compute_batch_start = (dnn_state == IDLE) && prefetch_batch_ready; // 로드된 데이터를 DNN이 이용하기 위한 신호

  assign input_data_ready = (loader_state == LOAD_STREAM) &&
                            prefetch_write_ready;
  assign prefetch_write_enable = input_data_valid && input_data_ready;
  assign array_controller_start = (dnn_state == TILE_START);
  assign image_batch_result_valid = (dnn_state == RESULT_VALID);

  assign more_neuron_groups =
      ((neuron_group_index + 1'b1) < current_layer_group_count);
  assign more_layers = (current_layer_index < 2'd3);

  assign activation_all_valid = activation_output_valid[0] &&
                                activation_output_valid[1] &&
                                activation_output_valid[2] &&
                                activation_output_valid[3] &&
                                activation_output_valid[4];
  assign maxfinder_all_complete = maxfinder_output_valid[0] &&
                                  maxfinder_output_valid[1] &&
                                  maxfinder_output_valid[2] &&
                                  maxfinder_output_valid[3] &&
                                  maxfinder_output_valid[4];

  assign activation_launch = (dnn_state == ACTIVATION_WRITE) &&
                             !activation_input_issued &&
                             bias_sram_read_valid[activation_column_index];
  assign activation_write_complete = (dnn_state == ACTIVATION_WRITE) &&
                                     activation_all_valid &&
                                     (activation_column_index == ARRAY_SIZE-1);
  assign maxfinder_clear = (dnn_state == LAYER_SETUP) &&
                           (current_layer_index == 2'd3);

  // Controller 요청을 Unified Buffer에 직접 전달
  always_comb begin
    for (unified_buffer_port_index = 0;
         unified_buffer_port_index < BATCH_SIZE;
         unified_buffer_port_index++) begin
      compute_read_enable[unified_buffer_port_index]
          = controller_input_read_enable[unified_buffer_port_index];
      if (current_layer_index == 2'd1)
        compute_read_address[unified_buffer_port_index]
            = controller_input_read_address[unified_buffer_port_index]
                                           [UNIFIED_BUFFER_ADDRESS_WIDTH-1:0];
      else
        compute_read_address[unified_buffer_port_index]
            = COMPUTE_REGION_BASE_ADDRESS +
              controller_input_read_address[unified_buffer_port_index];
      controller_input_read_data[unified_buffer_port_index]
          = compute_read_data[unified_buffer_port_index];
      controller_input_read_valid[unified_buffer_port_index]
          = compute_read_valid[unified_buffer_port_index];

      compute_write_enable[unified_buffer_port_index] = 1'b0;
      compute_write_address[unified_buffer_port_index] = '0;
      compute_write_data[unified_buffer_port_index] = '0;

      // Layer 3 결과는 Unified Buffer를 거치지 않고 maxFinder로 직접 전달
      if ((dnn_state == ACTIVATION_WRITE) && activation_all_valid &&
          (current_layer_index != 2'd3)) begin
        compute_write_enable[unified_buffer_port_index] = 1'b1;
        compute_write_address[unified_buffer_port_index]
            = COMPUTE_REGION_BASE_ADDRESS +
              neuron_group_index * ARRAY_SIZE + activation_column_index;
        compute_write_data[unified_buffer_port_index]
            = activation_output_data[unified_buffer_port_index];
      end
    end
  end

  always_comb begin
    for (bias_unit_index = 0; bias_unit_index < ARRAY_SIZE;
         bias_unit_index++) begin
      bias_sram_read_enable[bias_unit_index]
          = (dnn_state == ACTIVATION_WRITE);
    end
    for (activation_unit_index = 0; activation_unit_index < BATCH_SIZE;
         activation_unit_index++) begin
      activation_input_valid[activation_unit_index] = activation_launch;
    end
  end

  // 독립 Input Loader FSM
  always_comb begin
    next_loader_state = loader_state;
    case (loader_state)
      LOAD_IDLE:
        if (image_batch_start && image_batch_start_ready)
          next_loader_state = LOAD_STREAM;
      LOAD_STREAM:
        if (prefetch_write_enable &&
            (prefetch_image_index == BATCH_SIZE-1) &&
            (prefetch_pixel_index == INPUT_DATA_SIZE-1))
          next_loader_state = LOAD_COMPLETE;
      LOAD_COMPLETE:
        if (compute_batch_start)
          next_loader_state = LOAD_IDLE;
      default:
        next_loader_state = LOAD_IDLE;
    endcase
  end

  // INPUT_LOAD, OUTPUT_LOAD, MAXFINDER_START를 제거한 DNN Scheduler
  always_comb begin
    next_dnn_state = dnn_state;
    case (dnn_state)
      IDLE:
        if (prefetch_batch_ready) next_dnn_state = LAYER_SETUP;
      LAYER_SETUP:
        next_dnn_state = TILE_START;
      TILE_START:
        next_dnn_state = TILE_WAIT;
      TILE_WAIT:
        if (array_controller_done) next_dnn_state = ACTIVATION_WRITE;
      ACTIVATION_WRITE:
        if (activation_write_complete) next_dnn_state = GROUP_CHECK;
      GROUP_CHECK:
        if (more_neuron_groups) next_dnn_state = TILE_START;
        else                    next_dnn_state = LAYER_CHECK;
      LAYER_CHECK:
        if (more_layers) next_dnn_state = LAYER_SETUP;
        else             next_dnn_state = MAXFINDER_WAIT;
      MAXFINDER_WAIT:
        if (maxfinder_all_complete) next_dnn_state = RESULT_VALID;
      RESULT_VALID:
        if (image_batch_result_ready) next_dnn_state = IDLE;
      default:
        next_dnn_state = IDLE;
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      loader_state <= LOAD_IDLE;
      prefetch_image_index <= '0;
      prefetch_pixel_index <= '0;
      prefetch_area_select <= 1'b0;
      compute_area_select <= 1'b0;
    end else begin
      loader_state <= next_loader_state;

      if ((loader_state == LOAD_IDLE) && image_batch_start) begin
        prefetch_image_index <= '0;
        prefetch_pixel_index <= '0;
      end

      if ((loader_state == LOAD_STREAM) && prefetch_write_enable) begin
        if (prefetch_pixel_index == INPUT_DATA_SIZE-1) begin
          prefetch_pixel_index <= '0;
          if (prefetch_image_index != BATCH_SIZE-1)
            prefetch_image_index <= prefetch_image_index + 1'b1;
        end else begin
          prefetch_pixel_index <= prefetch_pixel_index + 1'b1;
        end
      end

      if (compute_batch_start) begin
        compute_area_select <= prefetch_area_select;
        prefetch_area_select <= ~prefetch_area_select;
      end
    end
  end

  // DNN Scheduler 세부적인 동작 제어
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dnn_state <= IDLE;
      current_layer_index <= 2'd1;
      neuron_group_index <= '0;
      activation_column_index <= '0;
      activation_input_issued <= 1'b0;
      // image_batch_complete <= 1'b0;
      for (image_batch_index = 0; image_batch_index < BATCH_SIZE;
           image_batch_index++) begin
        image_batch_result[image_batch_index] <= '0;
      end
    end else begin
      dnn_state <= next_dnn_state;
      // image_batch_complete <= 1'b0;

      if (compute_batch_start) begin
        current_layer_index <= 2'd1;
        neuron_group_index <= '0;
      end

      if ((dnn_state == TILE_WAIT) && array_controller_done) begin
        for (int image_index = 0; image_index < BATCH_SIZE; image_index++)
          for (int column_index = 0; column_index < ARRAY_SIZE; column_index++)
            partial_sum_capture_register[image_index][column_index]
                <= array_result[image_index][column_index];
        activation_column_index <= '0;
        activation_input_issued <= 1'b0;
      end

      if (dnn_state == ACTIVATION_WRITE) begin
        if (activation_launch)
          activation_input_issued <= 1'b1;

        if (activation_all_valid) begin
          activation_input_issued <= 1'b0;
          if (activation_column_index != ARRAY_SIZE-1)
            activation_column_index <= activation_column_index + 1'b1;
        end
      end

      if ((dnn_state == GROUP_CHECK) && more_neuron_groups)
        neuron_group_index <= neuron_group_index + 1'b1;

      if ((dnn_state == LAYER_CHECK) && more_layers) begin
        current_layer_index <= current_layer_index + 1'b1;
        neuron_group_index <= '0;
      end

      if ((dnn_state == MAXFINDER_WAIT) && maxfinder_all_complete) begin
        for (image_batch_index = 0; image_batch_index < BATCH_SIZE;
             image_batch_index++)
          image_batch_result[image_batch_index]
              <= maxfinder_output_data[image_batch_index];
        // image_batch_complete <= 1'b1;
      end
    end
  end

  Unified_Buffer #(
    .DATA_W(DATA_W),
    .BATCH_SIZE(BATCH_SIZE),
    .INPUT_REGION_DEPTH(INPUT_DATA_SIZE),
    .COMPUTE_REGION_DEPTH(UNIFIED_BUFFER_COMPUTE_DEPTH),
    .AREA_DEPTH(UNIFIED_BUFFER_AREA_DEPTH),
    .ADDRESS_WIDTH(UNIFIED_BUFFER_ADDRESS_WIDTH),
    .SRAM_READ_LATENCY(SRAM_READ_LATENCY)
  ) unified_buffer (
    .clk(clk),
    .rst_n(rst_n),
    .prefetch_area_select(prefetch_area_select),
    .prefetch_write_enable(prefetch_write_enable),
    .prefetch_write_data(input_data),
    .prefetch_image_index(prefetch_image_index),
    .prefetch_pixel_index(prefetch_pixel_index),
    .prefetch_write_ready(prefetch_write_ready),
    .compute_read_area_select(compute_read_area_select),
    .compute_read_enable(compute_read_enable),
    .compute_read_address(compute_read_address),
    .compute_read_data(compute_read_data),
    .compute_read_valid(compute_read_valid),
    .compute_write_area_select(compute_write_area_select),
    .compute_write_enable(compute_write_enable),
    .compute_write_address(compute_write_address),
    .compute_write_data(compute_write_data)
  );

  Weight_SRAM #(
    .DATA_W(DATA_W),
    .ARRAY_SIZE(ARRAY_SIZE),
    .COUNTER_WIDTH(COUNTER_WIDTH),
    .SRAM_READ_LATENCY(SRAM_READ_LATENCY),
    .LAYER1_INPUT_SIZE(INPUT_DATA_SIZE),
    .LAYER1_OUTPUT_SIZE(LAYER1_OUTPUT_SIZE),
    .LAYER2_INPUT_SIZE(LAYER1_OUTPUT_SIZE),
    .LAYER2_OUTPUT_SIZE(LAYER2_OUTPUT_SIZE),
    .LAYER3_INPUT_SIZE(LAYER2_OUTPUT_SIZE),
    .LAYER3_OUTPUT_SIZE(LAYER3_OUTPUT_SIZE)
  ) weight_sram (
    .clk(clk),
    .rst_n(rst_n),
    .current_layer_index(current_layer_index),
    .neuron_group_index(neuron_group_index),
    .weight_sram_read_enable(weight_sram_read_enable),
    .weight_sram_read_address(weight_sram_read_address),
    .weight_sram_read_data(weight_sram_read_data),
    .weight_sram_read_valid(weight_sram_read_valid)
  );

  Bias_SRAM #(
    .DATA_W(DATA_W),
    .ARRAY_SIZE(ARRAY_SIZE),
    .SRAM_READ_LATENCY(SRAM_READ_LATENCY),
    .LAYER1_OUTPUT_SIZE(LAYER1_OUTPUT_SIZE),
    .LAYER2_OUTPUT_SIZE(LAYER2_OUTPUT_SIZE),
    .LAYER3_OUTPUT_SIZE(LAYER3_OUTPUT_SIZE)
  ) bias_sram (
    .clk(clk),
    .rst_n(rst_n),
    .current_layer_index(current_layer_index),
    .neuron_group_index(neuron_group_index),
    .bias_sram_read_enable(bias_sram_read_enable),
    .bias_sram_read_data(bias_sram_read_data),
    .bias_sram_read_valid(bias_sram_read_valid)
  );

  systolic_controller #(
    .DATA_W(DATA_W),
    .ROWS(ARRAY_SIZE),
    .COLS(ARRAY_SIZE),
    .COUNTER_WIDTH(COUNTER_WIDTH),
    .SRAM_READ_LATENCY(SRAM_READ_LATENCY),
    .ACC_W(ACC_W)
  ) array_controller (
    .clk(clk),
    .rst_n(rst_n),
    .i_start(array_controller_start),
    .o_done(array_controller_done),
    .o_busy(array_controller_busy),
    .current_common_dimension_length(current_common_dimension_length),
    .input_feature_read_enable(controller_input_read_enable),
    .input_feature_read_address(controller_input_read_address),
    .input_feature_read_data(controller_input_read_data),
    .input_feature_read_valid(controller_input_read_valid),
    .weight_sram_read_enable(weight_sram_read_enable),
    .weight_sram_read_address(weight_sram_read_address),
    .weight_sram_read_data(weight_sram_read_data),
    .weight_sram_read_valid(weight_sram_read_valid),
    .o_mat_c(array_result)
  );

  generate
    genvar generated_activation_unit_index;
    for (generated_activation_unit_index = 0;
         generated_activation_unit_index < BATCH_SIZE;
         generated_activation_unit_index++) begin : ACTIVATION_UNIT_GENERATE
      Activation_Unit #(
        .DATA_W(DATA_W),
        .ACC_W(ACC_W),
        .SIGMOID_ADDRESS_WIDTH(SIGMOID_ADDRESS_WIDTH)
      ) activation_unit (
        .clk(clk),
        .rst_n(rst_n),
        .activation_input_valid(
            activation_input_valid[generated_activation_unit_index]),
        .activation_partial_sum_input(
            partial_sum_capture_register[generated_activation_unit_index]
                                        [activation_column_index]),
        .activation_bias_input(bias_sram_read_data[activation_column_index]),
        .activation_output_data(
            activation_output_data[generated_activation_unit_index]),
        .activation_output_valid(
            activation_output_valid[generated_activation_unit_index])
      );
    end

    // packed vector를 받는 maxFinder input register 없이 score 0 ~ 9를 순서대로 직접 입력
    genvar maxfinder_index;
    for (maxfinder_index = 0; maxfinder_index < BATCH_SIZE;
         maxfinder_index++) begin : MAXFINDER_GENERATE
      maxFinder #(
        .numInput(OUTPUT_CLASS_COUNT),
        .inputWidth(DATA_W)
      ) maxfinder (
        .i_clk(clk),
        .i_clear(maxfinder_clear),
        .i_score(activation_output_data[maxfinder_index]),
        .i_score_valid((current_layer_index == 2'd3) &&
                       activation_output_valid[maxfinder_index]),
        .o_data(maxfinder_output_data[maxfinder_index]),
        .o_data_valid(maxfinder_output_valid[maxfinder_index])
      );
    end
  endgenerate
endmodule

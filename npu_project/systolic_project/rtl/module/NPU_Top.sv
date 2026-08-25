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
  parameter int GLOBAL_BUFFER_DEPTH = 30,
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
  output logic image_batch_complete
);
  localparam int IMAGE_INDEX_WIDTH = $clog2(BATCH_SIZE);
  localparam int INPUT_ADDRESS_WIDTH = $clog2(INPUT_DATA_SIZE);
  localparam int GLOBAL_BUFFER_ADDRESS_WIDTH = $clog2(GLOBAL_BUFFER_DEPTH);
  localparam int GROUP_INDEX_WIDTH = 3;
  localparam int COLUMN_INDEX_WIDTH = $clog2(ARRAY_SIZE);
  localparam int SCORE_INDEX_WIDTH = $clog2(OUTPUT_CLASS_COUNT);

  typedef enum logic [3:0] {
    IDLE,
    INPUT_LOAD,
    LAYER_SETUP,
    TILE_START,
    TILE_WAIT,
    ACTIVATION_WRITE,
    GROUP_CHECK,
    LAYER_CHECK,
    OUTPUT_LOAD,
    MAXFINDER_START,
    MAXFINDER_WAIT,
    RESULT_VALID
  } dnn_state_t;

  dnn_state_t dnn_state, next_dnn_state;

  logic [1:0] current_layer_index;
  logic [GROUP_INDEX_WIDTH-1:0] neuron_group_index;
  logic [COLUMN_INDEX_WIDTH-1:0] activation_column_index;
  logic [SCORE_INDEX_WIDTH-1:0] maxfinder_score_index;
  logic [COUNTER_WIDTH-1:0] current_common_dimension_length;
  logic [COUNTER_WIDTH-1:0] current_layer_output_size;
  logic [GROUP_INDEX_WIDTH-1:0] current_layer_group_count;

  logic [IMAGE_INDEX_WIDTH-1:0] input_buffer_image_index;
  logic [INPUT_ADDRESS_WIDTH-1:0] input_buffer_pixel_index;
  logic input_buffer_clear;
  logic input_buffer_load_enable;
  logic input_buffer_batch_load_complete;
  logic input_buffer_read_enable [0:BATCH_SIZE-1];
  logic [INPUT_ADDRESS_WIDTH-1:0]
      input_buffer_read_address [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0]
      input_buffer_read_data [0:BATCH_SIZE-1];
  logic input_buffer_read_valid [0:BATCH_SIZE-1];

  logic global_buffer_read_buffer_select;
  logic global_buffer_write_buffer_select;
  logic global_buffer_read_enable [0:BATCH_SIZE-1];
  logic global_buffer_write_enable [0:BATCH_SIZE-1];
  logic [GLOBAL_BUFFER_ADDRESS_WIDTH-1:0]
      global_buffer_read_address [0:BATCH_SIZE-1];
  logic [GLOBAL_BUFFER_ADDRESS_WIDTH-1:0]
      global_buffer_write_address [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0]
      global_buffer_write_data [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0]
      global_buffer_read_data [0:BATCH_SIZE-1];
  logic global_buffer_read_valid [0:BATCH_SIZE-1];

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
      partial_sum_capture_register [0:BATCH_SIZE-1][0:ARRAY_SIZE-1];

  logic activation_input_valid [0:BATCH_SIZE-1];
  logic signed [DATA_W-1:0] activation_output_data [0:BATCH_SIZE-1];
  logic activation_output_valid [0:BATCH_SIZE-1];
  logic activation_input_issued; // 중복 요청을 막기 위한 내부 상태 플래그
  logic activation_launch;
  logic activation_all_valid;
  logic activation_write_complete;

  logic output_read_ready;
  logic maxfinder_input_load_complete;
  logic [OUTPUT_CLASS_COUNT*DATA_W-1:0]
      maxfinder_input_register [0:BATCH_SIZE-1];
  logic maxfinder_start;
  logic [31:0] maxfinder_output_data [0:BATCH_SIZE-1];
  logic maxfinder_output_valid [0:BATCH_SIZE-1];
  logic maxfinder_all_complete;

  logic more_neuron_groups;
  logic more_layers;
  integer source_bank_index;
  integer bias_bank_index;
  integer activation_unit_index;
  integer image_batch_index;

  // Layer에 따른 Ping-Pong Buffering을 구현하기 위한 조합 논리
  always_comb begin
    case (current_layer_index)
      2'd1: begin
        current_common_dimension_length = INPUT_DATA_SIZE;
        current_layer_output_size = LAYER1_OUTPUT_SIZE;
        current_layer_group_count = LAYER1_OUTPUT_SIZE / ARRAY_SIZE;
        global_buffer_read_buffer_select  = 1'b0;
        global_buffer_write_buffer_select = 1'b0;
      end
      2'd2: begin
        current_common_dimension_length = LAYER1_OUTPUT_SIZE;
        current_layer_output_size = LAYER2_OUTPUT_SIZE;
        current_layer_group_count = LAYER2_OUTPUT_SIZE / ARRAY_SIZE;
        global_buffer_read_buffer_select  = 1'b0;
        global_buffer_write_buffer_select = 1'b1;
      end
      default: begin
        current_common_dimension_length = LAYER2_OUTPUT_SIZE;
        current_layer_output_size = LAYER3_OUTPUT_SIZE;
        current_layer_group_count = LAYER3_OUTPUT_SIZE / ARRAY_SIZE;
        global_buffer_read_buffer_select  = 1'b1;
        global_buffer_write_buffer_select = 1'b0;
      end
    endcase

    // Final layer scores are stored in buffer A.
    if (dnn_state == OUTPUT_LOAD)
      global_buffer_read_buffer_select = 1'b0;
  end

  assign input_data_ready = (dnn_state == INPUT_LOAD);
  assign input_buffer_load_enable = input_data_valid && input_data_ready;
  assign input_buffer_clear = (dnn_state == IDLE) && image_batch_start;
  assign array_controller_start = (dnn_state == TILE_START);
  assign maxfinder_start = (dnn_state == MAXFINDER_START);
  assign image_batch_result_valid = (dnn_state == RESULT_VALID);

  assign more_neuron_groups =
      ((neuron_group_index + 1'b1) < current_layer_group_count);
  assign more_layers = (current_layer_index < 2'd3);

  // &activation_output_valid 해도 되지만, 직관적으로 보기 위해 모든 valid 신호를 and로 묶음
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

  // Source MUX : Layer 1 reads the input buffer / Layers 2, 3 read ping-pong
  always_comb begin
    for (source_bank_index = 0; source_bank_index < BATCH_SIZE;
         source_bank_index++) begin
      input_buffer_read_enable[source_bank_index] = 1'b0;
      input_buffer_read_address[source_bank_index] = '0;
      global_buffer_read_enable[source_bank_index] = 1'b0;
      global_buffer_read_address[source_bank_index] = '0;
      global_buffer_write_enable[source_bank_index] = 1'b0;
      global_buffer_write_address[source_bank_index] = '0;
      global_buffer_write_data[source_bank_index] = '0;
      controller_input_read_data[source_bank_index] = '0;
      controller_input_read_valid[source_bank_index] = 1'b0;

      if (current_layer_index == 2'd1) begin
        input_buffer_read_enable[source_bank_index]
            = controller_input_read_enable[source_bank_index];
        input_buffer_read_address[source_bank_index]
            = controller_input_read_address[source_bank_index][INPUT_ADDRESS_WIDTH-1:0];
        controller_input_read_data[source_bank_index]
            = input_buffer_read_data[source_bank_index];
        controller_input_read_valid[source_bank_index]
            = input_buffer_read_valid[source_bank_index];
      end else begin
        global_buffer_read_enable[source_bank_index]
            = controller_input_read_enable[source_bank_index];
        global_buffer_read_address[source_bank_index]
            = controller_input_read_address[source_bank_index]
                                           [GLOBAL_BUFFER_ADDRESS_WIDTH-1:0];
        controller_input_read_data[source_bank_index]
            = global_buffer_read_data[source_bank_index];
        controller_input_read_valid[source_bank_index]
            = global_buffer_read_valid[source_bank_index];
      end

      if ((dnn_state == ACTIVATION_WRITE) && activation_all_valid) begin
        global_buffer_write_enable[source_bank_index] = 1'b1;
        global_buffer_write_address[source_bank_index]
            = neuron_group_index * ARRAY_SIZE + activation_column_index;
        global_buffer_write_data[source_bank_index]
            = activation_output_data[source_bank_index];
      end

      if ((dnn_state == OUTPUT_LOAD) && !output_read_ready) begin
        global_buffer_read_enable[source_bank_index] = 1'b1;
        global_buffer_read_address[source_bank_index] = maxfinder_score_index;
      end
    end
  end

  always_comb begin
    for (bias_bank_index = 0; bias_bank_index < ARRAY_SIZE;
         bias_bank_index++) begin
      bias_sram_read_enable[bias_bank_index]
          = (dnn_state == ACTIVATION_WRITE);
    end
    for (activation_unit_index = 0; activation_unit_index < BATCH_SIZE;
         activation_unit_index++) begin
      activation_input_valid[activation_unit_index] = activation_launch;
    end
  end

  assign maxfinder_input_load_complete = (dnn_state == OUTPUT_LOAD) &&
      output_read_ready &&
      global_buffer_read_valid[0] && global_buffer_read_valid[1] &&
      global_buffer_read_valid[2] && global_buffer_read_valid[3] &&
      global_buffer_read_valid[4] &&
      (maxfinder_score_index == OUTPUT_CLASS_COUNT-1);

  // DNN Scheduler에서 next_state로 이동
  always_comb begin
    next_dnn_state = dnn_state;
    case (dnn_state)
      IDLE:
        if (image_batch_start) next_dnn_state = INPUT_LOAD;
      INPUT_LOAD:
        if (input_buffer_batch_load_complete) next_dnn_state = LAYER_SETUP;
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
        else             next_dnn_state = OUTPUT_LOAD;
      OUTPUT_LOAD:
        if (maxfinder_input_load_complete)
          next_dnn_state = MAXFINDER_START;
      MAXFINDER_START:
        next_dnn_state = MAXFINDER_WAIT;
      MAXFINDER_WAIT:
        if (maxfinder_all_complete) next_dnn_state = RESULT_VALID;
      RESULT_VALID:
        if (image_batch_result_ready) next_dnn_state = IDLE;
      default:
        next_dnn_state = IDLE;
    endcase
  end

  // DNN Scheduler의 State에 따른 동작 제어 + Capture register + MaxFinder Input Register
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dnn_state <= IDLE;
      current_layer_index <= 2'd1;
      neuron_group_index <= '0;
      activation_column_index <= '0;
      maxfinder_score_index <= '0;
      input_buffer_image_index <= '0;
      input_buffer_pixel_index <= '0;
      activation_input_issued <= 1'b0;
      output_read_ready <= 1'b0;
      image_batch_complete <= 1'b0;
      for (image_batch_index = 0; image_batch_index < BATCH_SIZE;
           image_batch_index++) begin
        image_batch_result[image_batch_index] <= '0;
        maxfinder_input_register[image_batch_index] <= '0;
      end
    end else begin
      dnn_state <= next_dnn_state;
      image_batch_complete <= 1'b0;

      if ((dnn_state == IDLE) && image_batch_start) begin
        current_layer_index <= 2'd1;
        neuron_group_index <= '0;
        input_buffer_image_index <= '0;
        input_buffer_pixel_index <= '0;
        maxfinder_score_index <= '0;
        output_read_ready <= 1'b0;
        for (image_batch_index = 0; image_batch_index < BATCH_SIZE;
             image_batch_index++)
          maxfinder_input_register[image_batch_index] <= '0;
      end

      if ((dnn_state == INPUT_LOAD) && input_buffer_load_enable) begin
        if (input_buffer_pixel_index == INPUT_DATA_SIZE-1) begin
          input_buffer_pixel_index <= '0;
          if (input_buffer_image_index != BATCH_SIZE-1)
            input_buffer_image_index <= input_buffer_image_index + 1'b1;
        end else begin
          input_buffer_pixel_index <= input_buffer_pixel_index + 1'b1;
        end
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

      if (dnn_state == GROUP_CHECK) begin
        if (more_neuron_groups)
          neuron_group_index <= neuron_group_index + 1'b1;
      end

      if (dnn_state == LAYER_CHECK) begin
        if (more_layers) begin
          current_layer_index <= current_layer_index + 1'b1;
          neuron_group_index <= '0;
        end else begin
          maxfinder_score_index <= '0;
          output_read_ready <= 1'b0;
        end
      end

      if (dnn_state == OUTPUT_LOAD) begin
        if (!output_read_ready)
          output_read_ready <= 1'b1;

        if (output_read_ready &&
            global_buffer_read_valid[0] && global_buffer_read_valid[1] &&
            global_buffer_read_valid[2] && global_buffer_read_valid[3] &&
            global_buffer_read_valid[4]) begin
          for (image_batch_index = 0; image_batch_index < BATCH_SIZE;
               image_batch_index++)
            maxfinder_input_register[image_batch_index]
                [maxfinder_score_index*DATA_W +: DATA_W]
                <= global_buffer_read_data[image_batch_index];
          output_read_ready <= 1'b0;
          if (maxfinder_score_index != OUTPUT_CLASS_COUNT-1)
            maxfinder_score_index <= maxfinder_score_index + 1'b1;
        end
      end

      if ((dnn_state == MAXFINDER_WAIT) && maxfinder_all_complete) begin
        for (image_batch_index = 0; image_batch_index < BATCH_SIZE;
             image_batch_index++)
          image_batch_result[image_batch_index]
              <= maxfinder_output_data[image_batch_index];
        image_batch_complete <= 1'b1;
      end
    end
  end

  Input_Buffer #(
    .DATA_W(DATA_W),
    .BATCH_SIZE(BATCH_SIZE),
    .INPUT_DATA_SIZE(INPUT_DATA_SIZE)
  ) input_buffer (
    .clk(clk),
    .rst_n(rst_n),
    .input_buffer_clear(input_buffer_clear),
    .input_buffer_load_data(input_data),
    .input_buffer_load_enable(input_buffer_load_enable),
    .input_buffer_image_index(input_buffer_image_index),
    .input_buffer_pixel_index(input_buffer_pixel_index),
    .input_buffer_batch_load_complete(input_buffer_batch_load_complete),
    .input_buffer_read_enable(input_buffer_read_enable),
    .input_buffer_read_address(input_buffer_read_address),
    .input_buffer_read_data(input_buffer_read_data),
    .input_buffer_read_valid(input_buffer_read_valid)
  );

  Global_Buffer #(
    .DATA_W(DATA_W),
    .BATCH_SIZE(BATCH_SIZE),
    .GLOBAL_BUFFER_DEPTH(GLOBAL_BUFFER_DEPTH)
  ) global_buffer (
    .clk(clk),
    .rst_n(rst_n),
    .global_buffer_read_buffer_select(global_buffer_read_buffer_select),
    .global_buffer_write_buffer_select(global_buffer_write_buffer_select),
    .global_buffer_read_enable(global_buffer_read_enable),
    .global_buffer_write_enable(global_buffer_write_enable),
    .global_buffer_read_address(global_buffer_read_address),
    .global_buffer_write_address(global_buffer_write_address),
    .global_buffer_write_data(global_buffer_write_data),
    .global_buffer_read_data(global_buffer_read_data),
    .global_buffer_read_valid(global_buffer_read_valid)
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

    genvar maxfinder_index;
    for (maxfinder_index = 0; maxfinder_index < BATCH_SIZE;
         maxfinder_index++) begin : MAXFINDER_GENERATE
      maxFinder #(
        .numInput(OUTPUT_CLASS_COUNT),
        .inputWidth(DATA_W)
      ) maxfinder (
        .i_clk(clk),
        .i_data(maxfinder_input_register[maxfinder_index]),
        .i_valid(maxfinder_start),
        .o_data(maxfinder_output_data[maxfinder_index]),
        .o_data_valid(maxfinder_output_valid[maxfinder_index])
      );
    end
  endgenerate
endmodule

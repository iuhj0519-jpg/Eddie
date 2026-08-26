module Weight_SRAM #(
  parameter int DATA_W = 8,
  parameter int ARRAY_SIZE = 5,
  parameter int COUNTER_WIDTH = 10,
  parameter int LAYER_INDEX_WIDTH = 2,
  parameter int GROUP_INDEX_WIDTH = 3,
  parameter int SRAM_READ_LATENCY = 1,
  parameter int LAYER1_INPUT_SIZE = 784,
  parameter int LAYER1_OUTPUT_SIZE = 30,
  parameter int LAYER2_INPUT_SIZE = 30,
  parameter int LAYER2_OUTPUT_SIZE = 20,
  parameter int LAYER3_INPUT_SIZE = 20,
  parameter int LAYER3_OUTPUT_SIZE = 10
)(
  input  logic clk,
  input  logic rst_n,
  input  logic [LAYER_INDEX_WIDTH-1:0] current_layer_index,
  input  logic [GROUP_INDEX_WIDTH-1:0] neuron_group_index,
  input  logic weight_sram_read_enable [0:ARRAY_SIZE-1],
  input  logic [COUNTER_WIDTH-1:0] weight_sram_read_address [0:ARRAY_SIZE-1],
  output logic signed [DATA_W-1:0] weight_sram_read_data [0:ARRAY_SIZE-1],
  output logic weight_sram_read_valid [0:ARRAY_SIZE-1]
);
  localparam int LAYER1_WEIGHT_COUNT = LAYER1_INPUT_SIZE * LAYER1_OUTPUT_SIZE;
  localparam int LAYER2_WEIGHT_COUNT = LAYER2_INPUT_SIZE * LAYER2_OUTPUT_SIZE;
  localparam int LAYER3_WEIGHT_COUNT = LAYER3_INPUT_SIZE * LAYER3_OUTPUT_SIZE;

  logic signed [DATA_W-1:0] layer1_weight_memory [0:LAYER1_WEIGHT_COUNT-1];
  logic signed [DATA_W-1:0] layer2_weight_memory [0:LAYER2_WEIGHT_COUNT-1];
  logic signed [DATA_W-1:0] layer3_weight_memory [0:LAYER3_WEIGHT_COUNT-1];

  logic signed [DATA_W-1:0] read_data_pipeline [0:ARRAY_SIZE-1][0:SRAM_READ_LATENCY-1];
  logic read_valid_pipeline [0:ARRAY_SIZE-1][0:SRAM_READ_LATENCY-1];

  integer neuron_index;
  integer bank_index;
  integer latency_index;
  integer selected_neuron_index;
  string mif_file_name;

  // 모든 Layer 연산에 필요한 Weight들을 SRAM 한 곳에 저장 (순차 로드하려면 외부 DRAM에 Weight를 보관해야 함)
  // 5 Bank로 구성되어 있어 5개의 포트가 존재
  initial begin
    for (neuron_index = 0; neuron_index < LAYER1_OUTPUT_SIZE; neuron_index++) begin
      mif_file_name = $sformatf("w_1_%0d.mif", neuron_index);
      $readmemb(mif_file_name, layer1_weight_memory,
                neuron_index * LAYER1_INPUT_SIZE,
                neuron_index * LAYER1_INPUT_SIZE + LAYER1_INPUT_SIZE - 1);
    end
    for (neuron_index = 0; neuron_index < LAYER2_OUTPUT_SIZE; neuron_index++) begin
      mif_file_name = $sformatf("w_2_%0d.mif", neuron_index);
      $readmemb(mif_file_name, layer2_weight_memory,
                neuron_index * LAYER2_INPUT_SIZE,
                neuron_index * LAYER2_INPUT_SIZE + LAYER2_INPUT_SIZE - 1);
    end
    for (neuron_index = 0; neuron_index < LAYER3_OUTPUT_SIZE; neuron_index++) begin
      mif_file_name = $sformatf("w_3_%0d.mif", neuron_index);
      $readmemb(mif_file_name, layer3_weight_memory,
                neuron_index * LAYER3_INPUT_SIZE,
                neuron_index * LAYER3_INPUT_SIZE + LAYER3_INPUT_SIZE - 1);
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (bank_index = 0; bank_index < ARRAY_SIZE; bank_index++) begin
        for (latency_index = 0; latency_index < SRAM_READ_LATENCY;
             latency_index++) begin
          read_data_pipeline[bank_index][latency_index]  <= '0;
          read_valid_pipeline[bank_index][latency_index] <= 1'b0;
        end
      end
    end else begin
      for (bank_index = 0; bank_index < ARRAY_SIZE; bank_index++) begin
        read_valid_pipeline[bank_index][0]
            <= weight_sram_read_enable[bank_index];

        if (weight_sram_read_enable[bank_index]) begin
          selected_neuron_index = neuron_group_index * ARRAY_SIZE + bank_index; // 그룹에 해당하는 각 뉴런에 Weight를 부여
          case (current_layer_index)
            2'd1: read_data_pipeline[bank_index][0]
                <= layer1_weight_memory[
                     selected_neuron_index * LAYER1_INPUT_SIZE +
                     weight_sram_read_address[bank_index]];
            2'd2: read_data_pipeline[bank_index][0]
                <= layer2_weight_memory[
                     selected_neuron_index * LAYER2_INPUT_SIZE +
                     weight_sram_read_address[bank_index]];
            2'd3: read_data_pipeline[bank_index][0]
                <= layer3_weight_memory[
                     selected_neuron_index * LAYER3_INPUT_SIZE +
                     weight_sram_read_address[bank_index]];
            default: read_data_pipeline[bank_index][0] <= '0;
          endcase
        end

        // SRAM_READ_LATENCY가 2 이상으로 확장될 때를 대비해 구성한 것
        for (latency_index = 1; latency_index < SRAM_READ_LATENCY;
             latency_index++) begin
          read_data_pipeline[bank_index][latency_index]
              <= read_data_pipeline[bank_index][latency_index-1];
          read_valid_pipeline[bank_index][latency_index]
              <= read_valid_pipeline[bank_index][latency_index-1];
        end
      end
    end
  end

  generate
    genvar output_bank_index;
    for (output_bank_index = 0; output_bank_index < ARRAY_SIZE;
         output_bank_index++) begin : WEIGHT_OUTPUT_BIND
      assign weight_sram_read_data[output_bank_index]
          = read_data_pipeline[output_bank_index][SRAM_READ_LATENCY-1];
      assign weight_sram_read_valid[output_bank_index]
          = read_valid_pipeline[output_bank_index][SRAM_READ_LATENCY-1];
    end
  endgenerate
endmodule

module Bias_SRAM #(
  parameter int DATA_W = 8,
  parameter int ARRAY_SIZE = 5,
  parameter int LAYER_INDEX_WIDTH = 2,
  parameter int GROUP_INDEX_WIDTH = 3,
  parameter int SRAM_READ_LATENCY = 1,
  parameter int LAYER1_OUTPUT_SIZE = 30,
  parameter int LAYER2_OUTPUT_SIZE = 20,
  parameter int LAYER3_OUTPUT_SIZE = 10
)(
  input  logic clk,
  input  logic rst_n,
  input  logic [LAYER_INDEX_WIDTH-1:0] current_layer_index,
  input  logic [GROUP_INDEX_WIDTH-1:0] neuron_group_index,
  input  logic bias_sram_read_enable [0:ARRAY_SIZE-1],
  output logic signed [DATA_W-1:0]
               bias_sram_read_data [0:ARRAY_SIZE-1],
  output logic bias_sram_read_valid [0:ARRAY_SIZE-1]
);
  logic signed [DATA_W-1:0] layer1_bias_memory [0:LAYER1_OUTPUT_SIZE-1];
  logic signed [DATA_W-1:0] layer2_bias_memory [0:LAYER2_OUTPUT_SIZE-1];
  logic signed [DATA_W-1:0] layer3_bias_memory [0:LAYER3_OUTPUT_SIZE-1];

  logic signed [DATA_W-1:0]
      read_data_pipeline [0:ARRAY_SIZE-1][0:SRAM_READ_LATENCY-1];
  logic read_valid_pipeline [0:ARRAY_SIZE-1][0:SRAM_READ_LATENCY-1];

  integer neuron_index;
  integer bank_index;
  integer latency_index;
  integer selected_neuron_index;
  string mif_file_name;

  initial begin
    for (neuron_index = 0; neuron_index < LAYER1_OUTPUT_SIZE; neuron_index++) begin
      mif_file_name = $sformatf("b_1_%0d.mif", neuron_index);
      $readmemb(mif_file_name, layer1_bias_memory, neuron_index, neuron_index);
    end
    for (neuron_index = 0; neuron_index < LAYER2_OUTPUT_SIZE; neuron_index++) begin
      mif_file_name = $sformatf("b_2_%0d.mif", neuron_index);
      $readmemb(mif_file_name, layer2_bias_memory, neuron_index, neuron_index);
    end
    for (neuron_index = 0; neuron_index < LAYER3_OUTPUT_SIZE; neuron_index++) begin
      mif_file_name = $sformatf("b_3_%0d.mif", neuron_index);
      $readmemb(mif_file_name, layer3_bias_memory, neuron_index, neuron_index);
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
            <= bias_sram_read_enable[bank_index];
        if (bias_sram_read_enable[bank_index]) begin
          selected_neuron_index = neuron_group_index * ARRAY_SIZE + bank_index;
          case (current_layer_index)
            2'd1: read_data_pipeline[bank_index][0]
                <= layer1_bias_memory[selected_neuron_index];
            2'd2: read_data_pipeline[bank_index][0]
                <= layer2_bias_memory[selected_neuron_index];
            2'd3: read_data_pipeline[bank_index][0]
                <= layer3_bias_memory[selected_neuron_index];
            default: read_data_pipeline[bank_index][0] <= '0;
          endcase
        end

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
         output_bank_index++) begin : BIAS_OUTPUT_BIND
      assign bias_sram_read_data[output_bank_index]
          = read_data_pipeline[output_bank_index][SRAM_READ_LATENCY-1];
      assign bias_sram_read_valid[output_bank_index]
          = read_valid_pipeline[output_bank_index][SRAM_READ_LATENCY-1];
    end
  endgenerate
endmodule

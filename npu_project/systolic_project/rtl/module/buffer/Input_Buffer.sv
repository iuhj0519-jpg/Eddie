module Input_Buffer #(
  parameter int DATA_W = 8,
  parameter int BATCH_SIZE = 5,
  parameter int INPUT_DATA_SIZE = 784,
  parameter int IMAGE_INDEX_WIDTH = $clog2(BATCH_SIZE),
  parameter int INPUT_ADDRESS_WIDTH = $clog2(INPUT_DATA_SIZE)
)(
  input  logic clk,
  input  logic rst_n,
  input  logic input_buffer_clear,
  input  logic signed [DATA_W-1:0] input_buffer_load_data,
  input  logic input_buffer_load_enable,
  input  logic [IMAGE_INDEX_WIDTH-1:0] input_buffer_image_index,
  input  logic [INPUT_ADDRESS_WIDTH-1:0] input_buffer_pixel_index,
  output logic input_buffer_batch_load_complete,
  input  logic input_buffer_read_enable [0:BATCH_SIZE-1],
  input  logic [INPUT_ADDRESS_WIDTH-1:0]
               input_buffer_read_address [0:BATCH_SIZE-1],
  output logic signed [DATA_W-1:0]
               input_buffer_read_data [0:BATCH_SIZE-1],
  output logic input_buffer_read_valid [0:BATCH_SIZE-1]
);
  logic signed [DATA_W-1:0]
      input_buffer_memory [0:BATCH_SIZE-1][0:INPUT_DATA_SIZE-1];

  integer bank_index;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      input_buffer_batch_load_complete <= 1'b0;
      for (bank_index = 0; bank_index < BATCH_SIZE; bank_index++) begin
        input_buffer_read_data[bank_index]  <= '0;
        input_buffer_read_valid[bank_index] <= 1'b0;
      end
    end else begin
      if (input_buffer_clear)
        input_buffer_batch_load_complete <= 1'b0;

      if (input_buffer_load_enable) begin
        input_buffer_memory[input_buffer_image_index]
                           [input_buffer_pixel_index] <= input_buffer_load_data;

        if ((input_buffer_image_index == BATCH_SIZE-1) &&
            (input_buffer_pixel_index == INPUT_DATA_SIZE-1))
          input_buffer_batch_load_complete <= 1'b1;
      end

      for (bank_index = 0; bank_index < BATCH_SIZE; bank_index++) begin
        input_buffer_read_valid[bank_index]
            <= input_buffer_read_enable[bank_index];
        if (input_buffer_read_enable[bank_index])
          input_buffer_read_data[bank_index]
              <= input_buffer_memory[bank_index]
                                    [input_buffer_read_address[bank_index]];
      end
    end
  end
endmodule

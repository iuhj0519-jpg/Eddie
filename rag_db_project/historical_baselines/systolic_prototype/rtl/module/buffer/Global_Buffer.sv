module Global_Buffer #(
  parameter int DATA_W = 8,
  parameter int BATCH_SIZE = 5,
  parameter int GLOBAL_BUFFER_DEPTH = 30,
  parameter int GLOBAL_BUFFER_ADDRESS_WIDTH = $clog2(GLOBAL_BUFFER_DEPTH)
)(
  input  logic clk,
  input  logic rst_n,
  input  logic global_buffer_read_buffer_select,
  input  logic global_buffer_write_buffer_select,
  input  logic global_buffer_read_enable [0:BATCH_SIZE-1],
  input  logic global_buffer_write_enable [0:BATCH_SIZE-1],
  input  logic [GLOBAL_BUFFER_ADDRESS_WIDTH-1:0]
               global_buffer_read_address [0:BATCH_SIZE-1],
  input  logic [GLOBAL_BUFFER_ADDRESS_WIDTH-1:0]
               global_buffer_write_address [0:BATCH_SIZE-1],
  input  logic signed [DATA_W-1:0]
               global_buffer_write_data [0:BATCH_SIZE-1],
  output logic signed [DATA_W-1:0]
               global_buffer_read_data [0:BATCH_SIZE-1],
  output logic global_buffer_read_valid [0:BATCH_SIZE-1]
);
  logic signed [DATA_W-1:0]
      global_buffer_a [0:BATCH_SIZE-1][0:GLOBAL_BUFFER_DEPTH-1];
  logic signed [DATA_W-1:0]
      global_buffer_b [0:BATCH_SIZE-1][0:GLOBAL_BUFFER_DEPTH-1];

  integer bank_index;

  // select=0: buffer A, select=1: buffer B
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (bank_index = 0; bank_index < BATCH_SIZE; bank_index++) begin
        global_buffer_read_data[bank_index]  <= '0;
        global_buffer_read_valid[bank_index] <= 1'b0;
      end
    end else begin
      for (bank_index = 0; bank_index < BATCH_SIZE; bank_index++) begin
        global_buffer_read_valid[bank_index]
            <= global_buffer_read_enable[bank_index];

        if (global_buffer_read_enable[bank_index]) begin
          if (global_buffer_read_buffer_select == 1'b0)
            global_buffer_read_data[bank_index]
                <= global_buffer_a[bank_index]
                                  [global_buffer_read_address[bank_index]];
          else
            global_buffer_read_data[bank_index]
                <= global_buffer_b[bank_index]
                                  [global_buffer_read_address[bank_index]];
        end

        if (global_buffer_write_enable[bank_index]) begin
          if (global_buffer_write_buffer_select == 1'b0)
            global_buffer_a[bank_index]
                           [global_buffer_write_address[bank_index]]
                <= global_buffer_write_data[bank_index];
          else
            global_buffer_b[bank_index]
                           [global_buffer_write_address[bank_index]]
                <= global_buffer_write_data[bank_index];
        end
      end
    end
  end
endmodule

module Unified_Buffer #(
  parameter int DATA_W            = 8,
  parameter int BATCH_SIZE        = 5,
  parameter int INPUT_REGION_DEPTH = 784,
  parameter int COMPUTE_REGION_DEPTH = 30,
  parameter int AREA_DEPTH = INPUT_REGION_DEPTH + COMPUTE_REGION_DEPTH,
  parameter int ADDRESS_WIDTH     = $clog2(AREA_DEPTH),
  parameter int SRAM_READ_LATENCY = 1
)(
  input  logic clk,
  input  logic rst_n,

  input  logic                          prefetch_area_select,
  input  logic                          prefetch_write_enable,
  input  logic signed [DATA_W-1:0]      prefetch_write_data,
  input  logic [$clog2(BATCH_SIZE)-1:0] prefetch_image_index,
  input  logic [ADDRESS_WIDTH-1:0]      prefetch_pixel_index,
  output logic                          prefetch_write_ready,

  input  logic                          compute_read_area_select,
  input  logic                          compute_read_enable [0:BATCH_SIZE-1],
  input  logic [ADDRESS_WIDTH-1:0]      compute_read_address[0:BATCH_SIZE-1],
  output logic signed [DATA_W-1:0]      compute_read_data   [0:BATCH_SIZE-1],
  output logic                          compute_read_valid  [0:BATCH_SIZE-1],

  input  logic                          compute_write_area_select,
  input  logic                          compute_write_enable[0:BATCH_SIZE-1],
  input  logic [ADDRESS_WIDTH-1:0]      compute_write_address[0:BATCH_SIZE-1],
  input  logic signed [DATA_W-1:0]      compute_write_data  [0:BATCH_SIZE-1]
);
  logic signed [DATA_W-1:0]
      area_a_memory [0:BATCH_SIZE-1][0:AREA_DEPTH-1];
  logic signed [DATA_W-1:0]
      area_b_memory [0:BATCH_SIZE-1][0:AREA_DEPTH-1];

  // Claude
  logic signed [DATA_W-1:0]
      read_data_pipeline [0:BATCH_SIZE-1][0:SRAM_READ_LATENCY-1];
  logic read_valid_pipeline
      [0:BATCH_SIZE-1][0:SRAM_READ_LATENCY-1];

  integer bank_index;
  integer latency_index;
  integer conflict_bank_index;
  logic prefetch_address_valid;
  logic prefetch_write_conflict;

  assign prefetch_address_valid =
      (prefetch_image_index < BATCH_SIZE) &&
      (prefetch_pixel_index < INPUT_REGION_DEPTH);

  // compute write / AXI write 충돌 방지
  always_comb begin 
    prefetch_write_conflict = 1'b0;
    for (conflict_bank_index = 0;
         conflict_bank_index < BATCH_SIZE;
         conflict_bank_index++) begin
      if (prefetch_address_valid &&
          (prefetch_image_index == conflict_bank_index) &&
          compute_write_enable[conflict_bank_index] &&
          (compute_write_area_select == prefetch_area_select))
        prefetch_write_conflict = 1'b1;
    end
  end

  assign prefetch_write_ready = prefetch_address_valid &&
                                !prefetch_write_conflict;

  // SRAM 자체의 Latency를 고려한 Hardware Skew (Skewing Unit과 다른 SRAM 자체 특성)
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (bank_index = 0; bank_index < BATCH_SIZE; bank_index++) begin
        for (latency_index = 0;
             latency_index < SRAM_READ_LATENCY;
             latency_index++) begin
          read_data_pipeline[bank_index][latency_index] <= '0;
          read_valid_pipeline[bank_index][latency_index] <= 1'b0;
        end
      end
    end else begin
      for (bank_index = 0; bank_index < BATCH_SIZE; bank_index++) begin
        // 동일 area/bank에 두 write가 겹치면 compute write가 우선
        if (compute_write_enable[bank_index] &&
            (compute_write_address[bank_index] < AREA_DEPTH) &&
            !compute_write_area_select) begin
          area_a_memory[bank_index][compute_write_address[bank_index]]
              <= compute_write_data[bank_index];
        end else if (prefetch_write_enable && prefetch_address_valid &&
                     !prefetch_area_select &&
                     (prefetch_image_index == bank_index)) begin
          area_a_memory[bank_index][prefetch_pixel_index]
              <= prefetch_write_data;
        end

        if (compute_write_enable[bank_index] &&
            (compute_write_address[bank_index] < AREA_DEPTH) &&
            compute_write_area_select) begin
          area_b_memory[bank_index][compute_write_address[bank_index]]
              <= compute_write_data[bank_index];
        end else if (prefetch_write_enable && prefetch_address_valid &&
                     prefetch_area_select &&
                     (prefetch_image_index == bank_index)) begin
          area_b_memory[bank_index][prefetch_pixel_index]
              <= prefetch_write_data;
        end

        read_valid_pipeline[bank_index][0]
            <= compute_read_enable[bank_index] &&
               (compute_read_address[bank_index] < AREA_DEPTH);

        if (compute_read_enable[bank_index] &&
            (compute_read_address[bank_index] < AREA_DEPTH)) begin
          // 동일 cycle 동일 주소 충돌은 write-first로 정의한다.
          if (compute_write_enable[bank_index] &&
              (compute_write_area_select == compute_read_area_select) &&
              (compute_write_address[bank_index] ==
               compute_read_address[bank_index]) &&
              (compute_write_address[bank_index] < AREA_DEPTH)) begin
            read_data_pipeline[bank_index][0]
                <= compute_write_data[bank_index];
          end else if (prefetch_write_enable && prefetch_address_valid &&
                       (prefetch_area_select == compute_read_area_select) &&
                       (prefetch_image_index == bank_index) &&
                       (prefetch_pixel_index ==
                        compute_read_address[bank_index])) begin
            read_data_pipeline[bank_index][0] <= prefetch_write_data;
          end else if (compute_read_area_select) begin
            read_data_pipeline[bank_index][0]
                <= area_b_memory[bank_index]
                                [compute_read_address[bank_index]];
          end else begin
            read_data_pipeline[bank_index][0]
                <= area_a_memory[bank_index]
                                [compute_read_address[bank_index]];
          end
        end

        for (latency_index = 1;
             latency_index < SRAM_READ_LATENCY;
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
    for (output_bank_index = 0;
         output_bank_index < BATCH_SIZE;
         output_bank_index++) begin : UNIFIED_BUFFER_OUTPUT_BIND
      assign compute_read_data[output_bank_index] =
          read_data_pipeline[output_bank_index][SRAM_READ_LATENCY-1];
      assign compute_read_valid[output_bank_index] =
          read_valid_pipeline[output_bank_index][SRAM_READ_LATENCY-1];
    end
  endgenerate

endmodule

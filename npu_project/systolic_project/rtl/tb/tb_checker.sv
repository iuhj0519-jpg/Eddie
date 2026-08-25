`timescale 1ns / 1ps

// Stand-alone checker for the internal layer results of NPU_Top.
// This testbench is independent of top_sim and bypasses AXI-Lite so that
// data-path errors can be isolated from the bus interface.
module tb_checker;
  localparam int DATA_W = 8;
  localparam int ACC_W = 2 * DATA_W + $clog2(784);
  localparam int BATCH_SIZE = 5;
  localparam int INPUT_DATA_SIZE = 784;
  localparam int LAYER1_OUTPUT_SIZE = 30;
  localparam int LAYER2_OUTPUT_SIZE = 20;
  localparam int LAYER3_OUTPUT_SIZE = 10;

  // Values follow the declaration order of dnn_state_t in NPU_Top.
  localparam logic [3:0] DNN_TILE_WAIT   = 4'd4;
  localparam logic [3:0] DNN_LAYER_CHECK = 4'd7;

  logic clk;
  logic rst_n;
  logic signed [DATA_W-1:0] input_data;
  logic input_data_valid;
  logic input_data_ready;
  logic image_batch_start;
  logic [31:0] image_batch_result [0:BATCH_SIZE-1];
  logic image_batch_result_valid;
  logic image_batch_result_ready;
  logic image_batch_complete;

  logic [DATA_W-1:0] image_memory_0 [0:INPUT_DATA_SIZE];
  logic [DATA_W-1:0] image_memory_1 [0:INPUT_DATA_SIZE];
  logic [DATA_W-1:0] image_memory_2 [0:INPUT_DATA_SIZE];
  logic [DATA_W-1:0] image_memory_3 [0:INPUT_DATA_SIZE];
  logic [DATA_W-1:0] image_memory_4 [0:INPUT_DATA_SIZE];

  // Raw MAC values before bias/Sigmoid.
  logic signed [ACC_W-1:0]
      layer1_raw_mac [0:BATCH_SIZE-1][0:LAYER1_OUTPUT_SIZE-1];
  logic signed [ACC_W-1:0]
      layer2_raw_mac [0:BATCH_SIZE-1][0:LAYER2_OUTPUT_SIZE-1];
  logic signed [ACC_W-1:0]
      layer3_raw_mac [0:BATCH_SIZE-1][0:LAYER3_OUTPUT_SIZE-1];

  // Activated values written to the ping-pong Global Buffer.
  logic signed [DATA_W-1:0]
      layer1_output [0:BATCH_SIZE-1][0:LAYER1_OUTPUT_SIZE-1];
  logic signed [DATA_W-1:0]
      layer2_output [0:BATCH_SIZE-1][0:LAYER2_OUTPUT_SIZE-1];
  logic signed [DATA_W-1:0]
      layer3_output [0:BATCH_SIZE-1][0:LAYER3_OUTPUT_SIZE-1];

  integer stimulus_image_index;
  integer initialization_image_index;
  integer initialization_neuron_index;
  integer result_image_index;
  integer raw_image_index;
  integer raw_neuron_index;
  integer raw_capture_address;
  integer activated_image_index;
  integer activated_capture_address;
  integer printed_image_index;
  integer pass_count;
  integer fail_count;

  NPU_Top #(
    .DATA_W(DATA_W),
    .ACC_W(ACC_W),
    .BATCH_SIZE(BATCH_SIZE),
    .INPUT_DATA_SIZE(INPUT_DATA_SIZE),
    .LAYER1_OUTPUT_SIZE(LAYER1_OUTPUT_SIZE),
    .LAYER2_OUTPUT_SIZE(LAYER2_OUTPUT_SIZE),
    .LAYER3_OUTPUT_SIZE(LAYER3_OUTPUT_SIZE)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .input_data(input_data),
    .input_data_valid(input_data_valid),
    .input_data_ready(input_data_ready),
    .image_batch_start(image_batch_start),
    .image_batch_result(image_batch_result),
    .image_batch_result_valid(image_batch_result_valid),
    .image_batch_result_ready(image_batch_result_ready),
    .image_batch_complete(image_batch_complete)
  );

  initial clk = 1'b0;
  always #5 clk = ~clk;

  function automatic logic [DATA_W-1:0] selected_pixel(
    input integer selected_image,
    input integer selected_pixel_index
  );
    begin
      case (selected_image)
        0: selected_pixel = image_memory_0[selected_pixel_index];
        1: selected_pixel = image_memory_1[selected_pixel_index];
        2: selected_pixel = image_memory_2[selected_pixel_index];
        3: selected_pixel = image_memory_3[selected_pixel_index];
        default: selected_pixel = image_memory_4[selected_pixel_index];
      endcase
    end
  endfunction

  function automatic logic [DATA_W-1:0] expected_class(
    input integer selected_image
  );
    begin
      expected_class = selected_pixel(selected_image, INPUT_DATA_SIZE);
    end
  endfunction

  task automatic send_one_image(input integer selected_image);
    integer send_pixel_index;
    begin
      for (send_pixel_index = 0; send_pixel_index < INPUT_DATA_SIZE;
           send_pixel_index = send_pixel_index + 1) begin
        @(negedge clk);
        input_data = selected_pixel(selected_image, send_pixel_index);
        input_data_valid = 1'b1;

        do @(posedge clk);
        while (!input_data_ready);
      end

      @(negedge clk);
      input_data_valid = 1'b0;
      input_data = '0;
    end
  endtask

  task automatic print_layer1(input integer selected_image);
    integer display_neuron_index;
    begin
      $display("============================================================");
      $display("[DUT] Layer 1 complete: image %0d, output [1x30]",
               selected_image);
      $write("Activated: [ ");
      for (display_neuron_index = 0;
           display_neuron_index < LAYER1_OUTPUT_SIZE;
           display_neuron_index = display_neuron_index + 1) begin
        $write("%0d ",
               $signed(layer1_output[selected_image][display_neuron_index]));
        if (((display_neuron_index + 1) % 10) == 0 &&
            display_neuron_index != LAYER1_OUTPUT_SIZE-1)
          $write("\n             ");
      end
      $write("]\nRaw MAC  : [ ");
      for (display_neuron_index = 0;
           display_neuron_index < LAYER1_OUTPUT_SIZE;
           display_neuron_index = display_neuron_index + 1) begin
        $write("%0d ",
               $signed(layer1_raw_mac[selected_image][display_neuron_index]));
        if (((display_neuron_index + 1) % 10) == 0 &&
            display_neuron_index != LAYER1_OUTPUT_SIZE-1)
          $write("\n             ");
      end
      $write("]\n");
    end
  endtask

  task automatic print_layer2(input integer selected_image);
    integer display_neuron_index;
    begin
      $display("============================================================");
      $display("[DUT] Layer 2 complete: image %0d, output [1x20]",
               selected_image);
      $write("Activated: [ ");
      for (display_neuron_index = 0;
           display_neuron_index < LAYER2_OUTPUT_SIZE;
           display_neuron_index = display_neuron_index + 1) begin
        $write("%0d ",
               $signed(layer2_output[selected_image][display_neuron_index]));
        if (((display_neuron_index + 1) % 10) == 0 &&
            display_neuron_index != LAYER2_OUTPUT_SIZE-1)
          $write("\n             ");
      end
      $write("]\nRaw MAC  : [ ");
      for (display_neuron_index = 0;
           display_neuron_index < LAYER2_OUTPUT_SIZE;
           display_neuron_index = display_neuron_index + 1) begin
        $write("%0d ",
               $signed(layer2_raw_mac[selected_image][display_neuron_index]));
        if (((display_neuron_index + 1) % 10) == 0 &&
            display_neuron_index != LAYER2_OUTPUT_SIZE-1)
          $write("\n             ");
      end
      $write("]\n");
    end
  endtask

  task automatic print_layer3(input integer selected_image);
    integer display_neuron_index;
    begin
      $display("============================================================");
      $display("[DUT] Layer 3 complete: image %0d, output [1x10]",
               selected_image);
      $write("Activated: [ ");
      for (display_neuron_index = 0;
           display_neuron_index < LAYER3_OUTPUT_SIZE;
           display_neuron_index = display_neuron_index + 1)
        $write("%0d ",
               $signed(layer3_output[selected_image][display_neuron_index]));
      $write("]\nRaw MAC  : [ ");
      for (display_neuron_index = 0;
           display_neuron_index < LAYER3_OUTPUT_SIZE;
           display_neuron_index = display_neuron_index + 1)
        $write("%0d ",
               $signed(layer3_raw_mac[selected_image][display_neuron_index]));
      $write("]\n");
    end
  endtask

  // Capture raw MAC results when one 5-neuron tile finishes.
  always @(posedge clk) begin
    if (rst_n && dut.dnn_state == DNN_TILE_WAIT &&
        dut.array_controller_done) begin
      for (raw_image_index = 0; raw_image_index < BATCH_SIZE;
           raw_image_index = raw_image_index + 1) begin
        for (raw_neuron_index = 0; raw_neuron_index < 5;
             raw_neuron_index = raw_neuron_index + 1) begin
          raw_capture_address = dut.neuron_group_index * 5 + raw_neuron_index;
          case (dut.current_layer_index)
            2'd1:
              if (raw_capture_address < LAYER1_OUTPUT_SIZE)
                layer1_raw_mac[raw_image_index][raw_capture_address]
                    = dut.array_result[raw_image_index][raw_neuron_index];
            2'd2:
              if (raw_capture_address < LAYER2_OUTPUT_SIZE)
                layer2_raw_mac[raw_image_index][raw_capture_address]
                    = dut.array_result[raw_image_index][raw_neuron_index];
            default:
              if (raw_capture_address < LAYER3_OUTPUT_SIZE)
                layer3_raw_mac[raw_image_index][raw_capture_address]
                    = dut.array_result[raw_image_index][raw_neuron_index];
          endcase
        end
      end
    end
  end

  // Capture the post-bias/post-Sigmoid values at the actual Global Buffer
  // write interface. This is the value consumed by the following layer.
  always @(posedge clk) begin
    if (rst_n) begin
      for (activated_image_index = 0; activated_image_index < BATCH_SIZE;
           activated_image_index = activated_image_index + 1) begin
        if (dut.global_buffer_write_enable[activated_image_index]) begin
          activated_capture_address
              = dut.global_buffer_write_address[activated_image_index];
          case (dut.current_layer_index)
            2'd1:
              if (activated_capture_address < LAYER1_OUTPUT_SIZE)
                layer1_output[activated_image_index][activated_capture_address]
                    = dut.global_buffer_write_data[activated_image_index];
            2'd2:
              if (activated_capture_address < LAYER2_OUTPUT_SIZE)
                layer2_output[activated_image_index][activated_capture_address]
                    = dut.global_buffer_write_data[activated_image_index];
            default:
              if (activated_capture_address < LAYER3_OUTPUT_SIZE)
                layer3_output[activated_image_index][activated_capture_address]
                    = dut.global_buffer_write_data[activated_image_index];
          endcase
        end
      end
    end
  end

  // Print each completed layer. Image 0 is test_data_0000.txt (digit 7), the
  // image currently known to be classified as 6.
  always @(posedge clk) begin
    if (rst_n && dut.dnn_state == DNN_LAYER_CHECK) begin
      case (dut.current_layer_index)
        2'd1:
          for (printed_image_index = 0; printed_image_index < BATCH_SIZE;
               printed_image_index = printed_image_index + 1)
            print_layer1(printed_image_index);
        2'd2:
          for (printed_image_index = 0; printed_image_index < BATCH_SIZE;
               printed_image_index = printed_image_index + 1)
            print_layer2(printed_image_index);
        default:
          for (printed_image_index = 0; printed_image_index < BATCH_SIZE;
               printed_image_index = printed_image_index + 1)
            print_layer3(printed_image_index);
      endcase
    end
  end

  initial begin
    clk = 1'b0;
    rst_n = 1'b0;
    input_data = '0;
    input_data_valid = 1'b0;
    image_batch_start = 1'b0;
    image_batch_result_ready = 1'b0;
    pass_count = 0;
    fail_count = 0;

    for (initialization_image_index = 0;
         initialization_image_index < BATCH_SIZE;
         initialization_image_index = initialization_image_index + 1) begin
      for (initialization_neuron_index = 0;
           initialization_neuron_index < LAYER1_OUTPUT_SIZE;
           initialization_neuron_index = initialization_neuron_index + 1) begin
        layer1_output[initialization_image_index][initialization_neuron_index] = 'x;
        layer1_raw_mac[initialization_image_index][initialization_neuron_index] = 'x;
      end
      for (initialization_neuron_index = 0;
           initialization_neuron_index < LAYER2_OUTPUT_SIZE;
           initialization_neuron_index = initialization_neuron_index + 1) begin
        layer2_output[initialization_image_index][initialization_neuron_index] = 'x;
        layer2_raw_mac[initialization_image_index][initialization_neuron_index] = 'x;
      end
      for (initialization_neuron_index = 0;
           initialization_neuron_index < LAYER3_OUTPUT_SIZE;
           initialization_neuron_index = initialization_neuron_index + 1) begin
        layer3_output[initialization_image_index][initialization_neuron_index] = 'x;
        layer3_raw_mac[initialization_image_index][initialization_neuron_index] = 'x;
      end
    end

    $readmemb("test_data_0000.txt", image_memory_0);
    $readmemb("test_data_0001.txt", image_memory_1);
    $readmemb("test_data_0002.txt", image_memory_2);
    $readmemb("test_data_0003.txt", image_memory_3);
    $readmemb("test_data_0004.txt", image_memory_4);

    repeat (10) @(posedge clk);
    @(negedge clk);
    rst_n = 1'b1;

    // Directly start NPU_Top; AXI-Lite behavior is tested separately by
    // top_sim. The pulse is stable across one rising clock edge.
    repeat (2) @(posedge clk);
    @(negedge clk);
    image_batch_start = 1'b1;
    @(negedge clk);
    image_batch_start = 1'b0;

    for (stimulus_image_index = 0; stimulus_image_index < BATCH_SIZE;
         stimulus_image_index = stimulus_image_index + 1)
      send_one_image(stimulus_image_index);

    wait (image_batch_result_valid === 1'b1);
    $display("============================================================");
    $display("[TB_CHECKER] Final classification results");
    for (result_image_index = 0; result_image_index < BATCH_SIZE;
         result_image_index = result_image_index + 1) begin
      if (image_batch_result[result_image_index]
          == expected_class(result_image_index)) begin
        pass_count = pass_count + 1;
        $display("PASS image %0d: detected=%0d expected=%0d",
                 result_image_index, image_batch_result[result_image_index],
                 expected_class(result_image_index));
      end else begin
        fail_count = fail_count + 1;
        $display("FAIL image %0d: detected=%0d expected=%0d",
                 result_image_index, image_batch_result[result_image_index],
                 expected_class(result_image_index));
      end
    end
    $display("Summary: PASS=%0d FAIL=%0d", pass_count, fail_count);
    $display("============================================================");

    @(negedge clk);
    image_batch_result_ready = 1'b1;
    @(negedge clk);
    image_batch_result_ready = 1'b0;
    repeat (3) @(posedge clk);
    $finish;
  end

  initial begin
    #2_000_000;
    $fatal(1, "tb_checker timeout: the NPU did not finish within 2 ms");
  end
endmodule

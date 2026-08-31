`timescale 1ns/1ps

module top_sim;
    localparam integer TEST_SAMPLE_COUNT = 100;
    localparam integer IMAGE_FEATURE_COUNT = 784;
    localparam integer BATCH_SIZE = 5;

    reg clock;
    reg reset_n;
    reg [7:0] axis_in_data;
    reg axis_in_data_valid;
    wire axis_in_data_ready;
    reg [4:0] s_axi_awaddr;
    reg [2:0] s_axi_awprot;
    reg s_axi_awvalid;
    wire s_axi_awready;
    reg [31:0] s_axi_wdata;
    reg [3:0] s_axi_wstrb;
    reg s_axi_wvalid;
    wire s_axi_wready;
    wire [1:0] s_axi_bresp;
    wire s_axi_bvalid;
    reg s_axi_bready;
    reg [4:0] s_axi_araddr;
    reg [2:0] s_axi_arprot;
    reg s_axi_arvalid;
    wire s_axi_arready;
    wire [31:0] s_axi_rdata;
    wire [1:0] s_axi_rresp;
    wire s_axi_rvalid;
    reg s_axi_rready;
    wire intr;

    reg [7:0] image_memory [0:IMAGE_FEATURE_COUNT];
    reg [7:0] expected_class [0:TEST_SAMPLE_COUNT-1];
    reg [8*128-1:0] test_filename;
    reg [31:0] read_value;
    integer batch_index;
    integer image_index;
    integer feature_index;
    integer sample_index;
    integer producer_sample_index;
    integer consumer_sample_index;
    integer pass_count;
    integer fail_count;
    integer interrupt_count;
    integer controller_elapsed_cycles;
    integer controller_expected_cycles;
    integer total_cycle_count;
    integer first_transfer_cycle;
    integer last_result_cycle;
    integer axi_backpressure_cycles;
    reg controller_measurement_active;
    reg previous_intr;

    always @(posedge clock) begin
        if (!reset_n) begin
            interrupt_count <= 0;
            previous_intr <= 1'b0;
            controller_elapsed_cycles <= 0;
            controller_expected_cycles <= 0;
            controller_measurement_active <= 1'b0;
            total_cycle_count <= 0;
            first_transfer_cycle <= -1;
            last_result_cycle <= -1;
            axi_backpressure_cycles <= 0;
        end else begin
            total_cycle_count <= total_cycle_count + 1;
            if (axis_in_data_valid && axis_in_data_ready && (first_transfer_cycle < 0))
                first_transfer_cycle <= total_cycle_count;
            if (axis_in_data_valid && !axis_in_data_ready)
                axi_backpressure_cycles <= axi_backpressure_cycles + 1;
            if (intr) begin
                if (previous_intr)
                    $fatal(1, "intr must be a one-cycle pulse");
                interrupt_count <= interrupt_count + 1;
            end
            previous_intr <= intr;

            if (device_under_test.controller_start) begin
                controller_measurement_active <= 1'b1;
                controller_elapsed_cycles <= 0;
                case (device_under_test.layer_index)
                    2'd1: controller_expected_cycles <= 797;
                    2'd2: controller_expected_cycles <= 43;
                    default: controller_expected_cycles <= 33;
                endcase
            end else if (controller_measurement_active) begin
                controller_elapsed_cycles <= controller_elapsed_cycles + 1;
                if (device_under_test.controller_done) begin
                    if ((controller_elapsed_cycles + 1) != controller_expected_cycles)
                        $fatal(1, "controller cycle mismatch: measured=%0d expected=%0d", controller_elapsed_cycles + 1, controller_expected_cycles);
                    controller_measurement_active <= 1'b0;
                end
            end
        end
    end

    zyNet device_under_test (
        .s_axi_aclk(clock), .s_axi_aresetn(reset_n),
        .axis_in_data(axis_in_data), .axis_in_data_valid(axis_in_data_valid),
        .axis_in_data_ready(axis_in_data_ready),
        .s_axi_awaddr(s_axi_awaddr), .s_axi_awprot(s_axi_awprot),
        .s_axi_awvalid(s_axi_awvalid), .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata), .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid), .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp), .s_axi_bvalid(s_axi_bvalid), .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr), .s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid), .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata), .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid), .s_axi_rready(s_axi_rready), .intr(intr)
    );

    initial clock = 1'b0;
    always #5 clock = ~clock;

    task send_image;
        input integer selected_sample;
        begin
            if (selected_sample < 10)
                $sformat(test_filename, "../../inputs/reference_model/testdata/test_data_000%0d.txt", selected_sample);
            else
                $sformat(test_filename, "../../inputs/reference_model/testdata/test_data_00%0d.txt", selected_sample);
            $readmemb(test_filename, image_memory);
            expected_class[selected_sample] = image_memory[IMAGE_FEATURE_COUNT];
            for (feature_index = 0; feature_index < IMAGE_FEATURE_COUNT; feature_index = feature_index + 1) begin
                @(negedge clock);
                axis_in_data       = image_memory[feature_index];
                axis_in_data_valid = 1'b1;
                while (!axis_in_data_ready)
                    @(negedge clock);
            end
            @(negedge clock);
            axis_in_data_valid = 1'b0;
        end
    endtask

    task read_axi;
        input [4:0] address;
        output [31:0] data;
        begin
            @(negedge clock);
            s_axi_araddr  = address;
            s_axi_arvalid = 1'b1;
            while (!s_axi_arready) @(negedge clock);
            @(negedge clock);
            s_axi_arvalid = 1'b0;
            while (!s_axi_rvalid) @(negedge clock);
            data = s_axi_rdata;
            s_axi_rready = 1'b1;
            @(negedge clock);
            s_axi_rready = 1'b0;
        end
    endtask

    initial begin
        reset_n = 1'b0;
        axis_in_data = 8'd0;
        axis_in_data_valid = 1'b0;
        s_axi_awaddr = 5'd0;
        s_axi_awprot = 3'd0;
        s_axi_awvalid = 1'b0;
        s_axi_wdata = 32'd0;
        s_axi_wstrb = 4'hf;
        s_axi_wvalid = 1'b0;
        s_axi_bready = 1'b1;
        s_axi_araddr = 5'd0;
        s_axi_arprot = 3'd0;
        s_axi_arvalid = 1'b0;
        s_axi_rready = 1'b0;
        pass_count = 0;
        fail_count = 0;
        interrupt_count = 0;

        repeat (10) @(posedge clock);
        reset_n = 1'b1;
        repeat (5) @(posedge clock);

        fork
            begin : input_producer
                for (producer_sample_index = 0; producer_sample_index < TEST_SAMPLE_COUNT; producer_sample_index = producer_sample_index + 1)
                    send_image(producer_sample_index);
            end
            begin : result_consumer
                for (batch_index = 0; batch_index < TEST_SAMPLE_COUNT/BATCH_SIZE; batch_index = batch_index + 1) begin
                    @(posedge intr);
                    for (image_index = 0; image_index < BATCH_SIZE; image_index = image_index + 1) begin
                        read_axi(5'h08, read_value);
                        consumer_sample_index = batch_index*BATCH_SIZE + image_index;
                        if (read_value[7:0] == expected_class[consumer_sample_index]) begin
                            pass_count = pass_count + 1;
                            $display("PASS sample=%0d detected=%0d expected=%0d", consumer_sample_index, read_value[7:0], expected_class[consumer_sample_index]);
                        end else begin
                            fail_count = fail_count + 1;
                            $display("FAIL sample=%0d detected=%0d expected=%0d", consumer_sample_index, read_value[7:0], expected_class[consumer_sample_index]);
                        end
                    end
                    last_result_cycle = total_cycle_count;
                end
            end
        join

        repeat (4) @(posedge clock);
        $display("FINAL_RESULT PASS=%0d FAIL=%0d ACCURACY=%0.6f%%", pass_count, fail_count, pass_count*100.0/TEST_SAMPLE_COUNT);
        $display("TOTAL_INFERENCE_CYCLES=%0d", last_result_cycle-first_transfer_cycle+1);
        $display("AXI_BACKPRESSURE_CYCLES=%0d", axi_backpressure_cycles);
        if (interrupt_count != TEST_SAMPLE_COUNT/BATCH_SIZE)
            $fatal(1, "interrupt count mismatch: measured=%0d expected=%0d", interrupt_count, TEST_SAMPLE_COUNT/BATCH_SIZE);
        if ((pass_count == 99) && (fail_count == 1))
            $display("REFERENCE_GOLDEN_MATCH PASS");
        else
            $fatal(1, "REFERENCE_GOLDEN_MATCH FAIL");
        $finish;
    end

    initial begin
        #10000000;
        $fatal(1, "TIMEOUT");
    end
endmodule

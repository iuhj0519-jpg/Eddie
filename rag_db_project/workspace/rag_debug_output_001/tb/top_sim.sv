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
    integer batch_index, image_index, feature_index;
    integer producer_sample_index, consumer_sample_index;
    integer pass_count, fail_count, interrupt_count;
    integer total_cycle_count, first_transfer_cycle, last_result_cycle;
    integer axi_backpressure_cycles;
    integer controller_elapsed_cycles, controller_expected_cycles;
    reg controller_measurement_active;
    reg previous_intr, previous_stream_stall, previous_read_stall;
    reg [7:0] previous_stream_data;
    reg [31:0] previous_read_data;
    integer protocol_errors, peak_active_pe_count, active_pe_count, monitor_index;
    wire [24:0] pe_active;

    // Independently check all 24,320 source weight bytes after ROM initialization.
    genvar check_bank;
    generate for (check_bank=0; check_bank<5; check_bank=check_bank+1) begin : CHECK_WEIGHT_CONTENT
        reg [7:0] expected_weight [0:783];
        reg [8*128-1:0] weight_filename;
        integer layer, group_number, word_number, length, groups, base, stride, word_total;
        initial begin
            #1;
            word_total=0;
            for (layer=1; layer<=3; layer=layer+1) begin
                length=(layer==1)?784:(layer==2)?30:20;
                groups=(layer==1)?6:(layer==2)?4:2;
                base=(layer==1)?0:(layer==2)?6144:6272;
                stride=(layer==1)?1024:32;
                for (group_number=0; group_number<groups; group_number=group_number+1) begin
                    $sformat(weight_filename,"memory/w_%0d_%0d.mif",layer,group_number*5+check_bank);
                    $readmemb(weight_filename,expected_weight,0,length-1);
                    for (word_number=0; word_number<length; word_number=word_number+1) begin
                        if (device_under_test.weight_sram_instance.WEIGHT_BANK[check_bank].memory[base+group_number*stride+word_number] !== expected_weight[word_number])
                            $fatal(1,"Weight mapping mismatch bank=%0d layer=%0d group=%0d word=%0d",check_bank,layer,group_number,word_number);
                        word_total=word_total+1;
                    end
                end
            end
            $display("WEIGHT_CONTENT_VERIFIED bank=%0d bytes=%0d",check_bank,word_total);
        end
    end endgenerate

    genvar monitor_row, monitor_column;
    generate for (monitor_row=0; monitor_row<5; monitor_row=monitor_row+1) begin : MONITOR_ROW
        for (monitor_column=0; monitor_column<5; monitor_column=monitor_column+1) begin : MONITOR_COL
            wire clear_pe = device_under_test.systolic_controller_instance.systolic_array_2d_instance.ARRAY_ROWS[monitor_row].ARRAY_COLUMNS[monitor_column].pe_systolic_cell_instance.mac_pe_instance.clr;
            wire enable_pe = device_under_test.systolic_controller_instance.systolic_array_2d_instance.ARRAY_ROWS[monitor_row].ARRAY_COLUMNS[monitor_column].pe_systolic_cell_instance.mac_pe_instance.en;
            wire signed [7:0] operand_a = device_under_test.systolic_controller_instance.systolic_array_2d_instance.ARRAY_ROWS[monitor_row].ARRAY_COLUMNS[monitor_column].pe_systolic_cell_instance.mac_pe_instance.a;
            wire signed [7:0] operand_b = device_under_test.systolic_controller_instance.systolic_array_2d_instance.ARRAY_ROWS[monitor_row].ARRAY_COLUMNS[monitor_column].pe_systolic_cell_instance.mac_pe_instance.b;
            wire signed [25:0] actual_acc = device_under_test.systolic_controller_instance.systolic_array_2d_instance.ARRAY_ROWS[monitor_row].ARRAY_COLUMNS[monitor_column].pe_systolic_cell_instance.mac_pe_instance.acc_sum;
            reg signed [25:0] expected_acc;
            assign pe_active[monitor_row*5+monitor_column] = enable_pe;
            always @(posedge clock) begin
                if (!reset_n) expected_acc <= 26'sd0;
                else begin
                    if (actual_acc !== expected_acc) $fatal(1,"MAC numeric mismatch row=%0d col=%0d",monitor_row,monitor_column);
                    if (clear_pe) expected_acc <= 26'sd0;
                    else if (enable_pe) expected_acc <= expected_acc + operand_a*operand_b;
                end
            end
        end
    end endgenerate

    always @(posedge clock) begin
        if (!reset_n) begin
            interrupt_count <= 0;
            total_cycle_count <= 0;
            first_transfer_cycle <= -1;
            axi_backpressure_cycles <= 0;
            previous_intr <= 0;
            previous_stream_stall <= 0;
            previous_read_stall <= 0;
            protocol_errors <= 0;
            peak_active_pe_count <= 0;
            controller_elapsed_cycles <= 0;
            controller_expected_cycles <= 0;
            controller_measurement_active <= 0;
        end else begin
            total_cycle_count <= total_cycle_count+1;
            if (axis_in_data_valid && axis_in_data_ready && first_transfer_cycle < 0)
                first_transfer_cycle <= total_cycle_count;
            if (axis_in_data_valid && !axis_in_data_ready)
                axi_backpressure_cycles <= axi_backpressure_cycles+1;
            if (previous_stream_stall && (!axis_in_data_valid || axis_in_data !== previous_stream_data)) begin
                protocol_errors <= protocol_errors+1;
                $fatal(1,"AXIS data/valid changed under backpressure");
            end
            if (previous_read_stall && (!s_axi_rvalid || s_axi_rdata !== previous_read_data)) begin
                protocol_errors <= protocol_errors+1;
                $fatal(1,"AXI read response changed under backpressure");
            end
            previous_stream_stall <= axis_in_data_valid && !axis_in_data_ready;
            previous_stream_data <= axis_in_data;
            previous_read_stall <= s_axi_rvalid && !s_axi_rready;
            previous_read_data <= s_axi_rdata;
            if (intr) begin
                if (previous_intr) $fatal(1,"intr must be a one-cycle pulse");
                interrupt_count <= interrupt_count+1;
            end
            previous_intr <= intr;
            active_pe_count = 0;
            for (monitor_index=0; monitor_index<25; monitor_index=monitor_index+1)
                if (pe_active[monitor_index]) active_pe_count=active_pe_count+1;
            if (active_pe_count>peak_active_pe_count) peak_active_pe_count<=active_pe_count;
            if (device_under_test.controller_start) begin
                controller_measurement_active <= 1;
                controller_elapsed_cycles <= 0;
                case (device_under_test.layer_index)
                    2'd1: controller_expected_cycles <= 797;
                    2'd2: controller_expected_cycles <= 43;
                    default: controller_expected_cycles <= 33;
                endcase
            end else if (controller_measurement_active) begin
                controller_elapsed_cycles <= controller_elapsed_cycles+1;
                if (device_under_test.controller_done) begin
                    if (controller_elapsed_cycles+1 != controller_expected_cycles)
                        $fatal(1,"controller cycle contract changed");
                    controller_measurement_active <= 0;
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
        $display("PROTOCOL_ERRORS=%0d", protocol_errors);
        $display("PEAK_ACTIVE_PE_COUNT=%0d", peak_active_pe_count);
        if (interrupt_count != TEST_SAMPLE_COUNT/BATCH_SIZE)
            $fatal(1, "interrupt count mismatch: measured=%0d expected=%0d", interrupt_count, TEST_SAMPLE_COUNT/BATCH_SIZE);
        $display("INTERRUPT_COUNT_PER_BATCH=%0d", interrupt_count/(TEST_SAMPLE_COUNT/BATCH_SIZE));
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

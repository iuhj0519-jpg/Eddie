`timescale 1ns/1ps
`include "systolic_parameters.svh"

module unified_buffer (
    input  wire                    clock,
    input  wire                    reset,
    input  wire [`DATA_WIDTH-1:0]  stream_data,
    input  wire                    stream_valid,
    output wire                    stream_ready,
    input  wire                    advance_batch,
    input  wire                    read_input_region,
    input  wire                    read_secondary_region,
    input  wire                    release_input_address,
    input  wire [49:0]             read_address,
    input  wire [4:0]              read_enable,
    output reg  signed [39:0]      read_data,
    output reg  [4:0]              read_valid,
    input  wire [4:0]              activation_write_address,
    input  wire                    write_secondary_region,
    input  wire [39:0]             activation_write_data,
    input  wire                    activation_write_enable,
    output reg                     current_batch_loaded,
    output reg                     next_batch_loaded
);
    localparam integer FEATURE_COUNT      = `INPUT_FEATURE_COUNT;
    localparam integer INTERMEDIATE_COUNT = `LAYER_1_NEURON_COUNT;
    localparam integer SECONDARY_COUNT     = `LAYER_2_NEURON_COUNT;
    localparam integer BANK_DEPTH          = FEATURE_COUNT + INTERMEDIATE_COUNT + SECONDARY_COUNT;
    localparam integer ADDRESS_WIDTH       = 10;

    reg signed [`DATA_WIDTH-1:0] memory_bank_0 [0:BANK_DEPTH-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_1 [0:BANK_DEPTH-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_2 [0:BANK_DEPTH-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_3 [0:BANK_DEPTH-1];
    reg signed [`DATA_WIDTH-1:0] memory_bank_4 [0:BANK_DEPTH-1];

    reg [ADDRESS_WIDTH-1:0] stream_feature_index;
    reg [2:0] stream_image_index;
    reg [ADDRESS_WIDTH:0] consumed_feature_count_0;
    reg [ADDRESS_WIDTH:0] consumed_feature_count_1;
    reg [ADDRESS_WIDTH:0] consumed_feature_count_2;
    reg [ADDRESS_WIDTH:0] consumed_feature_count_3;
    reg [ADDRESS_WIDTH:0] consumed_feature_count_4;

    wire [ADDRESS_WIDTH:0] selected_consumed_feature_count =
        (stream_image_index == 3'd0) ? consumed_feature_count_0 :
        (stream_image_index == 3'd1) ? consumed_feature_count_1 :
        (stream_image_index == 3'd2) ? consumed_feature_count_2 :
        (stream_image_index == 3'd3) ? consumed_feature_count_3 :
                                       consumed_feature_count_4;

    // A following Batch may overwrite only a feature already consumed by Layer 1.
    // Activation writes receive priority so each Bank remains one-read/one-write.
    assign stream_ready = !reset && !activation_write_enable && !next_batch_loaded &&
                          (!current_batch_loaded ||
                           ({1'b0, stream_feature_index} < selected_consumed_feature_count));

    integer lane_index;
    reg [ADDRESS_WIDTH-1:0] selected_read_address;
    always @(posedge clock) begin
        if (reset) begin
            stream_feature_index       <= {ADDRESS_WIDTH{1'b0}};
            stream_image_index         <= 3'd0;
            consumed_feature_count_0   <= {(ADDRESS_WIDTH+1){1'b0}};
            consumed_feature_count_1   <= {(ADDRESS_WIDTH+1){1'b0}};
            consumed_feature_count_2   <= {(ADDRESS_WIDTH+1){1'b0}};
            consumed_feature_count_3   <= {(ADDRESS_WIDTH+1){1'b0}};
            consumed_feature_count_4   <= {(ADDRESS_WIDTH+1){1'b0}};
            current_batch_loaded       <= 1'b0;
            next_batch_loaded          <= 1'b0;
            read_data                  <= 40'd0;
            read_valid                 <= 5'd0;
        end else begin
            read_valid <= read_enable;

            for (lane_index = 0; lane_index < 5; lane_index = lane_index + 1) begin
                if (read_input_region)
                    selected_read_address = read_address[lane_index*10 +: 10];
                else
                    selected_read_address = FEATURE_COUNT +
                                            (read_secondary_region ? INTERMEDIATE_COUNT : 0) +
                                            read_address[lane_index*10 +: 10];

                if (read_enable[lane_index]) begin
                    case (lane_index)
                        0: read_data[7:0]   <= memory_bank_0[selected_read_address];
                        1: read_data[15:8]  <= memory_bank_1[selected_read_address];
                        2: read_data[23:16] <= memory_bank_2[selected_read_address];
                        3: read_data[31:24] <= memory_bank_3[selected_read_address];
                        4: read_data[39:32] <= memory_bank_4[selected_read_address];
                    endcase
                end
            end

            // Layer 1 reuses every feature for all output groups. Release an
            // address only during the final group, after its synchronous read.
            if (read_input_region && release_input_address) begin
                if (read_enable[0] && (consumed_feature_count_0 <= {1'b0, read_address[9:0]}))
                    consumed_feature_count_0 <= {1'b0, read_address[9:0]} + 1'b1;
                if (read_enable[1] && (consumed_feature_count_1 <= {1'b0, read_address[19:10]}))
                    consumed_feature_count_1 <= {1'b0, read_address[19:10]} + 1'b1;
                if (read_enable[2] && (consumed_feature_count_2 <= {1'b0, read_address[29:20]}))
                    consumed_feature_count_2 <= {1'b0, read_address[29:20]} + 1'b1;
                if (read_enable[3] && (consumed_feature_count_3 <= {1'b0, read_address[39:30]}))
                    consumed_feature_count_3 <= {1'b0, read_address[39:30]} + 1'b1;
                if (read_enable[4] && (consumed_feature_count_4 <= {1'b0, read_address[49:40]}))
                    consumed_feature_count_4 <= {1'b0, read_address[49:40]} + 1'b1;
            end

            if (advance_batch) begin
                current_batch_loaded     <= next_batch_loaded;
                next_batch_loaded        <= 1'b0;
                consumed_feature_count_0 <= {(ADDRESS_WIDTH+1){1'b0}};
                consumed_feature_count_1 <= {(ADDRESS_WIDTH+1){1'b0}};
                consumed_feature_count_2 <= {(ADDRESS_WIDTH+1){1'b0}};
                consumed_feature_count_3 <= {(ADDRESS_WIDTH+1){1'b0}};
                consumed_feature_count_4 <= {(ADDRESS_WIDTH+1){1'b0}};
            end

            if (activation_write_enable) begin
                memory_bank_0[FEATURE_COUNT + (write_secondary_region ? INTERMEDIATE_COUNT : 0) + activation_write_address] <= activation_write_data[7:0];
                memory_bank_1[FEATURE_COUNT + (write_secondary_region ? INTERMEDIATE_COUNT : 0) + activation_write_address] <= activation_write_data[15:8];
                memory_bank_2[FEATURE_COUNT + (write_secondary_region ? INTERMEDIATE_COUNT : 0) + activation_write_address] <= activation_write_data[23:16];
                memory_bank_3[FEATURE_COUNT + (write_secondary_region ? INTERMEDIATE_COUNT : 0) + activation_write_address] <= activation_write_data[31:24];
                memory_bank_4[FEATURE_COUNT + (write_secondary_region ? INTERMEDIATE_COUNT : 0) + activation_write_address] <= activation_write_data[39:32];
            end else if (stream_valid && stream_ready) begin
                case (stream_image_index)
                    3'd0: memory_bank_0[stream_feature_index] <= stream_data;
                    3'd1: memory_bank_1[stream_feature_index] <= stream_data;
                    3'd2: memory_bank_2[stream_feature_index] <= stream_data;
                    3'd3: memory_bank_3[stream_feature_index] <= stream_data;
                    default: memory_bank_4[stream_feature_index] <= stream_data;
                endcase

                if (stream_feature_index == FEATURE_COUNT-1) begin
                    stream_feature_index <= {ADDRESS_WIDTH{1'b0}};
                    if (stream_image_index == 3'd4) begin
                        stream_image_index <= 3'd0;
                        if (current_batch_loaded)
                            next_batch_loaded <= 1'b1;
                        else
                            current_batch_loaded <= 1'b1;
                    end else begin
                        stream_image_index <= stream_image_index + 1'b1;
                    end
                end else begin
                    stream_feature_index <= stream_feature_index + 1'b1;
                end
            end
        end
    end
endmodule

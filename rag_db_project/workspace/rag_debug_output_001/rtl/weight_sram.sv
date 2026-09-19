`timescale 1ns/1ps

// Five independent synchronous ROM banks; unchanged MIF data and one-cycle read.
module weight_sram (
    input wire clock,
    input wire [1:0] layer_index,
    input wire [2:0] group_index,
    input wire [49:0] read_address,
    input wire [4:0] read_enable,
    output wire signed [39:0] read_data,
    output reg [4:0] read_valid
);
    always @(posedge clock) read_valid <= read_enable;
    genvar bank_index;
    generate for (bank_index=0; bank_index<5; bank_index=bank_index+1) begin : WEIGHT_BANK
        // L1: six 1024-word slots; L2: four 32-word slots; L3: two 32-word slots.
        (* rom_style = "block", ram_style = "block" *) reg [7:0] memory [0:6335];
        reg [7:0] read_register;
        reg [12:0] bank_address;
        wire [9:0] feature_address = read_address[bank_index*10 +: 10];
        integer init_index;
        initial begin
            for (init_index=0; init_index<6336; init_index=init_index+1)
                memory[init_index] = 8'd0;
            case (bank_index)
                0: begin
                    $readmemb("memory/w_1_0.mif", memory, 0, 783);
                    $readmemb("memory/w_1_5.mif", memory, 1024, 1807);
                    $readmemb("memory/w_1_10.mif", memory, 2048, 2831);
                    $readmemb("memory/w_1_15.mif", memory, 3072, 3855);
                    $readmemb("memory/w_1_20.mif", memory, 4096, 4879);
                    $readmemb("memory/w_1_25.mif", memory, 5120, 5903);
                    $readmemb("memory/w_2_0.mif", memory, 6144, 6173);
                    $readmemb("memory/w_2_5.mif", memory, 6176, 6205);
                    $readmemb("memory/w_2_10.mif", memory, 6208, 6237);
                    $readmemb("memory/w_2_15.mif", memory, 6240, 6269);
                    $readmemb("memory/w_3_0.mif", memory, 6272, 6291);
                    $readmemb("memory/w_3_5.mif", memory, 6304, 6323);
                end
                1: begin
                    $readmemb("memory/w_1_1.mif", memory, 0, 783);
                    $readmemb("memory/w_1_6.mif", memory, 1024, 1807);
                    $readmemb("memory/w_1_11.mif", memory, 2048, 2831);
                    $readmemb("memory/w_1_16.mif", memory, 3072, 3855);
                    $readmemb("memory/w_1_21.mif", memory, 4096, 4879);
                    $readmemb("memory/w_1_26.mif", memory, 5120, 5903);
                    $readmemb("memory/w_2_1.mif", memory, 6144, 6173);
                    $readmemb("memory/w_2_6.mif", memory, 6176, 6205);
                    $readmemb("memory/w_2_11.mif", memory, 6208, 6237);
                    $readmemb("memory/w_2_16.mif", memory, 6240, 6269);
                    $readmemb("memory/w_3_1.mif", memory, 6272, 6291);
                    $readmemb("memory/w_3_6.mif", memory, 6304, 6323);
                end
                2: begin
                    $readmemb("memory/w_1_2.mif", memory, 0, 783);
                    $readmemb("memory/w_1_7.mif", memory, 1024, 1807);
                    $readmemb("memory/w_1_12.mif", memory, 2048, 2831);
                    $readmemb("memory/w_1_17.mif", memory, 3072, 3855);
                    $readmemb("memory/w_1_22.mif", memory, 4096, 4879);
                    $readmemb("memory/w_1_27.mif", memory, 5120, 5903);
                    $readmemb("memory/w_2_2.mif", memory, 6144, 6173);
                    $readmemb("memory/w_2_7.mif", memory, 6176, 6205);
                    $readmemb("memory/w_2_12.mif", memory, 6208, 6237);
                    $readmemb("memory/w_2_17.mif", memory, 6240, 6269);
                    $readmemb("memory/w_3_2.mif", memory, 6272, 6291);
                    $readmemb("memory/w_3_7.mif", memory, 6304, 6323);
                end
                3: begin
                    $readmemb("memory/w_1_3.mif", memory, 0, 783);
                    $readmemb("memory/w_1_8.mif", memory, 1024, 1807);
                    $readmemb("memory/w_1_13.mif", memory, 2048, 2831);
                    $readmemb("memory/w_1_18.mif", memory, 3072, 3855);
                    $readmemb("memory/w_1_23.mif", memory, 4096, 4879);
                    $readmemb("memory/w_1_28.mif", memory, 5120, 5903);
                    $readmemb("memory/w_2_3.mif", memory, 6144, 6173);
                    $readmemb("memory/w_2_8.mif", memory, 6176, 6205);
                    $readmemb("memory/w_2_13.mif", memory, 6208, 6237);
                    $readmemb("memory/w_2_18.mif", memory, 6240, 6269);
                    $readmemb("memory/w_3_3.mif", memory, 6272, 6291);
                    $readmemb("memory/w_3_8.mif", memory, 6304, 6323);
                end
                4: begin
                    $readmemb("memory/w_1_4.mif", memory, 0, 783);
                    $readmemb("memory/w_1_9.mif", memory, 1024, 1807);
                    $readmemb("memory/w_1_14.mif", memory, 2048, 2831);
                    $readmemb("memory/w_1_19.mif", memory, 3072, 3855);
                    $readmemb("memory/w_1_24.mif", memory, 4096, 4879);
                    $readmemb("memory/w_1_29.mif", memory, 5120, 5903);
                    $readmemb("memory/w_2_4.mif", memory, 6144, 6173);
                    $readmemb("memory/w_2_9.mif", memory, 6176, 6205);
                    $readmemb("memory/w_2_14.mif", memory, 6208, 6237);
                    $readmemb("memory/w_2_19.mif", memory, 6240, 6269);
                    $readmemb("memory/w_3_4.mif", memory, 6272, 6291);
                    $readmemb("memory/w_3_9.mif", memory, 6304, 6323);
                end
            endcase
        end
        always @(*) begin
            case (layer_index)
                2'd1: bank_address = {group_index, feature_address};
                2'd2: bank_address = 13'd6144 + {5'd0, group_index, 5'd0} + {8'd0, feature_address[4:0]};
                default: bank_address = 13'd6272 + {5'd0, group_index, 5'd0} + {8'd0, feature_address[4:0]};
            endcase
        end
        always @(posedge clock)
            if (read_enable[bank_index])
                read_register <= memory[bank_address];
        assign read_data[bank_index*8 +: 8] = read_register;
    end endgenerate
endmodule

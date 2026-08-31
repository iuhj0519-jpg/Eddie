`timescale 1ns/1ps

module bias_sram (
    input  wire        clock,
    input  wire [1:0]  layer_index,
    input  wire [2:0]  group_index,
    output reg  signed [39:0] bias_data
);
    reg signed [7:0] layer_1_bias [0:29];
    reg signed [7:0] layer_2_bias [0:19];
    reg signed [7:0] layer_3_bias [0:9];
    integer column_index;
    integer neuron_index;

    initial begin
        $readmemb("memory/b_1_0.mif",  layer_1_bias, 0, 0);   $readmemb("memory/b_1_1.mif",  layer_1_bias, 1, 1);
        $readmemb("memory/b_1_2.mif",  layer_1_bias, 2, 2);   $readmemb("memory/b_1_3.mif",  layer_1_bias, 3, 3);
        $readmemb("memory/b_1_4.mif",  layer_1_bias, 4, 4);   $readmemb("memory/b_1_5.mif",  layer_1_bias, 5, 5);
        $readmemb("memory/b_1_6.mif",  layer_1_bias, 6, 6);   $readmemb("memory/b_1_7.mif",  layer_1_bias, 7, 7);
        $readmemb("memory/b_1_8.mif",  layer_1_bias, 8, 8);   $readmemb("memory/b_1_9.mif",  layer_1_bias, 9, 9);
        $readmemb("memory/b_1_10.mif", layer_1_bias,10,10);   $readmemb("memory/b_1_11.mif", layer_1_bias,11,11);
        $readmemb("memory/b_1_12.mif", layer_1_bias,12,12);   $readmemb("memory/b_1_13.mif", layer_1_bias,13,13);
        $readmemb("memory/b_1_14.mif", layer_1_bias,14,14);   $readmemb("memory/b_1_15.mif", layer_1_bias,15,15);
        $readmemb("memory/b_1_16.mif", layer_1_bias,16,16);   $readmemb("memory/b_1_17.mif", layer_1_bias,17,17);
        $readmemb("memory/b_1_18.mif", layer_1_bias,18,18);   $readmemb("memory/b_1_19.mif", layer_1_bias,19,19);
        $readmemb("memory/b_1_20.mif", layer_1_bias,20,20);   $readmemb("memory/b_1_21.mif", layer_1_bias,21,21);
        $readmemb("memory/b_1_22.mif", layer_1_bias,22,22);   $readmemb("memory/b_1_23.mif", layer_1_bias,23,23);
        $readmemb("memory/b_1_24.mif", layer_1_bias,24,24);   $readmemb("memory/b_1_25.mif", layer_1_bias,25,25);
        $readmemb("memory/b_1_26.mif", layer_1_bias,26,26);   $readmemb("memory/b_1_27.mif", layer_1_bias,27,27);
        $readmemb("memory/b_1_28.mif", layer_1_bias,28,28);   $readmemb("memory/b_1_29.mif", layer_1_bias,29,29);
        $readmemb("memory/b_2_0.mif",  layer_2_bias, 0, 0);   $readmemb("memory/b_2_1.mif",  layer_2_bias, 1, 1);
        $readmemb("memory/b_2_2.mif",  layer_2_bias, 2, 2);   $readmemb("memory/b_2_3.mif",  layer_2_bias, 3, 3);
        $readmemb("memory/b_2_4.mif",  layer_2_bias, 4, 4);   $readmemb("memory/b_2_5.mif",  layer_2_bias, 5, 5);
        $readmemb("memory/b_2_6.mif",  layer_2_bias, 6, 6);   $readmemb("memory/b_2_7.mif",  layer_2_bias, 7, 7);
        $readmemb("memory/b_2_8.mif",  layer_2_bias, 8, 8);   $readmemb("memory/b_2_9.mif",  layer_2_bias, 9, 9);
        $readmemb("memory/b_2_10.mif", layer_2_bias,10,10);   $readmemb("memory/b_2_11.mif", layer_2_bias,11,11);
        $readmemb("memory/b_2_12.mif", layer_2_bias,12,12);   $readmemb("memory/b_2_13.mif", layer_2_bias,13,13);
        $readmemb("memory/b_2_14.mif", layer_2_bias,14,14);   $readmemb("memory/b_2_15.mif", layer_2_bias,15,15);
        $readmemb("memory/b_2_16.mif", layer_2_bias,16,16);   $readmemb("memory/b_2_17.mif", layer_2_bias,17,17);
        $readmemb("memory/b_2_18.mif", layer_2_bias,18,18);   $readmemb("memory/b_2_19.mif", layer_2_bias,19,19);
        $readmemb("memory/b_3_0.mif",  layer_3_bias,0,0);     $readmemb("memory/b_3_1.mif",  layer_3_bias,1,1);
        $readmemb("memory/b_3_2.mif",  layer_3_bias,2,2);     $readmemb("memory/b_3_3.mif",  layer_3_bias,3,3);
        $readmemb("memory/b_3_4.mif",  layer_3_bias,4,4);     $readmemb("memory/b_3_5.mif",  layer_3_bias,5,5);
        $readmemb("memory/b_3_6.mif",  layer_3_bias,6,6);     $readmemb("memory/b_3_7.mif",  layer_3_bias,7,7);
        $readmemb("memory/b_3_8.mif",  layer_3_bias,8,8);     $readmemb("memory/b_3_9.mif",  layer_3_bias,9,9);
    end

    always @(posedge clock) begin
        for (column_index = 0; column_index < 5; column_index = column_index + 1) begin
            neuron_index = group_index * 5 + column_index;
            case (layer_index)
                2'd1: bias_data[column_index*8 +: 8] <= layer_1_bias[neuron_index];
                2'd2: bias_data[column_index*8 +: 8] <= layer_2_bias[neuron_index];
                default: bias_data[column_index*8 +: 8] <= layer_3_bias[neuron_index];
            endcase
        end
    end
endmodule

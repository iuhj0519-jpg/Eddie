`timescale 1ns/1ps

module weight_sram (
    input  wire               clock,
    input  wire [1:0]         layer_index,
    input  wire [2:0]         group_index,
    input  wire [49:0]        read_address,
    input  wire [4:0]         read_enable,
    output reg  signed [39:0] read_data,
    output reg  [4:0]         read_valid
);
    localparam integer LAYER_1_LENGTH = 784;
    localparam integer LAYER_2_LENGTH = 30;
    localparam integer LAYER_3_LENGTH = 20;

    reg signed [7:0] layer_1_weight [0:30*LAYER_1_LENGTH-1];
    reg signed [7:0] layer_2_weight [0:20*LAYER_2_LENGTH-1];
    reg signed [7:0] layer_3_weight [0:10*LAYER_3_LENGTH-1];
    integer column_index;
    integer neuron_index;

    initial begin
        $readmemb("memory/w_1_0.mif",  layer_1_weight, 0*784,  1*784-1);
        $readmemb("memory/w_1_1.mif",  layer_1_weight, 1*784,  2*784-1);
        $readmemb("memory/w_1_2.mif",  layer_1_weight, 2*784,  3*784-1);
        $readmemb("memory/w_1_3.mif",  layer_1_weight, 3*784,  4*784-1);
        $readmemb("memory/w_1_4.mif",  layer_1_weight, 4*784,  5*784-1);
        $readmemb("memory/w_1_5.mif",  layer_1_weight, 5*784,  6*784-1);
        $readmemb("memory/w_1_6.mif",  layer_1_weight, 6*784,  7*784-1);
        $readmemb("memory/w_1_7.mif",  layer_1_weight, 7*784,  8*784-1);
        $readmemb("memory/w_1_8.mif",  layer_1_weight, 8*784,  9*784-1);
        $readmemb("memory/w_1_9.mif",  layer_1_weight, 9*784, 10*784-1);
        $readmemb("memory/w_1_10.mif", layer_1_weight,10*784, 11*784-1);
        $readmemb("memory/w_1_11.mif", layer_1_weight,11*784, 12*784-1);
        $readmemb("memory/w_1_12.mif", layer_1_weight,12*784, 13*784-1);
        $readmemb("memory/w_1_13.mif", layer_1_weight,13*784, 14*784-1);
        $readmemb("memory/w_1_14.mif", layer_1_weight,14*784, 15*784-1);
        $readmemb("memory/w_1_15.mif", layer_1_weight,15*784, 16*784-1);
        $readmemb("memory/w_1_16.mif", layer_1_weight,16*784, 17*784-1);
        $readmemb("memory/w_1_17.mif", layer_1_weight,17*784, 18*784-1);
        $readmemb("memory/w_1_18.mif", layer_1_weight,18*784, 19*784-1);
        $readmemb("memory/w_1_19.mif", layer_1_weight,19*784, 20*784-1);
        $readmemb("memory/w_1_20.mif", layer_1_weight,20*784, 21*784-1);
        $readmemb("memory/w_1_21.mif", layer_1_weight,21*784, 22*784-1);
        $readmemb("memory/w_1_22.mif", layer_1_weight,22*784, 23*784-1);
        $readmemb("memory/w_1_23.mif", layer_1_weight,23*784, 24*784-1);
        $readmemb("memory/w_1_24.mif", layer_1_weight,24*784, 25*784-1);
        $readmemb("memory/w_1_25.mif", layer_1_weight,25*784, 26*784-1);
        $readmemb("memory/w_1_26.mif", layer_1_weight,26*784, 27*784-1);
        $readmemb("memory/w_1_27.mif", layer_1_weight,27*784, 28*784-1);
        $readmemb("memory/w_1_28.mif", layer_1_weight,28*784, 29*784-1);
        $readmemb("memory/w_1_29.mif", layer_1_weight,29*784, 30*784-1);

        $readmemb("memory/w_2_0.mif",  layer_2_weight, 0*30,  1*30-1);
        $readmemb("memory/w_2_1.mif",  layer_2_weight, 1*30,  2*30-1);
        $readmemb("memory/w_2_2.mif",  layer_2_weight, 2*30,  3*30-1);
        $readmemb("memory/w_2_3.mif",  layer_2_weight, 3*30,  4*30-1);
        $readmemb("memory/w_2_4.mif",  layer_2_weight, 4*30,  5*30-1);
        $readmemb("memory/w_2_5.mif",  layer_2_weight, 5*30,  6*30-1);
        $readmemb("memory/w_2_6.mif",  layer_2_weight, 6*30,  7*30-1);
        $readmemb("memory/w_2_7.mif",  layer_2_weight, 7*30,  8*30-1);
        $readmemb("memory/w_2_8.mif",  layer_2_weight, 8*30,  9*30-1);
        $readmemb("memory/w_2_9.mif",  layer_2_weight, 9*30, 10*30-1);
        $readmemb("memory/w_2_10.mif", layer_2_weight,10*30, 11*30-1);
        $readmemb("memory/w_2_11.mif", layer_2_weight,11*30, 12*30-1);
        $readmemb("memory/w_2_12.mif", layer_2_weight,12*30, 13*30-1);
        $readmemb("memory/w_2_13.mif", layer_2_weight,13*30, 14*30-1);
        $readmemb("memory/w_2_14.mif", layer_2_weight,14*30, 15*30-1);
        $readmemb("memory/w_2_15.mif", layer_2_weight,15*30, 16*30-1);
        $readmemb("memory/w_2_16.mif", layer_2_weight,16*30, 17*30-1);
        $readmemb("memory/w_2_17.mif", layer_2_weight,17*30, 18*30-1);
        $readmemb("memory/w_2_18.mif", layer_2_weight,18*30, 19*30-1);
        $readmemb("memory/w_2_19.mif", layer_2_weight,19*30, 20*30-1);

        $readmemb("memory/w_3_0.mif", layer_3_weight,0*20,  1*20-1);
        $readmemb("memory/w_3_1.mif", layer_3_weight,1*20,  2*20-1);
        $readmemb("memory/w_3_2.mif", layer_3_weight,2*20,  3*20-1);
        $readmemb("memory/w_3_3.mif", layer_3_weight,3*20,  4*20-1);
        $readmemb("memory/w_3_4.mif", layer_3_weight,4*20,  5*20-1);
        $readmemb("memory/w_3_5.mif", layer_3_weight,5*20,  6*20-1);
        $readmemb("memory/w_3_6.mif", layer_3_weight,6*20,  7*20-1);
        $readmemb("memory/w_3_7.mif", layer_3_weight,7*20,  8*20-1);
        $readmemb("memory/w_3_8.mif", layer_3_weight,8*20,  9*20-1);
        $readmemb("memory/w_3_9.mif", layer_3_weight,9*20, 10*20-1);
    end

    always @(posedge clock) begin
        read_valid <= read_enable;
        for (column_index = 0; column_index < 5; column_index = column_index + 1) begin
            neuron_index = group_index * 5 + column_index;
            if (read_enable[column_index]) begin
                case (layer_index)
                    2'd1: read_data[column_index*8 +: 8] <= layer_1_weight[neuron_index*LAYER_1_LENGTH + read_address[column_index*10 +: 10]];
                    2'd2: read_data[column_index*8 +: 8] <= layer_2_weight[neuron_index*LAYER_2_LENGTH + read_address[column_index*10 +: 10]];
                    default: read_data[column_index*8 +: 8] <= layer_3_weight[neuron_index*LAYER_3_LENGTH + read_address[column_index*10 +: 10]];
                endcase
            end
        end
    end
endmodule

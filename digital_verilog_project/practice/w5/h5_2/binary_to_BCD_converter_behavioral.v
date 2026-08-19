module binary_to_BCD_converter_behavioral_module (
    input [3:0] four_bit_binary,
    output reg [9:0] BCD_code
);
    always @(four_bit_binary) begin
        case (four_bit_binary)
            4'b0000: BCD_code <= 10'b00_0000_0000;
            4'b0001: BCD_code <= 10'b00_0000_0001;
            4'b0010: BCD_code <= 10'b00_0000_0010;
            4'b0011: BCD_code <= 10'b00_0000_0011;
            4'b0100: BCD_code <= 10'b00_0000_0100;
            4'b0101: BCD_code <= 10'b00_0000_0101;
            4'b0110: BCD_code <= 10'b00_0000_0110;
            4'b0111: BCD_code <= 10'b00_0000_0111;
            4'b1000: BCD_code <= 10'b00_0000_1000;
            4'b1001: BCD_code <= 10'b00_0000_1001;
            4'b1010: BCD_code <= 10'b00_0001_0000;
            4'b1011: BCD_code <= 10'b00_0001_0001;
            4'b1100: BCD_code <= 10'b00_0001_0010;
            4'b1101: BCD_code <= 10'b00_0001_0011;
            4'b1110: BCD_code <= 10'b00_0001_0100;
            4'b1111: BCD_code <= 10'b00_0001_0101;
            default: BCD_code <= 10'b00_0000_0000;
        endcase
    end
endmodule
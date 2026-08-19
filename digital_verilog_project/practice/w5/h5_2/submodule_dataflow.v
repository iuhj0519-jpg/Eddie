module submodule_dataflow_module (
    input [3:0] in,
    output [3:0] out
);
    assign out = (in<4'd4 || in==4'd4) ? in : (in==4'd5) ? 4'b1000 : (in==4'd6) ? 4'b1001 : (in==4'd7) ? 4'b1010 : (in==4'd8) ? 4'b1011 : (in==4'd9) ? 4'b1100 : 4'b0000;
endmodule
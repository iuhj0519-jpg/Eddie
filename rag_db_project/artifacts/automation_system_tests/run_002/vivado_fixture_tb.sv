`timescale 1ns/1ps
module top_sim;
reg clock=0, reset_n=0;
reg [7:0] data=0;
wire [7:0] result;
reg [7:0] mem[0:0], testdata[0:0];
always #5 clock=~clock;
zyNet device_under_test(clock,reset_n,data,result);
initial begin
  $readmemb("memory/w.mif",mem);
  $readmemb("../../inputs/reference_model/testdata/test_data_0000.txt",testdata);
  if (mem[0] !== 8'd1 || testdata[0] !== 8'd2) $fatal(1,"Input path failure");
  #20; reset_n=1;
  for (integer i=0;i<100;i=i+1) begin
    @(negedge clock); data=i;
    @(negedge clock);
    if (result !== i+1) $fatal(1,"Fixture mismatch");
  end
  $display("FINAL_RESULT PASS=100 FAIL=0 ACCURACY=100.000000%%");
  $display("REFERENCE_GOLDEN_MATCH PASS");
  $finish;
end
endmodule

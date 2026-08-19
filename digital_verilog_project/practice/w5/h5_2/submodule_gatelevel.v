module submodule_gatelevel_module (
    input in3, in2, in1, in0,
    output out3, out2, out1, out0
);
    /*
    *** Note ***
    Boolean expression: Sum Of Products (SOP)
    in3 = A, in2 = B, in1 = C, in0 = D
    out3 = A+BD+BC
    out2 = AD+BC'D'
    out1 = AD'+B'C+CD
    out0 = AD'+A'B'D+BCD'
    */

    wire not_1_out, not_2_out, not_3_out, not_4_out, not_5_out;
    wire and_1_out, and_2_out, and_3_out, and_4_out, and_5_out, and_6_out, and_7_out, and_8_out, and_9_out, and_10_out;
    wire or_1_out, or_2_out;

    not_gate not_1(.a(in3), .out(not_1_out)); // A'
    not_gate not_2(.a(in2), .out(not_2_out)); // B'
    not_gate not_3(.a(in1), .out(not_3_out)); // C'
    not_gate not_4(.a(in0), .out(not_4_out)); // D'

    // out3 A+BD+BC
    and_gate and_1(.a(in2), .b(in1), .out(and_1_out)); // BC
    and_gate and_2(.a(in2), .b(in0), .out(and_2_out)); // BD
    or_gate or_1(.a(in3), .b(and_1_out), .out(or_1_out)); // A+BC
    or_gate or_2(.a(or_1_out), .b(and_2_out), .out(out3));

    // out2 AD+BC'D'
    and_gate and_3(.a(in3), .b(in0), .out(and_3_out)); // AD
    and_gate and_4(.a(in2), .b(not_4_out), .out(and_4_out)); // BD'
    and_gate and_5(.a(and_4_out), .b(not_3_out), .out(and_5_out)); // BC'D'
    or_gate or_3(.a(and_3_out), .b(and_5_out), .out(out2));

    // out1 AD'+B'C+CD
    // Fill this out
    and_gate and_6(.a(not_4_out), .b(in3), .out(and_6_out)); // AD'
    not_gate not_5(.a(and_4_out), .out(not_5_out)); // B'+D
    and_gate and_7(.a(not_5_out), .b(in1), .out(and_7_out)); // B'C+CD
    or_gate or_4(.a(and_7_out), .b(and_6_out), .out(out1));

    // out0 AD'+BCD'+A'B'D
    // Fill this out
    and_gate and_8(.a(and_1_out), .b(not_4_out), .out(and_8_out)); // BCD'
    or_gate or_5(.a(and_8_out), .b(and_6_out), .out(or_2_out)); // AD'+BCD'
    and_gate and_9(.a(not_1_out), .b(not_2_out), .out(and_9_out)); // A'B'
    and_gate and_10(.a(and_9_out), .b(in0), .out(and_10_out)); // A'B'D
    or_gate or_6(.a(or_2_out), .b(and_10_out), .out(out0));
    
endmodule
module second_binary_top (
    input logic clk, rst,
    input logic signed [31:0] raw,
    output logic pdm
);
    gndless_fixedpoint___FixedPointValue__gndless_fixedpoint_Q1_31 audio();
    logic signed [31:0] sample;
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) sample <= 0;
        else sample <= raw;
    end
    assign audio.raw = sample;
    gndless_delta_sigma_DeltaSigma2nd dut(.clk(clk),.rst(rst),.audio(audio),.pdm(pdm));
endmodule

module second_ternary_top (
    input logic clk, rst,
    input logic signed [31:0] raw,
    output logic pdm_p, pdm_n
);
    gndless_fixedpoint___FixedPointValue__gndless_fixedpoint_Q1_31 audio();
    logic signed [31:0] sample;
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) sample <= 0;
        else sample <= raw;
    end
    assign audio.raw = sample;
    gndless_delta_sigma_DeltaSigma2ndTernary dut(.clk(clk),.rst(rst),.audio(audio),.pdm_p(pdm_p),.pdm_n(pdm_n));
endmodule

`timescale 1ns / 1ps


`define MaxTestSamples 100

module top_sim(

    );

    localparam int DATA_W = npu_param_pkg::DATA_W;                         // 추가
    localparam int BATCH_SIZE = npu_param_pkg::BATCH_SIZE;                 // 추가
    localparam int INPUT_DATA_SIZE = npu_param_pkg::INPUT_DATA_SIZE;       // 추가
    localparam int AXI_DATA_WIDTH = 32;                                    // 추가
    localparam int AXI_ADDR_WIDTH = 32;                                    // 추가
    localparam [AXI_ADDR_WIDTH-1:0] CONTROL_ADDRESS = 32'd28;              // 추가

    reg reset;
    reg clock;
    reg [DATA_W-1:0] in;
    reg in_valid;
    reg [DATA_W-1:0] in_mem [INPUT_DATA_SIZE:0];
    reg [25*7:0] fileName;
    reg s_axi_awvalid;
    reg [31:0] s_axi_awaddr;
    wire s_axi_awready;
    reg [31:0] s_axi_wdata;
    reg s_axi_wvalid;
    wire s_axi_wready;
    wire s_axi_bvalid;
    reg s_axi_bready;
    wire intr;
    reg [31:0] axiRdData;
    reg [31:0] s_axi_araddr;
    wire [31:0] s_axi_rdata;
    reg s_axi_arvalid;
    wire s_axi_arready;
    wire s_axi_rvalid;
    reg s_axi_rready;
    reg [DATA_W-1:0] expected;

    wire in_ready;                                                         // 추가
    reg [DATA_W-1:0] expected_batch [0:BATCH_SIZE-1];                      // 추가
    reg [31:0] detected_batch [0:BATCH_SIZE-1];                            // 추가

    // Weight/Bias_SRAM이 MIF 파일을 직접 로드하기 때문에 필요 없는 변수
    /*
    wire [31:0] numNeurons[31:1];
    wire [31:0] numWeights[31:1];

    assign numNeurons[1] = 30;
    assign numNeurons[2] = 30;
    assign numNeurons[3] = 10;
    assign numNeurons[4] = 10;

    assign numWeights[1] = 784;
    assign numWeights[2] = 30;
    assign numWeights[3] = 30;
    assign numWeights[4] = 10;
    */

    integer right=0;
    integer wrong=0;
    integer batch_start_index;                                             // 추가
    integer image_index;                                                   // 추가
    integer total_tested;                                                  // 추가

    zyNet #(
    .C_S_AXI_DATA_WIDTH(AXI_DATA_WIDTH),                                   // 추가
    .C_S_AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),                                   // 추가
    .DATA_W(DATA_W),                                                       // 추가
    .BATCH_SIZE(BATCH_SIZE)                                                // 추가
    ) dut(
    .s_axi_aclk(clock),
    .s_axi_aresetn(reset),
    .s_axi_awaddr(s_axi_awaddr),
    .s_axi_awprot(0),
    .s_axi_awvalid(s_axi_awvalid),
    .s_axi_awready(s_axi_awready),
    .s_axi_wdata(s_axi_wdata),
    .s_axi_wstrb(4'hF),
    .s_axi_wvalid(s_axi_wvalid),
    .s_axi_wready(s_axi_wready),
    .s_axi_bresp(),
    .s_axi_bvalid(s_axi_bvalid),
    .s_axi_bready(s_axi_bready),
    .s_axi_araddr(s_axi_araddr),
    .s_axi_arprot(0),
    .s_axi_arvalid(s_axi_arvalid),
    .s_axi_arready(s_axi_arready),
    .s_axi_rdata(s_axi_rdata),
    .s_axi_rresp(),
    .s_axi_rvalid(s_axi_rvalid),
    .s_axi_rready(s_axi_rready),
    .axis_in_data(in),
    .axis_in_data_valid(in_valid),
    // .axis_in_data_ready(),                                              // 기존
    .axis_in_data_ready(in_ready),                                         // 추가
    .intr(intr)
    );

    initial
    begin
        clock = 1'b0;
        s_axi_awvalid = 1'b0;
        s_axi_bready = 1'b0;
        s_axi_wvalid = 1'b0;
        s_axi_arvalid = 1'b0;
    end

    always
        #5 clock = ~clock;

    function [7:0] to_ascii;
      input integer a;
      begin
        to_ascii = a+48;
      end
    endfunction

    always @(posedge clock)
    begin
        s_axi_bready <= s_axi_bvalid;
        s_axi_rready <= s_axi_rvalid;
    end

    task writeAxi(
    input [31:0] address,
    input [31:0] data
    );
    begin
        @(posedge clock);
        s_axi_awvalid <= 1'b1;
        s_axi_awaddr <= address;
        s_axi_wdata <= data;
        s_axi_wvalid <= 1'b1;
        wait(s_axi_wready);
        @(posedge clock);
        s_axi_awvalid <= 1'b0;
        s_axi_wvalid <= 1'b0;
        @(posedge clock);
    end
    endtask

    task readAxi(
    input [31:0] address
    );
    begin
        @(posedge clock);
        s_axi_arvalid <= 1'b1;
        s_axi_araddr <= address;
        wait(s_axi_arready);
        @(posedge clock);
        s_axi_arvalid <= 1'b0;
        wait(s_axi_rvalid);
        @(posedge clock);
        axiRdData <= s_axi_rdata;
        @(posedge clock);
    end
    endtask

    // 기존: Weight_SRAM이 MIF 파일을 직접 읽으므로 실행하지 않지만 삭제하지 않음
    /*
    task configWeights();
    integer i,j,k,t;
    integer neuronNo_int;
    reg [DATA_W:0] config_mem [783:0];
    begin
        @(posedge clock);
        for(k=1;k<=3;k=k+1)
        begin
            writeAxi(12,k);
            for(j=0;j<numNeurons[k];j=j+1)
            begin
                neuronNo_int = j;
                fileName[0] = "f";
                fileName[1] = "i";
                fileName[2] = "m";
                fileName[3] = ".";
                if(j > 9)
                begin
                    fileName[4] = 48;
                    fileName[5] = 48;
                    i=0;
                    while(neuronNo_int != 0)
                    begin
                        fileName[i+4] = to_ascii(neuronNo_int%10);
                        neuronNo_int = neuronNo_int/10;
                        i=i+1;
                    end
                    fileName[6] = "_";
                    fileName[7] = to_ascii(k);
                    fileName[8] = "_";
                    fileName[9] = "w";
                end
                else
                begin
                    fileName[4] = 48;
                    i=0;
                    while(neuronNo_int != 0)
                    begin
                        fileName[i+4] = to_ascii(neuronNo_int%10);
                        neuronNo_int = neuronNo_int/10;
                        i=i+1;
                    end
                    fileName[5] = "_";
                    fileName[6] = to_ascii(k);
                    fileName[7] = "_";
                    fileName[8] = "w";
                end
                $readmemb(fileName, config_mem);
                writeAxi(16,j);
                for (t=0; t<numWeights[k]; t=t+1)
                    writeAxi(0,{15'd0,config_mem[t]});
            end
        end
    end
    endtask

    // 기존: Bias_SRAM이 MIF 파일을 직접 읽으므로 실행하지 않지만 삭제하지 않음
    task configBias();
    integer i,j,k,t;
    integer neuronNo_int;
    reg [31:0] bias[0:0];
    begin
        @(posedge clock);
        for(k=1;k<=3;k=k+1)
        begin
            writeAxi(12,k);
            for(j=0;j<numNeurons[k];j=j+1)
            begin
                neuronNo_int = j;
                fileName[0] = "f";
                fileName[1] = "i";
                fileName[2] = "m";
                fileName[3] = ".";
                if(j>9)
                begin
                    fileName[4] = 48;
                    fileName[5] = 48;
                    i=0;
                    while(neuronNo_int != 0)
                    begin
                        fileName[i+4] = to_ascii(neuronNo_int%10);
                        neuronNo_int = neuronNo_int/10;
                        i=i+1;
                    end
                    fileName[6] = "_";
                    fileName[7] = to_ascii(k);
                    fileName[8] = "_";
                    fileName[9] = "b";
                end
                else
                begin
                    fileName[4] = 48;
                    i=0;
                    while(neuronNo_int != 0)
                    begin
                        fileName[i+4] = to_ascii(neuronNo_int%10);
                        neuronNo_int = neuronNo_int/10;
                        i=i+1;
                    end
                    fileName[5] = "_";
                    fileName[6] = to_ascii(k);
                    fileName[7] = "_";
                    fileName[8] = "b";
                end
                $readmemb(fileName, bias);
                writeAxi(16,j);
                writeAxi(4,{15'd0,bias[0]});
            end
        end
    end
    endtask
    */

    task sendData();
    integer t;
    begin
        $readmemb(fileName, in_mem);
        @(posedge clock);
        @(posedge clock);
        @(posedge clock);
        for (t=0; t<INPUT_DATA_SIZE; t=t+1) begin
            @(posedge clock);
            in <= in_mem[t];
            in_valid <= 1;
            wait(in_ready);                                                  // 추가
        end
        @(posedge clock);
        in_valid <= 0;
        expected = in_mem[t];
        expected_batch[image_index] = in_mem[t];                             // 추가
    end
    endtask

    integer i,j,layerNo=1,k;
    integer start;
    integer testDataCount;
    integer testDataCount_int;
    reg[7:0] fileNum [3:0];
    initial
    begin
        reset = 0;
        in_valid = 0;
        total_tested = 0;                                                     // 추가
        #100;
        reset = 1;
        #100
        writeAxi(CONTROL_ADDRESS,0); //clear soft reset                       // 변경: 주소만 기존 28과 동일한 이름 사용
        start = $time;
        `ifndef pretrained
            // configWeights();                                               // 기존: MIF 기반 SRAM 사용으로 주석 처리
            // configBias();                                                  // 기존: MIF 기반 SRAM 사용으로 주석 처리
        `endif
        $display("Configuration completed",,,,$time-start,,"ns");
        start = $time;
        // for(testDataCount=0;testDataCount<`MaxTestSamples;testDataCount=testDataCount+1) // 기존
        for(batch_start_index=0;batch_start_index<`MaxTestSamples;batch_start_index=batch_start_index+BATCH_SIZE) // 추가
        begin
            writeAxi(CONTROL_ADDRESS,32'h0000_0002);                          // 추가: image_batch_start = 1
            writeAxi(CONTROL_ADDRESS,32'h0000_0000);                          // 추가: image_batch_start = 0

            for(image_index=0;image_index<BATCH_SIZE;image_index=image_index+1) // 추가
            begin
                testDataCount = batch_start_index + image_index;              // 추가
                testDataCount_int = testDataCount;
                fileName = "test_data_";

                for (i = 0; i < 4; i = i + 1)
                begin
                    fileNum[i] = 8'b0; // Initialize each register to 0
                end

                i=0;
                while(testDataCount_int != 0)
                begin
                    fileNum[i] = (testDataCount_int%10);
                    testDataCount_int = testDataCount_int/10;
                    i=i+1;
                end

                for (i = 4; i > 0; i = i-1)
                begin
                    if (fileNum[i - 1] == 0)
                    begin
                        fileName = {fileName, "0"};
                    end
                    else
                    begin
                        fileName = {fileName, to_ascii(fileNum[i - 1])};
                    end
                end

                fileName = {fileName, ".txt"};

                $display("Filename: %s",fileName);
                sendData();
            end

            // @(posedge intr);                                               // 기존 : 한 이미지 처리 방식
            wait(intr === 1'b1);                                              // 추가 : 5-image batch 결과 대기

            for(image_index=0;image_index<BATCH_SIZE;image_index=image_index+1) // 추가
            begin
                readAxi(8 + image_index*4);                                   // 추가 : 결과 레지스터 5개 순차 읽기
                detected_batch[image_index] = axiRdData;                      // 추가
                total_tested = total_tested + 1;                              // 추가
                if(axiRdData==expected_batch[image_index])
                begin
                    right = right+1;
                    $display("PASS %0d: detected=%0d expected=%0d",
                             batch_start_index+image_index,
                             axiRdData,expected_batch[image_index]);
                end
                else
                begin
                    wrong = wrong+1;
                    $display("FAIL %0d: detected=%0d expected=%0d",
                             batch_start_index+image_index,
                             axiRdData,expected_batch[image_index]);
                end
            end

            $display("Batch %0d complete, accuracy=%0f%%",
                     batch_start_index/BATCH_SIZE,
                     right*100.0/total_tested);                               // 추가

            writeAxi(CONTROL_ADDRESS,32'h0000_0004);                          // 추가 : image_batch_result_ready = 1 (Testbench가 5개 결과 모두 읽음)
            writeAxi(CONTROL_ADDRESS,32'h0000_0000);                          // 추가 : ready 해제
            wait(intr === 1'b0);                                              // 추가

            /*
            // 기존: 단일 결과 비교 방식은 5-image batch 구조에서 사용하지 않지만 삭제하지 않음
            readAxi(8);
            if(axiRdData==expected)
                right = right+1;
            $display("%0d. Accuracy: %f, Detected number: %0x, Expected: %x",
                     testDataCount+1,right*100.0/(testDataCount+1),axiRdData,expected);
            */
        end
        $display("====================================================");     // 추가
        $display("Total=%0d PASS=%0d FAIL=%0d Accuracy=%0f%%",
                 total_tested,right,wrong,right*100.0/total_tested);          // 추가
        $display("====================================================");     // 추가
        // $display("Accuracy: %f",right*100.0/testDataCount);                // 기존
        // $stop;                                                             // 기존
        $finish;                                                              // 추가
    end

endmodule

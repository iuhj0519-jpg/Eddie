package npu_param_pkg;
  parameter int DATA_W                 = 8;
  parameter int ACC_W                  = 2 * DATA_W + $clog2(784);
  parameter int BATCH_SIZE             = 5;
  parameter int ARRAY_SIZE             = 5;
  parameter int INPUT_DATA_SIZE        = 784;
  parameter int OUTPUT_CLASS_COUNT     = 10;

  parameter int LAYER1_INPUT_SIZE      = 784;
  parameter int LAYER1_OUTPUT_SIZE     = 30;
  parameter int LAYER2_INPUT_SIZE      = 30;
  parameter int LAYER2_OUTPUT_SIZE     = 20;
  parameter int LAYER3_INPUT_SIZE      = 20;
  parameter int LAYER3_OUTPUT_SIZE     = 10;

  parameter int GLOBAL_BUFFER_DEPTH    = LAYER1_OUTPUT_SIZE;
  parameter int SRAM_READ_LATENCY      = 1;
  parameter int SIGMOID_ADDRESS_WIDTH  = 10;
  parameter int WEIGHT_INTEGER_WIDTH   = 1;

  parameter int INPUT_ADDRESS_WIDTH = $clog2(INPUT_DATA_SIZE);
  parameter int GLOBAL_BUFFER_ADDRESS_WIDTH = $clog2(GLOBAL_BUFFER_DEPTH);
  parameter int IMAGE_INDEX_WIDTH = $clog2(BATCH_SIZE);
  parameter int LAYER_INDEX_WIDTH = 2;
  parameter int GROUP_INDEX_WIDTH = $clog2((LAYER1_OUTPUT_SIZE / ARRAY_SIZE) + 1);
  parameter int COLUMN_INDEX_WIDTH = $clog2(ARRAY_SIZE);
  parameter int COUNTER_WIDTH =
      $clog2(LAYER1_INPUT_SIZE + (2 * ARRAY_SIZE) + SRAM_READ_LATENCY + 4);
endpackage

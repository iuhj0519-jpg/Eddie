# Systolic Prototype Implementation And Verification

## Evidence Boundary

- T0: `REFERENCE_MODEL_SPECIFICATION.md`, `SYSTOLIC_ACCELERATOR_SPECIFICATION.md`
- T1: 승인된 Reference Model RTL
- Direct Source: 승인된 Weight, Bias, Sigmoid LUT, Test Vector
- Excluded: `historical_baselines/**`, 외부 Web, 외부 LLM/API
- Requirement Coverage: `REQ-SYS-001`~`REQ-SYS-029`의 구현 및 Test 항목 PASS

## Requirement To Module Mapping

| Concern | Implementation | Primary Requirements |
|---|---|---|
| 5×5 Output-Stationary Array | `mac_pe.sv`, `pe_systolic_cell.sv`, `systolic_array_2d.sv` | REQ-SYS-001, 002, 012, 013, 027 |
| Image-Major Batch Input | `input_buffer.sv` | REQ-SYS-003, 004 |
| Layer 1/2 Ping-Pong | `global_buffer.sv` | REQ-SYS-005, 006, 007 |
| SRAM Streaming/Skew/Handshake | `systolic_controller.sv`, `input_buffer.sv`, `global_buffer.sv`, `weight_sram.sv` | REQ-SYS-008, 011, 016, 017, 028 |
| Fixed-Point/Saturation/LUT | `activation_unit.sv` | REQ-SYS-014, 015, 019, 026 |
| Direct Layer 3 Classification | `maxFinder.sv` | REQ-SYS-007, REQ-REF-007, REQ-SYS-029 |
| AXI Result/Interrupt | `axi_lite_wrapper.sv`, `zyNet.sv` | REQ-SYS-020~024, 029 |

## ModelSim Result

- Simulator: ModelSim Intel FPGA Edition 10.5b
- Compile: 0 Errors, 0 Warnings
- Test Set: 100 MNIST Samples, 20 Batches, 5 Images per Batch
- Result: 99 PASS, 1 FAIL
- Accuracy: 99.000000%
- Known Failure: Sample 18, Detected 8, Expected 3
- Reference Golden Match: PASS
- Controller Cycle Assertions: 797/43/33 PASS
- Interrupt Assertions: Batch당 1-Cycle, 총 20회 PASS
- Matrix Register Duplication: `latched_mat_a`, `latched_mat_b` 및 동등한 전체 Matrix Register 없음

전체 Transcript는 실행 시 `reports/modelsim_transcript.log`에 생성된다. ModelSim Work Library 파일은 실행 Artifact이며 설계 Source가 아니다.

## Verification Scope

이번 결과는 RTL Compile, Elaboration, 100-Sample Functional Simulation을 통과했다. FPGA Synthesis, Timing Closure, On-Board Validation은 아직 수행하지 않았으므로 해당 항목은 Verified로 간주하지 않는다.

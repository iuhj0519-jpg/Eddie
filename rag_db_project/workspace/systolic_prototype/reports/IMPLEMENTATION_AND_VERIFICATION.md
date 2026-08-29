# Systolic Prototype Implementation And Verification

## Evidence Boundary

- T0: `REFERENCE_MODEL_SPECIFICATION.md`, `SYSTOLIC_ACCELERATOR_SPECIFICATION.md`
- T1: 승인된 Reference Model RTL
- Direct Source: 승인된 Weight, Bias, Sigmoid LUT, Test Vector
- Excluded: `historical_baselines/**`, 외부 Web, 외부 LLM/API
- Requirement Coverage: 39/39 PASS

## Requirement To Module Mapping

| Concern | Implementation | Primary Requirements |
|---|---|---|
| 5×5 Output-Stationary Array | `processing_element.sv`, `systolic_array.sv` | REQ-SYS-001, 002, 012, 013 |
| Image-Major Batch Input | `input_buffer.sv` | REQ-SYS-003, 004 |
| Layer 1/2 Ping-Pong | `global_buffer.sv` | REQ-SYS-005, 006, 007 |
| Scheduler/Handshake | `dnn_scheduler.sv`, `systolic_controller.sv` | REQ-SYS-008, 011, 016, 017 |
| Fixed-Point/Saturation/LUT | `activation_unit.sv` | REQ-SYS-014, 015, 019, 026 |
| Direct Layer 3 Classification | `max_finder.sv` | REQ-SYS-007, REQ-REF-007 |
| AXI Result/Interrupt | `axi_lite_result_interface.sv`, `zyNet.sv` | REQ-SYS-020~024 |

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

전체 Transcript는 실행 시 `reports/modelsim_transcript.log`에 생성된다. ModelSim Work Library 파일은 실행 Artifact이며 설계 Source가 아니다.

## Verification Scope

이번 결과는 RTL Compile, Elaboration, 100-Sample Functional Simulation을 통과했다. FPGA Synthesis, Timing Closure, On-Board Validation은 아직 수행하지 않았으므로 해당 항목은 Verified로 간주하지 않는다.

# Optimized Accelerator Implementation And Verification

## Evidence Boundary

설계에는 승인된 세 SPEC, 승인된 Reference RTL, `prototype_generation/run_002`에서 검증된 Systolic Prototype만 사용했다. 외부 Web, 외부 LLM/API와 차단 대상 디렉터리는 설계 근거로 사용하지 않았다. Requirement와 검색 Chunk의 연결은 `experiments/optimization_generation/run_001`에 고정되어 있다.

## Unified Buffer Candidate Comparison

| Candidate | Bank당 byte | 전체 byte | 장점 | 단점 |
|---|---:|---:|---|---|
| Double-Batch Storage | 1,598 | 7,990 | 단순한 소유권과 최대 prefetch 자유도 | 용량과 BRAM 낭비가 큼 |
| Lifetime-Reuse Storage | 834 | 4,170 | 읽기가 끝난 주소를 순차 재사용하고 중간결과 ping-pong 보존 | ready/주소 제어가 추가됨 |

Lifetime-Reuse Storage를 선택했다. Bank당 784-byte 입력영역, 30-byte Layer 1 결과영역, 20-byte Layer 2 결과영역으로 구성한다. Layer 1은 입력을 여섯 output group에서 재사용하므로 마지막 group의 synchronous read 이후에만 주소를 해제한다. 이 조건이 만족되지 않으면 AXI Stream에 backpressure를 건다.

Prototype의 분리형 논리용량은 Input 3,920 byte와 Global 300 byte로 총 4,220 byte이다. 최적화 구조는 총 4,170 byte로 50 byte(약 1.18%) 감소한다. 분리된 15개 RTL memory array를 5개 Bank Array로 통합하므로 FPGA BRAM packing에는 유리할 가능성이 있으나 실제 BRAM Block 수는 Quartus 합성으로 확인해야 한다.

## Unified Buffer Disadvantage Mitigation

- Port contention: Activation write에 우선순위를 주고 AXI write를 정지시켜 Bank당 최대 1-read/1-write로 제한한다.
- Data corruption: Layer 1 마지막 group에서만 소비주소를 반환하고 Layer 1/2 결과영역을 분리한다.
- Address MUX: Region 선택은 상수 offset 두 개와 Layer 신호만 사용한다.
- Ready critical path: Bank별 단조 증가 consumed counter와 현재 stream Bank 비교만 수행한다.
- Capacity growth: 전체 다음 Batch 복제 대신 수명이 끝난 입력주소를 재사용한다.

## AXI Latency Hiding

첫 Batch는 5×784 data를 모두 받은 뒤 compute를 시작한다. 이후에는 마지막 Layer 1 group에서 반환되는 입력주소부터 다음 Batch를 받으며, Layer 2/3 compute 동안 가능한 범위까지 prefetch한다. 다음 Batch 전체가 완료되지 않았으면 남은 data에 대해서만 IDLE에서 기다린다. 따라서 기능 안정성을 위해 필요한 backpressure는 남지만, 첫 Batch 이후의 AXI Load 전부를 직렬로 배치하는 구조보다 latency 일부가 compute에 숨겨진다.

## ModelSim Verification

| Check | Result |
|---|---|
| SystemVerilog compile | PASS, 0 errors/0 warnings |
| 100 MNIST inference | PASS 99, FAIL 1, Accuracy 99.0% |
| Golden behavior | PASS |
| Interrupt | 20 pulses, 1 pulse/Batch |
| Controller cycle | PASS, 797/43/33 per group |
| End-to-end inference | 161,735 cycle |
| AXI backpressure | 77,977 cycle |

동일 ModelSim 실행에서 Prototype의 종료시각은 1,837,345 ns, Optimized Accelerator는 1,617,525 ns였다. 10 ns clock 기준 전체 실행구간은 약 12.0% 단축되었다. 이 값은 RTL simulation 성능이며 합성 후 Fmax 변화를 포함하지 않는다.

## PPA Assessment

- Performance: AXI Load/compute 중첩으로 simulation end-to-end 시간이 약 12.0% 개선됐다.
- Area: 논리 byte는 약 1.18% 감소하고 memory array 계층은 단순해졌다. 실제 BRAM/LUT 수는 합성이 필요하다.
- Power: 실행시간과 memory 분할 감소는 동적전력에 유리할 수 있으나, 추가 ready/address logic 때문에 확정적인 개선으로 기록하지 않는다.
- Possible downgrade: Unified Buffer arbitration과 주소선택 logic이 Fmax/LUT에 불리할 수 있고, 안전한 재사용 조건 때문에 AXI backpressure가 남는다.

Quartus 합성, Timing Analyzer와 Power Analyzer 결과가 추가되기 전에는 Area/Fmax/Power를 `measured`로 간주하지 않는다.

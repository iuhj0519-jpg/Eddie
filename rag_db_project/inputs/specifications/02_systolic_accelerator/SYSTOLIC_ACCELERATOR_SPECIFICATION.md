# 5×5 Output-Stationary Systolic Accelerator Specification

- 문서 ID: SYS-SPEC-001
- 버전: 0.2
- 상태: draft-for-review
- 기능 블록: Input Buffer, Global Buffer, DNN Scheduler, Systolic Controller, Systolic Array
- 비교 대상: `historical_baselines/systolic_prototype`

## 1. 목적

이 문서는 legacy FC-MLP의 fully-connected 연산을 5×5 systolic array에서 수행하기 위한 목표 아키텍처를 정의한다. 5개의 row는 한 batch의 MNIST image 5개를 동시에 처리하고, 5개의 column은 output neuron 5개를 병렬 계산한다. 한 batch는 5개 image이며 20개 batch를 반복해 총 100개 image를 추론한다.

이 문서는 Historical Baseline의 RTL 구조를 복제하기 위한 문서가 아니다. 승인된 기능, interface, memory 동작과 timing 계약만 제공하며 RAG Agent는 이를 만족하는 독립적인 RTL을 생성해야 한다.

## 2. Design Provenance And Exclusions

| 구분 | 설계 요소 | SPEC 처리 |
|---|---|---|
| 사용자 설계 | Input Buffer | 필수 아키텍처로 포함 |
| 사용자 설계 | Global Buffer와 ping-pong buffering | 필수 아키텍처로 포함 |
| 사용자 설계 | DNN Scheduler FSM | 필수 제어 구조로 포함 |
| 기능 요구 | 5×5 Output-Stationary Systolic Array | FC 연산 대체 구조로 포함 |
| Reference Model 계승 | AXI-Stream, AXI-Lite, activation, MaxFinder 기능 | 외부 호환성과 기능 보존 대상으로 포함 |
| 기존 AI 제안 | 별도 Capture Register | 생성 요구사항에서 제외 |
| 기존 AI 제안 | 별도 MaxFinder Input Register | 생성 요구사항에서 제외 |

결과는 완료 timing에 맞춰 activation 또는 Global Buffer write 경로가 직접 소비해야 한다.

## 3. Top-Level Architecture

```text
AXI-Stream Input
       │
       ▼
+------------------+
| Input Buffer     |  5 banks, one bank per image
+------------------+
       │ Layer 1 source
       ▼
+------------------+       +------------------+
| Systolic Array   | <---- | Weight Memory    |
| 5 rows × 5 cols  |       +------------------+
+------------------+       +------------------+
       │                    | Bias/Activation  |
       └------------------> +------------------+
                               │
                               ▼
                     +------------------+
                     | Global Buffer    |
                     | 5 banks, A/B     |
                     | ping-pong        |
                     +------------------+
                         │          ▲
                         └ next layer

Final Layer Result ──> MaxFinder ──> AXI-Lite Result/Interrupt

DNN Scheduler controls load, layer, tile, group, output and result phases.
```

### 3.1 Input Buffer

- AXI-Stream으로 전달되는 5개 image의 입력을 저장한다.
- 5개 bank를 사용하며 각 bank는 image 한 개의 784개 feature에 대응한다.
- 한 batch의 논리적 입력 matrix는 `[5×784]`다.
- 입력 완료 전 Systolic Array 연산을 시작해서는 안 된다.
- Layer 1의 row input은 Input Buffer의 대응 image bank에서 읽는다.
- 입력 순서와 8-bit data 표현은 Reference Model의 AXI-Stream 계약을 유지한다.

### 3.2 Global Buffer

- Layer 사이의 intermediate result와 tile 결과를 저장한다.
- 5개 image lane에 대응하는 5개 bank로 구성한다.
- 두 개의 논리적 영역 A/B를 사용해 source read와 destination write를 분리한다.
- 현재 layer가 A를 읽으면 결과를 B에 쓰고, 다음 layer에서는 B를 읽어 A에 쓴다.
- read/write 영역 교대는 DNN Scheduler가 layer 경계에서 제어한다.
- 한 bank에서 동시에 필요한 여러 neuron score를 읽을 수 있도록 address와 vector packing 규칙을 정의해야 한다.
- 별도 Capture Register 없이 Systolic Array 완료 결과를 activation/write 경로가 직접 Global Buffer에 저장해야 한다.

### 3.3 DNN Scheduler

DNN Scheduler는 Input Buffer, Global Buffer, Systolic Array, activation과 output sequence를 제어한다.

```text
IDLE → INPUT_LOAD → LAYER_SETUP → TILE_START → TILE_WAIT
                    ↑                           ↓
                    └── GROUP_CHECK ← ACTIVATION_WRITE
                          ↓
                     LAYER_CHECK ── next layer/group
                          ↓ final layer
OUTPUT_LOAD → MAXFINDER_START → MAXFINDER_WAIT → RESULT_VALID → IDLE
```

- `INPUT_LOAD`: 한 batch의 5개 image가 Input Buffer에 저장될 때까지 대기한다.
- `LAYER_SETUP`: 현재 layer의 K, output group 수, source/destination buffer 영역을 설정한다.
- `TILE_START`: Systolic Controller의 start를 1 cycle assertion한다.
- `TILE_WAIT`: 1-cycle done을 기다린다.
- `ACTIVATION_WRITE`: 별도 Capture Register 없이 완료된 array 결과를 activation/write 경로에서 소비한다.
- `GROUP_CHECK`: 다음 5-neuron group 또는 layer 종료를 결정한다.
- `LAYER_CHECK`: 다음 layer로 이동하거나 최종 output sequence를 시작한다.
- `OUTPUT_LOAD`: 최종 10개 score를 MaxFinder가 소비할 수 있는 순서로 제공한다.
- `MAXFINDER_START`, `MAXFINDER_WAIT`: Reference Model과 동등한 class 선택 기능을 실행한다.
- `RESULT_VALID`: batch의 5개 class 결과가 유효함을 표시한다.

별도 `PARTIAL_SUM_CAPTURE` state와 별도 MaxFinder Input Register는 생성 요구사항에 포함하지 않는다.

## 4. Systolic Array Architecture

| 항목 | 기준값 | 의미 |
|---|---:|---|
| Array Rows | 5 | 동시에 처리하는 image lane |
| Array Columns | 5 | 동시에 처리하는 output neuron lane |
| Operand Width | 8 | signed fixed-point input 및 weight |
| Accumulator Width | 26 | signed partial sum |
| SRAM Read Latency | 1 | memory read latency 가정 |

전체 array는 25개의 Processing Element로 구성한다.

- A/input feature는 각 row의 왼쪽에서 입력되어 오른쪽으로 전달된다.
- B/weight는 각 column의 위쪽에서 입력되어 아래쪽으로 전달된다.
- row와 column 위치에 맞춰 operand를 skew해 목표 Processing Element에서 같은 cycle에 만나게 한다.
- 각 Processing Element의 partial sum은 연산 종료까지 해당 element에 유지한다.
- operand만 인접 Processing Element로 이동하므로 dataflow는 output-stationary다.

```text
product = signed(input) × signed(weight)
partial_sum(next) = partial_sum + product, when enabled
```

## 5. Interface Preservation And Handshake

### 5.1 External AXI Interface

Reference Model의 다음 external interface 이름과 transfer 의미를 유지한다.

| Interface | 유지 대상 |
|---|---|
| AXI-Stream input | `axis_in_data`, `axis_in_data_valid`, `axis_in_data_ready` |
| AXI-Lite | address, data, response, valid/ready channel 계약 |
| completion | `intr` 기반 결과 통지 |

AXI-Stream transfer는 `axis_in_data_valid && axis_in_data_ready`인 clock에서 성립한다. data, valid, ready의 세 signal을 사용하는 interface이지만 AXI handshake 조건 자체는 valid/ready의 동시 assertion이다.

### 5.2 Systolic Controller Three-Signal Handshake

Systolic Controller는 다음 세 control signal의 계약을 제공한다.

| Signal | 방향 | 계약 |
|---|---|---|
| `i_start` | input | 새 tile 요청, 1-cycle assertion |
| `o_busy` | output | 계산 진행 중 1 |
| `o_done` | output | 계산 완료 시 정확히 1 cycle 동안 1 |

이 start/busy/done 관계는 내부 controller handshake이며 AXI protocol channel 자체는 아니다. 외부 AXI interface와 내부 controller handshake를 혼동해서는 안 된다.

```text
IDLE --i_start=1 for 1 cycle--> RUN --calculation complete--> DONE_STATE
 ^                                                           |
 └-------------------- next clock ----------------------------┘
```

- start 수락 전 `busy=0`, `done=0`이어야 한다.
- RUN에서만 `busy=1`이어야 한다.
- 완료 시 `busy=0`, `done=1`이어야 한다.
- `done`은 정확히 1 cycle이어야 하며 다음 clock에는 0으로 복귀해야 한다.
- DNN Scheduler는 `TILE_WAIT`에서 done을 검출하고 다음 처리로 이동해야 한다.

## 6. Batch Mapping And Layer Tiling

```text
1 batch = 5 images
20 batches × 5 images = 100 images
```

5개 column을 사용하므로 output neuron은 5개 단위 group으로 처리한다.

| Layer | K | Output Neurons | Groups |
|---|---:|---:|---:|
| Layer 1 | 784 | 30 | 6 |
| Layer 2 | 30 | 20 | 4 |
| Layer 3 | 20 | 10 | 2 |

- Layer 1 source는 Input Buffer다.
- Layer 2와 Layer 3 source는 Global Buffer의 현재 read 영역이다.
- Layer 결과는 Global Buffer의 반대 write 영역에 저장하고 layer 경계에서 A/B 역할을 교대한다.
- 최종 10개 score는 Reference Model과 동등한 MaxFinder 기능으로 전달한다.

## 7. Fixed-Point Format

연산 형식은 floating point가 아니라 signed fixed point다.

- input/weight operand: signed 8-bit fixed point
- accumulator: signed 26-bit
- 정확한 binary-point 위치와 Q-format: 미확정
- IEEE-754 floating-point operator: 사용하지 않음

Q-format이 승인되기 전까지 RAG Agent는 fractional bit 수나 scale을 추측해서는 안 된다. Historical Baseline의 구현값도 승인된 Q-format 근거 없이 정답으로 복사해서는 안 된다.

Signed 8-bit operand와 최대 `K=784`에서 최악 크기 `16,384×784=12,845,056`은 signed 26-bit 범위 안에 있다. 정상 입력 범위에서는 accumulator overflow가 발생하지 않아야 한다.

## 8. Theoretical Cycle Contract

목표 controller의 tile 완료 cycle은 다음 식을 사용한다.

```text
TARGET_CYCLES = K + ROWS + COLS + SRAM_READ_LATENCY + 2
              = K + 13
```

- `K`: dot-product 공통 차원
- `ROWS=5`: row skew와 drain 여유
- `COLS=5`: column 전파와 drain 여유
- `SRAM_READ_LATENCY=1`: SRAM read 지연
- `+2`: controller/array pipeline 여유

| Layer | K | Group 수 | Target Cycles/Group | Group 합계 |
|---|---:|---:|---:|---:|
| Layer 1 | 784 | 6 | 797 | 4,782 |
| Layer 2 | 30 | 4 | 43 | 172 |
| Layer 3 | 20 | 2 | 33 | 66 |

797/43/33은 5개 output neuron group 하나의 목표 cycle이며 layer 전체 또는 end-to-end latency가 아니다. 세 layer의 group cycle 합계는 batch당 5,020 cycle이다. Input Buffer load, activation, Global Buffer write, DNN Scheduler overhead와 MaxFinder latency는 포함하지 않는다.

Historical Baseline은 counter/state transition 때문에 start 수락부터 done까지 798/44/34 clocks가 걸린다. 이 수치는 비교 기준이며 생성 목표가 아니다. RAG 생성 RTL은 1-cycle done을 포함해 797/43/33 target을 만족하도록 독립적으로 counter와 완료 조건을 설계해야 한다.

## 9. Generation Independence And Naming

- Reference Model에서 계승한 external AXI signal과 parameter 이름은 그대로 유지한다.
- 본 SPEC에서 이름을 명시한 controller handshake `i_start`, `o_busy`, `o_done`은 interface 계약으로 유지한다.
- Input Buffer, Global Buffer, DNN Scheduler는 필수 기능 블록이지만 내부 RTL module identifier를 Historical Baseline과 같게 만들 필요는 없다.
- Historical Baseline의 internal state, register, helper signal과 module hierarchy를 복사해서는 안 된다.
- 별도 Capture Register 및 별도 MaxFinder Input Register를 추가해서는 안 된다.
- 생성 결과는 동일한 기능과 timing 요구를 만족하면서도 Historical Baseline과 구조적으로 독립적이어야 한다.

## 10. Requirements

- REQ-SYS-001: Systolic Array는 5 row × 5 column의 25개 Processing Element로 구성해야 한다.
- REQ-SYS-002: A operand는 row 방향, B operand는 column 방향으로 이동해야 한다.
- REQ-SYS-003: partial sum은 output-stationary 방식으로 각 Processing Element에 유지해야 한다.
- REQ-SYS-004: Input Buffer는 5개 image의 `[5×784]` input을 5개 bank에 저장해야 한다.
- REQ-SYS-005: Global Buffer는 5개 bank와 A/B 논리 영역을 사용해 layer 간 ping-pong buffering을 수행해야 한다.
- REQ-SYS-006: DNN Scheduler는 문서에 정의된 load, layer, tile, group, output 및 result sequence를 제어해야 한다.
- REQ-SYS-007: `i_start`는 tile마다 1 cycle assertion해야 한다.
- REQ-SYS-008: `o_busy`는 계산 진행 중에만 1이어야 한다.
- REQ-SYS-009: `o_done`은 계산 완료 시 정확히 1 cycle이어야 한다.
- REQ-SYS-010: external AXI-Stream과 AXI-Lite interface는 Reference Model의 signal 이름과 transfer 계약을 유지해야 한다.
- REQ-SYS-011: 한 batch는 image 5개를 병렬 처리하고 20개 batch로 100개 baseline image를 처리해야 한다.
- REQ-SYS-012: Layer 1/2/3은 각각 6/4/2개의 5-neuron group을 처리해야 한다.
- REQ-SYS-013: operand는 signed 8-bit fixed point, accumulator는 signed 26-bit여야 한다.
- REQ-SYS-014: 승인 전 Q-format을 추측하거나 floating-point 연산으로 변경해서는 안 된다.
- REQ-SYS-015: group별 target cycle은 Layer 1/2/3에 대해 797/43/33이어야 한다.
- REQ-SYS-016: 798/44/34 clocks의 Historical Baseline 동작을 생성 목표로 복사해서는 안 된다.
- REQ-SYS-017: 별도 Capture Register를 필수 data path로 추가해서는 안 된다.
- REQ-SYS-018: 별도 MaxFinder Input Register를 필수 data path로 추가해서는 안 된다.
- REQ-SYS-019: 생성 RTL은 Historical Baseline의 internal naming과 module hierarchy에 의존해서는 안 된다.

## 11. Verification Items

- AXI-Stream valid/ready transfer와 Input Buffer bank/address mapping
- 5개 image의 동시 처리와 20-batch 반복
- Global Buffer A/B ping-pong read/write 충돌 방지
- DNN Scheduler state transition 및 group/layer 반복 횟수
- `i_start`, `o_busy`, `o_done` three-signal handshake와 1-cycle done
- group별 797/43/33 target cycle assertion
- signed fixed-point bit-accurate comparison
- 26-bit accumulator range assertion
- 별도 Capture Register와 MaxFinder Input Register가 없는 data path
- Historical Baseline과 생성 RTL의 module 구조 및 코드 유사도 비교

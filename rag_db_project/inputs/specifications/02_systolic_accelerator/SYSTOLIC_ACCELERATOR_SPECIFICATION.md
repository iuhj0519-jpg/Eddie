# 5×5 Output-Stationary Systolic Accelerator Specification

- 문서 ID: SYS-SPEC-001
- 버전: 1.0
- 상태: approved
- 기능 블록: Input Buffer, Global Buffer, DNN Scheduler, Systolic Controller, Systolic Array, Activation Unit, Weight SRAM, Bias SRAM, SigROM

## 1. 목적

이 문서는 MNIST FC-MLP Reference Model의 fully-connected 연산부에 5×5 systolic controller와 Systolic Array를 이식하기 위한 목표 아키텍처를 정의한다. 기존 external AXI interface와 784→30→20→10 inference 기능을 유지하면서, 연산에 필요한 buffer, SRAM, activation과 scheduling 구조를 추가한다.

5개의 row는 한 batch의 MNIST image 5개를 동시에 처리하고, 5개의 column은 output neuron 5개를 병렬 계산한다. 한 batch는 5개 image이며 20개 batch를 반복해 총 100개 image를 추론한다.

Agent는 이 문서와 승인된 RAG DB 입력만 근거로 코드를 생성해야 한다. 이 문서에 규정되지 않은 내부 구현은 기능·timing·interface 요구사항을 만족하는 범위에서 독립적으로 결정한다.

## 2. Functional Scope

| 기능 블록 | 역할 |
|---|---|
| Input Buffer | AXI-Stream으로 수신한 5개 image 저장 |
| Global Buffer | Layer 1/2의 8-bit Activation Unit 출력 저장과 ping-pong buffering |
| DNN Scheduler | input, layer, tile, group, activation, output sequence 제어 |
| Systolic Controller | start/busy/done과 operand 공급 timing 제어 |
| 5×5 Systolic Array | 5개 image × 5개 output neuron의 Output-Stationary MAC |
| Weight SRAM | 현재 layer/group의 weight를 5개 column에 공급 |
| Bias SRAM | 현재 output neuron group의 bias 공급 |
| SigROM | Sigmoid lookup table 제공 |
| Activation Unit | bias addition, Sigmoid input 변환과 Q1.7 출력 생성 |
| MaxFinder | Layer 3의 10개 activated score에서 class 선택 |

SPEC에 명시되지 않은 중간 register나 별도 저장 구조는 필수 블록이 아니다. Agent가 기능상 필요하다고 판단하면 근거, interface 영향과 cycle 영향을 설명한 뒤 구현할 수 있다.

## 3. Top-Level Architecture

```text
AXI-Stream Input
       │
       ▼
+------------------+
| Input Buffer     |  5 banks, one image per bank
+------------------+
       │ Layer 1 source
       ▼
+------------------+       +------------------+
| 5×5 Systolic     | <---- | Weight SRAM      |  5 banks
| Array/Controller |       +------------------+
+------------------+       +------------------+
       │                    | Bias SRAM        |  5 banks
       ▼                    +------------------+
+------------------+       +------------------+
| Activation Unit | <---- | SigROM           |  5 lanes
+------------------+       +------------------+
       │
       ├─ Layer 1/2 ──> Global Buffer A/B ──> next layer
       │                  5-bank ping-pong
       │
       └─ Layer 3 ─────> MaxFinder ────────> AXI-Lite Result/Interrupt

DNN Scheduler controls every load, layer, tile, group, activation and result phase.
```

## 4. Input Buffer

- Reference Model의 `axis_in_data`, `axis_in_data_valid`, `axis_in_data_ready`로 입력을 수신한다.
- 5개 bank를 사용하며 각 bank는 image 한 개의 784개 Q1.7 feature에 대응한다.
- 한 batch의 논리적 입력 matrix는 `[5×784]`다.
- 입력은 Image-Major 순서다. Batch 1은 image 0의 feature `[0:783]`, image 1의 feature `[0:783]`, ... image 4의 feature `[0:783]` 순서로 수신한다.
- 0-based batch index를 `b`라고 하면 batch `b`는 image `5b`부터 `5b+4`까지를 포함하고, 각 image의 784개 feature를 모두 받은 뒤 다음 image로 이동한다.
- Input Buffer에 data가 load 된 다음 연산이 시작되며, 한 batch 입력 완료 전 Layer 1 연산을 시작해서는 안 된다.
- Layer 1의 row operand는 Input Buffer의 대응 image bank에서 읽는다.
- Reference Model과 동일하게 `axis_in_data_ready`는 정상 동작 중 항상 1이어야 한다.
- 연속 valid 입력을 손실 없이 저장할 수 있어야 하며, 내부 buffer 상태 때문에 AXI 입력 순서나 transfer 의미를 변경해서는 안 된다.

## 5. Global Buffer And Layer Dataflow

Global Buffer는 Layer 1과 Layer 2의 Activation Unit 출력만 저장한다.

- 5개 image lane에 대응하는 5개 bank로 구성한다.
- 저장 data width는 Activation Unit 출력과 동일한 signed 8-bit Q1.7이다.
- A/B 두 논리 영역으로 source read와 destination write를 분리한다.
- Layer 1의 Q1.7 activation output을 첫 write 영역에 저장한다.
- Layer 2는 Layer 1 결과 영역을 읽고, 자신의 Q1.7 activation output을 반대 영역에 저장한다.
- layer 경계에서 DNN Scheduler가 A/B read/write 역할을 교대한다.
- 동일 cycle의 source read와 destination write가 같은 physical location에서 충돌해서는 안 된다.
- Layer 3는 Global Buffer에서 Layer 2 결과를 읽지만, Layer 3의 activation output은 Global Buffer에 저장하지 않고 MaxFinder 경로로 전달한다.

Layer 3 결과의 직접 전달이 구현상 불가능하다고 판단되면 Agent는 저장 구조를 임의로 추가하기 전에 원인, 필요한 저장량, cycle 변화와 interface 영향을 보고해야 한다. 승인 없이 Layer 3 저장을 기본 dataflow로 변경해서는 안 된다.

## 6. DNN Scheduler

```text
IDLE → INPUT_LOAD → LAYER_SETUP → TILE_START → TILE_WAIT
                    ↑                           ↓
                    └── GROUP_CHECK ← ACTIVATION_WRITE
                          ↓
                     LAYER_CHECK ── next layer/group
                          ↓ final layer
OUTPUT_LOAD → MAXFINDER_START → MAXFINDER_WAIT → RESULT_VALID → IDLE
```

- `INPUT_LOAD`: Input Buffer에 한 batch의 5개 image가 저장될 때까지 대기한다.
- `LAYER_SETUP`: 현재 layer의 K, output group 수와 source/destination 경로를 설정한다.
- `TILE_START`: Systolic Controller의 `i_start`를 1 cycle assertion한다.
- `TILE_WAIT`: `o_done`의 1-cycle assertion을 기다린다.
- `ACTIVATION_WRITE`: bias와 Sigmoid 변환을 적용한다. Layer 1/2는 Global Buffer에 쓰고 Layer 3는 output 경로로 전달한다.
- `GROUP_CHECK`: 다음 5-neuron group 또는 현재 layer 종료를 결정한다.
- `LAYER_CHECK`: 다음 layer로 이동하거나 최종 output sequence를 시작한다.
- `OUTPUT_LOAD`: Layer 3의 activated score 10개를 Reference Model의 MaxFinder가 소비할 수 있는 형식과 순서로 제공한다.
- `MAXFINDER_START`, `MAXFINDER_WAIT`: image별 class 선택 완료를 관리한다.
- `RESULT_VALID`: batch의 class 결과 5개가 유효함을 표시한다.

## 7. Systolic Array Architecture

| 항목 | 기준값 | 의미 |
|---|---:|---|
| Array Rows | 5 | 동시에 처리하는 image lane |
| Array Columns | 5 | 동시에 처리하는 output neuron lane |
| Input/Activation Width | 8 | signed Q1.7 |
| Weight Width | 8 | signed Q4.4 |
| Accumulator Width | 26 | signed Q15.11 |
| SRAM Read Latency | 1 | Weight/Bias SRAM read latency |

전체 array는 25개의 Processing Element로 구성한다.

- A/input feature는 각 row의 왼쪽에서 입력되어 오른쪽으로 전달된다.
- B/weight는 각 column의 위쪽에서 입력되어 아래쪽으로 전달된다.
- row와 column 위치에 맞춰 operand를 skew해 목표 Processing Element에서 같은 cycle에 만나게 한다.
- 각 Processing Element의 partial sum은 연산 종료까지 해당 element에 유지한다.
- operand만 인접 Processing Element로 이동하므로 dataflow는 output-stationary다.

## 8. Weight SRAM, Bias SRAM And SigROM

- Weight SRAM은 5개 column에 대응하는 5개 bank로 구성하고 현재 layer/group의 Q4.4 weight를 공급한다.
- Weight address는 row/column skew와 K 범위를 반영해야 한다.
- Bias SRAM은 output neuron 5개 단위 group에 대응하는 Q5.3 bias를 공급한다.
- Weight와 Bias MIF의 layer/neuron 순서는 Reference Model과 동일해야 한다.
- SigROM은 Reference Model의 `sigContent.mif`를 사용한다.
- 5개 image lane이 독립적인 Sigmoid address를 동시에 조회할 수 있어야 한다.
- SRAM/ROM latency는 Systolic Controller와 DNN Scheduler timing에 반영해야 한다.

## 9. Fixed-Point Contract

Reference Model과 생성 모델은 다음 fixed-point chain을 동일하게 유지한다.

```text
Activation/Input Q1.7
    × Weight Q4.4
    → Product Q5.11
    → Accumulator Q15.11
    + Bias Q5.3 aligned to Q15.11
    → Sigmoid Input Q5.5
    → Activation Output Q1.7
```

| 단계 | Format | Width | 변환 계약 |
|---|---|---:|---|
| Input/Previous Activation | Q1.7 | 8 | signed |
| Weight | Q4.4 | 8 | signed |
| Product | Q5.11 | 16 | signed multiplication |
| Accumulator | Q15.11 | 26 | product의 fractional 11-bit 유지 |
| Bias | Q5.3 | 8 | accumulator 가산 전 fractional alignment 필요 |
| Sigmoid Input | Q5.5 | 10 | accumulator+bias에서 fractional 6-bit 축소 |
| Activation Output | Q1.7 | 8 | `sigContent.mif` lookup result |

- Bias Q5.3은 Q15.11에 더하기 전에 sign extension하고 fractional 차이 8-bit만큼 left shift한다.
- Q15.11에서 Q5.5로 변환할 때 fractional bit 6개를 제거한다.
- Reference Model과 bit-accurate한 truncation, sign과 overflow 처리를 유지해야 한다.
- IEEE-754 floating-point operator를 사용해서는 안 된다.

Q15.11의 값이 signed Q5.5 표현 범위를 벗어나면 Sigmoid LUT address를 생성하기 전에 saturation해야 한다. Q5.5의 범위는 raw `-512`~`511`, 실수값 `-16.0`~`15.96875`다.

- Q15.11 raw 값이 `32704`보다 크면 Q5.5 최댓값 `10'b0111111111`로 clamp한다.
- Q15.11 raw 값이 `-32768`보다 작으면 Q5.5 최솟값 `10'b1000000000`로 clamp한다.
- 범위 안이면 fractional 6-bit를 제거해 Q5.5 LUT address를 만든다.
- 이 saturation은 integer MSB overflow와 wrap-around로 인해 큰 양수가 음수 LUT 영역으로, 또는 큰 음수가 양수 LUT 영역으로 잘못 mapping되는 것을 방지한다.

## 10. External AXI Interface

Reference Model의 external AXI signal 이름, width와 transfer 의미를 유지한다.

| Interface | 유지 대상 |
|---|---|
| AXI-Stream Input | `axis_in_data`, `axis_in_data_valid`, `axis_in_data_ready` |
| AXI-Lite | address, data, response와 valid/ready channel 계약 |
| Completion | `intr` 기반 결과 통지 |

AXI-Stream transfer는 `axis_in_data_valid && axis_in_data_ready`인 clock에서 성립한다. Input Buffer 추가로 인해 입력 data의 순서, width 또는 valid/ready 의미가 바뀌어서는 안 된다.

## 11. AXI-Lite Batch Result And Interrupt

- 한 batch의 class 결과 5개는 image row 순서인 image 0→4의 상대 순서로 제공한다.
- Reference Model의 output register decode `3'h2`, byte address `0x08` 하나를 유지한다.
- Software/testbench가 `0x08`을 반복 read하면 각 완료된 AXI read handshake마다 다음 class 결과를 반환한다.
- batch result read index는 RESULT_VALID 진입 시 0으로 초기화하고 0부터 4까지 증가한다.
- AXI-Lite byte address `0x08`은 내부의 5-entry class result storage를 순차 조회하는 단일 address window로 동작한다.
- 다섯 번째 read handshake가 끝나면 현재 batch의 class result 5개와 read index를 clear한다.
- 다음 batch의 AXI-Stream 입력을 받기 전에 class result storage와 read index가 모두 0으로 초기화되어 있어야 한다.
- 다섯 결과가 모두 준비되면 `intr`를 batch당 정확히 한 번, 1 cycle assertion한다.
- `intr`의 pulse 의미는 Reference Model의 `intr = out_valid` 동작과 동일하게 유지한다.
- DNN Scheduler는 모든 image의 MaxFinder가 끝나면 RESULT_VALID에 진입하고, 다섯 번째 AXI-Lite result read handshake가 완료될 때까지 이 상태를 유지한다.
- 다섯 번째 result read가 완료되면 RESULT_VALID를 종료하고 IDLE로 복귀한다.
- 다음 batch의 Image-Major stream은 IDLE 복귀 후 INPUT_LOAD에서 시작한다.

## 12. Systolic Controller Handshake

| Signal | 방향 | 계약 |
|---|---|---|
| `i_start` | input | 새 tile 요청, 1-cycle assertion |
| `o_busy` | output | 계산 진행 중 1 |
| `o_done` | output | 계산 완료 시 정확히 1 cycle 동안 1 |

start/busy/done은 내부 controller의 three-signal handshake이며 AXI protocol channel 자체는 아니다.

```text
IDLE --i_start=1 for 1 cycle--> RUN --calculation complete--> DONE_STATE
 ^                                                           |
 └-------------------- next clock ----------------------------┘
```

- start 수락 전 `o_busy=0`, `o_done=0`이어야 한다.
- RUN에서만 `o_busy=1`이어야 한다.
- 완료 시 `o_busy=0`, `o_done=1`이어야 한다.
- `o_done`은 정확히 1 cycle이어야 하며 다음 clock에는 0으로 복귀해야 한다.
- DNN Scheduler는 `TILE_WAIT`에서 `o_done`을 검출해야 한다.

## 13. Batch Mapping And Layer Tiling

```text
1 batch = 5 images
20 batches × 5 images = 100 images
```

```text
Batch 1: image  0 →  1 →  2 →  3 →  4
Batch 2: image  5 →  6 →  7 →  8 →  9
...
Batch 20: image 95 → 96 → 97 → 98 → 99

Each image stream: feature[0] → feature[1] → ... → feature[783]
```

현재 batch의 `RESULT_VALID` 종료와 IDLE 복귀가 완료되기 전에는 다음 batch stream을 시작하지 않는다.

| Layer | K | Output Neurons | 5-Neuron Groups | Source | Destination |
|---|---:|---:|---:|---|---|
| Layer 1 | 784 | 30 | 6 | Input Buffer | Global Buffer |
| Layer 2 | 30 | 20 | 4 | Global Buffer | Opposite Global Buffer Region |
| Layer 3 | 20 | 10 | 2 | Global Buffer | MaxFinder Path |

## 14. Theoretical Cycle Contract

tile 완료 목표 cycle은 다음 식을 사용한다.

```text
TARGET_CYCLES = K + ROWS + COLS + SRAM_READ_LATENCY + 2
              = K + 13
```

| Layer | K | Group 수 | Target Cycles/Group | Group 합계 |
|---|---:|---:|---:|---:|
| Layer 1 | 784 | 6 | 797 | 4,782 |
| Layer 2 | 30 | 4 | 43 | 172 |
| Layer 3 | 20 | 2 | 33 | 66 |

797/43/33은 5개 output neuron group 하나의 목표 cycle이며 layer 전체 또는 end-to-end latency가 아니다. 세 layer의 group cycle 합계는 batch당 5,020 cycle이다. Input Buffer load, activation, Global Buffer write, DNN Scheduler overhead와 MaxFinder latency는 포함하지 않는다.

Agent가 목표 cycle과 다른 완료 조건이 불가피하다고 판단하면 코드를 확정하기 전에 원인, 계산식과 예상 cycle을 보고해야 한다.

## 15. Code Generation Boundary

- Reference Model에서 계승한 external AXI signal과 parameter 이름은 그대로 유지한다.
- 본 SPEC에서 이름을 명시한 `i_start`, `o_busy`, `o_done`은 controller interface 계약으로 유지한다.
- 새 parameter 이름은 의미를 나타내는 full name의 `UPPER_SNAKE_CASE`를 사용한다.
- 새 signal, register, counter와 내부 control 이름은 의미를 나타내는 full name의 lowercase `snake_case`를 사용한다.
- 관용적인 protocol 이름이나 본 SPEC이 고정한 이름 외에는 의미를 축약한 identifier를 사용하지 않는다.
- 내부 module과 state 이름은 기능을 명확히 표현하되 SPEC이 특정 identifier를 강제하지 않는다.
- 승인된 RAG DB 밖의 구현이나 코드 구조를 생성 근거로 사용해서는 안 된다.
- 명시되지 않은 내부 구조가 필요하면 Agent가 기능적 근거와 trade-off를 설명하고 자체적으로 결정한다.

Q15.11→Q5.5 saturation은 comparator와 three-way MUX로 구성한 combinational clamp를 우선 사용해 추가 cycle을 만들지 않는다. Timing closure 때문에 pipeline register가 불가피하면 Agent는 구현 전에 변경 이유와 cycle 영향을 보고해야 한다.

## 16. Requirements

- REQ-SYS-001: Systolic Array는 5 row × 5 column의 25개 Processing Element로 구성해야 한다.
- REQ-SYS-002: partial sum은 Output-Stationary 방식으로 각 Processing Element에 유지해야 한다.
- REQ-SYS-003: Input Buffer는 5개 image의 `[5×784]` Q1.7 input을 5개 bank에 저장해야 한다.
- REQ-SYS-004: `axis_in_data`의 width, order, valid/ready transfer와 always-ready 동작을 Reference Model과 동일하게 유지해야 한다.
- REQ-SYS-005: Global Buffer는 Layer 1/2의 Q1.7 Activation Unit 출력만 저장해야 한다.
- REQ-SYS-006: Global Buffer는 5개 bank와 A/B 논리 영역으로 ping-pong buffering을 수행해야 한다.
- REQ-SYS-007: Layer 3의 Q1.7 activation output은 기본 dataflow에서 Global Buffer에 저장하지 않고 MaxFinder 경로로 전달해야 한다.
- REQ-SYS-008: DNN Scheduler는 정의된 input, layer, tile, group, activation, output과 result sequence를 제어해야 한다.
- REQ-SYS-009: Weight SRAM과 Bias SRAM은 5-bank 구조로 현재 group의 weight와 bias를 공급해야 한다.
- REQ-SYS-010: SigROM은 Reference Model의 `sigContent.mif`와 Q5.5 address 계약을 유지해야 한다.
- REQ-SYS-011: `i_start`와 `o_done`은 각각 정확히 1 cycle이어야 하고 `o_busy`는 계산 중에만 1이어야 한다.
- REQ-SYS-012: 한 batch는 image 5개를 병렬 처리하고 20개 batch로 100개 image를 처리해야 한다.
- REQ-SYS-013: Layer 1/2/3은 각각 6/4/2개의 5-neuron group을 처리해야 한다.
- REQ-SYS-014: fixed-point chain은 Q1.7×Q4.4→Q15.11, Bias Q5.3, Sigmoid Input Q5.5, Activation Output Q1.7을 유지해야 한다.
- REQ-SYS-015: IEEE-754 floating-point 연산을 사용해서는 안 된다.
- REQ-SYS-016: group별 target cycle은 Layer 1/2/3에 대해 797/43/33이어야 한다.
- REQ-SYS-017: 목표 cycle 변경이 필요하면 Agent는 구현 전 근거와 새 계산식을 보고해야 한다.
- REQ-SYS-018: 생성 코드는 승인된 RAG DB 입력만 설계 근거로 사용해야 한다.
- REQ-SYS-019: Q15.11에서 Q5.5로 변환할 때 signed Q5.5 범위를 벗어난 값은 LUT address 생성 전에 최댓값 또는 최솟값으로 saturation해야 한다.
- REQ-SYS-020: AXI-Stream input은 batch 안에서 Image-Major 순서로 image별 feature `[0:783]`을 연속 수신해야 한다.
- REQ-SYS-021: 다음 batch input은 현재 batch의 RESULT_VALID 종료와 IDLE 복귀 후 INPUT_LOAD에서 시작해야 한다.
- REQ-SYS-022: class 결과 5개는 AXI-Lite byte address `0x08`의 반복 read로 image 순서대로 제공하고, 다섯 번째 read handshake 후 RESULT_VALID에서 IDLE로 복귀해야 한다.
- REQ-SYS-023: `intr`는 batch 결과 5개가 모두 준비됐을 때 batch당 정확히 한 번, 1 cycle assertion해야 한다.
- REQ-SYS-024: 다섯 번째 result read 후부터 다음 batch 입력 전까지 5-entry class result storage와 read index를 clear해야 한다.
- REQ-SYS-025: 새 parameter는 `UPPER_SNAKE_CASE`, 새 internal signal/register/counter는 full-name lowercase `snake_case` 규칙을 따라야 한다.
- REQ-SYS-026: Q5.5 saturation은 기본적으로 추가 pipeline cycle 없는 combinational comparator/MUX 구조로 구현해야 한다.

## 17. Verification Items

- AXI-Stream always-ready transfer와 Input Buffer bank/address mapping
- 5개 image 동시 처리와 20-batch 반복
- Layer 1/2 Q1.7 activation write와 Global Buffer A/B ping-pong 충돌 방지
- Layer 3 activation의 MaxFinder 직접 전달
- DNN Scheduler state transition과 6/4/2 group 반복
- `i_start`, `o_busy`, `o_done` handshake와 1-cycle done
- Weight/Bias MIF의 layer, neuron, bank mapping
- Q1.7×Q4.4→Q15.11 fixed-point bit-accurate MAC
- Bias Q5.3 alignment와 Q5.5 Sigmoid input 변환
- Q5.5 saturation boundary와 MSB overflow 방지
- `sigContent.mif` lookup과 Q1.7 activation output
- Image-Major input ordering과 batch 간 RESULT_VALID/IDLE 경계
- AXI-Lite `0x08` 반복 read의 image 0→4 결과 순서와 read index reset
- 다섯 번째 read 후 class result storage clear와 다음 batch 시작 전 reset 상태
- batch당 1-cycle `intr`
- parameter 및 internal signal naming lint
- saturation combinational path가 target cycle을 증가시키지 않는지 확인
- group별 797/43/33 target cycle assertion
- 100-image inference 결과와 Reference Model 기능 비교

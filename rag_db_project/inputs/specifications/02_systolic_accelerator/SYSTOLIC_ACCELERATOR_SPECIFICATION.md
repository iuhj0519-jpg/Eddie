# 5×5 Output-Stationary Systolic Accelerator Specification

- 문서 ID: SYS-SPEC-001
- 버전: 0.1
- 상태: draft-for-review
- 목표 module: `systolic_controller`, `systolic_array_2d`, `pe_systolic_cell`, `mac_pe`
- 참고 구현: `historical_baselines/systolic_prototype`

## 1. 목적

이 문서는 legacy FC-MLP의 fully-connected 연산을 5×5 systolic array에서 수행하기 위한 목표 아키텍처를 정의한다. 5개의 row는 한 batch의 MNIST image 5개를 동시에 처리하는 image lane이고, 5개의 column은 한 neuron group의 output lane이다. 한 batch는 5개 image로 구성하며 20개 batch를 반복해 총 100개 image를 추론한다.

## 2. Array architecture

| Parameter | 기준값 | 의미 |
|---|---:|---|
| `ROWS` | 5 | array row/동시 input lane |
| `COLS` | 5 | array column/output neuron lane |
| `DATA_W` | 8 | signed input 및 weight width |
| `ACC_W` | 26 | signed accumulated result width |
| `SRAM_READ_LATENCY` | 1 | 현재 memory read latency 가정 |

전체 array는 25개의 `pe_systolic_cell`로 구성한다.

```text
A input → PE(0,0) → PE(0,1) → ... → PE(0,4)
          ↓         ↓                 ↓
         PE(1,0) → PE(1,1) → ... → PE(1,4)
          ↓         ↓                 ↓
          ...       ...               ...
          ↓         ↓                 ↓
         PE(4,0) → PE(4,1) → ... → PE(4,4)
                    ↑
                 B input
```

- A/input feature는 각 row의 왼쪽에서 입력되어 오른쪽으로 전달된다.
- B/weight는 각 column의 위쪽에서 입력되어 아래쪽으로 전달된다.
- row/column index만큼 입력 주소를 지연해 두 operand가 목표 PE에서 같은 cycle에 만나도록 skew한다.

## 3. Output-stationary dataflow

각 PE의 partial sum은 해당 PE 내부 `acc_sum` register에 머무른다. A와 B operand만 인접 PE로 이동하며, 누산 결과는 연산이 끝날 때까지 이동하지 않는다. 따라서 dataflow는 output-stationary(OS)다.

`mac_pe` 동작:

```text
mul = signed(a) × signed(b)
acc_sum(next) = acc_sum + mul, when enable=1
```

- reset 또는 `clr`에서 accumulator를 0으로 만든다.
- `en=1`일 때만 multiply-accumulate한다.
- `en=0`이면 operand pipeline과 accumulator 상태를 유지한다.

## 4. Controller interface

| Signal | 방향 | 의미 |
|---|---|---|
| `i_start` | input | 새 tile 연산 요청 |
| `o_busy` | output | controller가 RUN 상태임 |
| `o_done` | output | 결과가 완료되어 DONE_STATE에 있음 |
| `current_common_dimension_length` | input | 현재 layer의 K dimension |

Memory feed interface는 row별 input-feature read와 column별 weight read를 제공한다. 각 read channel은 enable, address, data, valid를 가진다.

## 5. FSM

```text
IDLE --i_start=1--> RUN --cycle complete--> DONE_STATE
  ^                                       |
  └--------------- i_start=0 -------------┘
```

### IDLE

- `o_busy=0`, `o_done=0`
- `i_start=1`이면 다음 상태를 `RUN`으로 설정한다.
- `(state==IDLE) && i_start`에서 `array_clr=1`로 accumulator를 초기화한다.

### RUN

- `o_busy=1`, `o_done=0`
- `array_en=1`
- cycle counter를 증가시킨다.
- skew된 input/weight read address를 생성하고 valid data를 array에 공급한다.
- 완료 조건을 만족하면 `DONE_STATE`로 전이한다.

### DONE_STATE

- `o_busy=0`, `o_done=1`
- `o_done`은 one-cycle pulse가 아니라 상태 level이다.
- requester가 `i_start=0`으로 내리면 `IDLE`로 돌아간다.

Controller 단독 interface에서는 start가 계속 1이면 DONE_STATE에 머물고, start가 0인 clock에서 IDLE 복귀를 예약한다.

현재 `NPU_Top` 결합에서는 `array_controller_start = (dnn_state == TILE_START)`이므로 `i_start`는 `TILE_START` 동안 1 cycle만 1이고, `TILE_WAIT` 진입과 함께 0이 된다. Controller는 IDLE에서 이 start를 수락한 뒤 start level과 무관하게 RUN을 계속한다. 계산 완료 후 DONE_STATE에 진입하면 `o_done`이 1이 되며, 이 시점에는 `i_start`가 이미 0이므로 다음 clock에 IDLE로 돌아간다. 따라서 현재 결합에서 관찰되는 `o_done`은 1 cycle이지만, 별도의 one-cycle pulse 생성 로직이 아니라 상태와 handshake의 결과다. 목표 구현은 이 동작을 변경하지 않는다.

## 6. Batch mapping

```text
1 batch = 5 images
20 batches × 5 images = 100 images
```

- 입력 matrix의 한 tile은 `[5×K]`이며 각 row가 서로 다른 image에 대응한다.
- Layer 1에서 `K=784`이고 5개 image의 feature vector를 병렬 처리한다.
- 각 row는 독립적인 image 결과를 유지하며, 최종적으로 5개의 maxFinder가 batch의 class 결과 5개를 생성한다.
- 20-batch 반복은 array 내부 한 번의 tile 연산이 아니라 testbench 또는 상위 제어가 수행하는 전체 inference schedule이다.

## 7. DNN Scheduler and top-level data path

```text
IDLE → INPUT_LOAD → LAYER_SETUP → TILE_START → TILE_WAIT
                    ↑                           ↓
                    └── GROUP_CHECK ← ACTIVATION_WRITE
                          ↓
                     LAYER_CHECK ── next layer/group
                          ↓ final layer
OUTPUT_LOAD → MAXFINDER_START → MAXFINDER_WAIT → RESULT_VALID → IDLE
```

- 별도의 `PARTIAL_SUM_CAPTURE` 상태를 두지 않는다. `TILE_WAIT && array_controller_done`인 clock edge에서 array 결과를 capture register에 저장하고 `ACTIVATION_WRITE`로 진행한다.
- Layer 1/2 intermediate activation은 5-bank global buffer의 A/B 영역을 ping-pong 방식으로 사용한다.
- Weight는 global buffer에 저장하지 않고 5-bank Weight SRAM에서 skew 후 array로 직접 공급한다.
- Bias SRAM, activation unit, SigROM과 maxFinder는 batch의 5개 image lane에 맞춰 병렬 구성한다.
- `GROUP_CHECK`는 현재 layer의 다음 5-neuron group을 결정하고, `LAYER_CHECK`는 다음 layer 또는 최종 output 경로를 결정한다.

## 8. Input/weight skew

RUN cycle counter를 `cnt`라고 할 때 row `r`과 column `c`의 기본 주소는 다음과 같다.

```text
input_feature_address[r] = cnt - r
weight_address[c]        = cnt - c
```

주소는 `0 <= address < current_common_dimension_length` 범위에서만 enable해야 한다. memory valid가 0일 때 array operand는 0을 공급한다.

## 9. Layer tiling

5개 column을 사용하므로 output neuron group은 다음과 같다.

| Layer | Output neuron | 5-column group |
|---|---:|---:|
| Layer 1 | 30 | 6 |
| Layer 2 | 20 | 4 |
| Layer 3 | 10 | 2 |

현재 30, 20, 10은 모두 5로 나누어 떨어진다. 이후 array 크기를 변경하면 ceiling division과 invalid-lane mask가 필요하다.

## 10. Numeric format status

현재 RTL은 IEEE-754 floating-point 연산기를 사용하지 않는다. `logic signed [DATA_W-1:0]` operand와 signed multiplier/accumulator로 구현되어 있으므로 bit-level 구현은 signed integer 또는 fixed-point encoding이다. 따라서 이를 floating point라고 확정해서는 안 된다.

- operand width: signed 8-bit
- accumulator width: signed 26-bit
- 정확한 binary-point 위치와 Q-format: 미확정
- `mac_pe`에는 saturation 로직이 없으므로 overflow 시 fixed-width two's-complement wrap 동작을 한다.
- 다만 signed 8-bit operand와 최대 `K=784`에서 최악 크기 `16,384×784=12,845,056`은 signed 26-bit 범위 안이므로 정상 입력 범위에서는 accumulator overflow가 발생하지 않아야 한다.

RAG Agent는 Q-format이 승인되기 전까지 scale을 추측하거나 floating-point로 변환해서는 안 된다.

## 11. Cycle model

Controller의 현재 완료-cycle 모델은 다음과 같다. 이는 실측값이나 수학적으로 최소인 systolic latency가 아니라, 현재 설계가 drain과 memory/pipeline 여유를 포함해 정한 이론적 controller threshold다.

```text
CALC_CYCLES = K + ROWS + COLS + SRAM_READ_LATENCY + 2
```

각 항의 의미는 다음과 같다.

- `K`: 한 output을 만들기 위한 dot-product 공통 차원
- `ROWS`: row skew 및 drain을 위한 설계 여유
- `COLS`: column 전파 및 drain을 위한 설계 여유
- `SRAM_READ_LATENCY`: synchronous SRAM read 지연
- `2`: controller/array pipeline 여유

기준값 `ROWS=5`, `COLS=5`, `SRAM_READ_LATENCY=1`이므로 `CALC_CYCLES = K + 13`이다.

| Layer | K | 5-neuron group 수 | group당 `CALC_CYCLES` | layer group 합계 |
|---|---:|---:|---:|---:|
| Layer 1 | 784 | 6 | 797 | 4,782 |
| Layer 2 | 30 | 4 | 43 | 172 |
| Layer 3 | 20 | 2 | 33 | 66 |

797/43/33은 layer 전체가 아니라 5개 output neuron을 계산하는 tile/group 하나의 threshold다. 세 layer의 group threshold 합계는 batch당 5,020이며, input load, activation, buffer write, maxFinder, scheduler 상태 전이 비용은 포함하지 않는다.

현재 RTL은 RUN의 `cnt=0`부터 시작하고 `cnt >= CALC_CYCLES`일 때 다음 clock에 DONE_STATE로 전이한다. 따라서 start 수락 edge부터 `o_done` assertion까지의 RTL상 관찰 간격은 group당 `CALC_CYCLES + 1`, 즉 798/44/34 clock으로 해석된다. SPEC의 797/43/33은 승인된 controller threshold이며, 전체 latency와 혼동하지 않아야 한다.

## 12. 요구사항

- REQ-SYS-001: 기본 array는 5 row × 5 column의 25개 PE로 구성해야 한다.
- REQ-SYS-002: A operand는 row 방향, B operand는 column 방향으로 전달해야 한다.
- REQ-SYS-003: partial sum은 각 PE에 유지되는 output-stationary 방식이어야 한다.
- REQ-SYS-004: controller FSM은 `IDLE`, `RUN`, `DONE_STATE`로 구성해야 한다.
- REQ-SYS-005: `i_start` 수락 시 새 연산 전에 모든 accumulator를 clear해야 한다.
- REQ-SYS-006: `o_busy`는 RUN에서만 1이어야 한다.
- REQ-SYS-007: `o_done`은 DONE_STATE에서 1이어야 한다. 현재 `NPU_Top`처럼 `i_start`가 TILE_START의 1-cycle level이고 DONE_STATE 진입 전에 이미 0이면 `o_done`은 결과적으로 1 cycle 동안 관찰되어야 하며, 별도 pulse 생성기로 변경하지 않아야 한다.
- REQ-SYS-008: input과 weight address는 row/column index에 따라 skew되어야 한다.
- REQ-SYS-009: memory valid가 없는 operand는 0으로 처리해야 한다.
- REQ-SYS-010: signed 8-bit operand의 partial sum은 signed 26-bit accumulator에 저장해야 한다.
- REQ-SYS-011: layer별 output group 수는 30/20/10 neuron을 모두 처리해야 한다.
- REQ-SYS-012: 완료-cycle 모델은 K와 memory latency를 parameter로 사용해야 한다.
- REQ-SYS-013: 모든 array read address는 current K dimension 범위를 벗어나면 안 된다.
- REQ-SYS-014: reset 후 FSM은 IDLE, accumulator와 control counter는 0이어야 한다.
- REQ-SYS-015: 한 batch는 5개 image로 구성하고 array의 5개 row에서 동시에 처리해야 한다.
- REQ-SYS-016: 전체 baseline inference는 20개 batch를 반복해 총 100개 image를 처리해야 한다.
- REQ-SYS-017: group별 `CALC_CYCLES` threshold는 Layer 1/2/3에 대해 각각 797/43/33이어야 한다.
- REQ-SYS-018: 797/43/33을 layer 전체 latency 또는 end-to-end latency로 보고해서는 안 된다.
- REQ-SYS-019: numeric Q-format이 승인되기 전까지 operand를 floating-point로 간주하거나 임의의 binary-point를 적용해서는 안 된다.
- REQ-SYS-020: partial sum은 별도 scheduler state 없이 `TILE_WAIT && o_done` edge에서 capture해야 한다.
- REQ-SYS-021: `mac_pe`에 임의의 saturation 연산을 추가해서는 안 되며, signed 26-bit 범위 내에서 reference와 bit-accurate하게 일치해야 한다.

## 13. 검증 필요 항목

- `TILE_START` 1-cycle start와 DONE_STATE level output의 결합 동작 assertion
- group별 threshold 797/43/33과 관찰 간격 798/44/34의 cycle assertion
- memory valid 지연 시 고정 cycle 모델의 안전성
- signed 8-bit 최악 입력과 `K=784`에서 26-bit accumulator range assertion
- array 크기 변경 시 partial group lane masking
- OS 결과와 reference neuron arithmetic의 layer별 bit-accurate 비교

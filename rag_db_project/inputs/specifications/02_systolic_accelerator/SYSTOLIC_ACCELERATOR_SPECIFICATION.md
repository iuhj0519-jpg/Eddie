# 5×5 Output-Stationary Systolic Accelerator Specification

- 문서 ID: SYS-SPEC-001
- 버전: 0.1
- 상태: draft-for-review
- 목표 module: `systolic_controller`, `systolic_array_2d`, `pe_systolic_cell`, `mac_pe`
- 참고 구현: `historical_baselines/systolic_prototype`

## 1. 목적

이 문서는 legacy FC-MLP의 fully-connected 연산을 5×5 systolic array에서 수행하기 위한 목표 아키텍처를 정의한다. 5개의 row는 동시에 처리할 input/image lane, 5개의 column은 한 neuron group의 output lane으로 사용하며 layer의 output neuron은 5개 단위 group으로 처리한다.

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

따라서 start requester는 done을 확인한 뒤 start를 deassert해야 한다. start가 계속 1이면 controller는 DONE_STATE에 머문다.

## 6. Input/weight skew

RUN cycle counter를 `cnt`라고 할 때 row `r`과 column `c`의 기본 주소는 다음과 같다.

```text
input_feature_address[r] = cnt - r
weight_address[c]        = cnt - c
```

주소는 `0 <= address < current_common_dimension_length` 범위에서만 enable해야 한다. memory valid가 0일 때 array operand는 0을 공급한다.

## 7. Layer tiling

5개 column을 사용하므로 output neuron group은 다음과 같다.

| Layer | Output neuron | 5-column group |
|---|---:|---:|
| Layer 1 | 30 | 6 |
| Layer 2 | 20 | 4 |
| Layer 3 | 10 | 2 |

현재 30, 20, 10은 모두 5로 나누어 떨어진다. 이후 array 크기를 변경하면 ceiling division과 invalid-lane mask가 필요하다.

## 8. Cycle model

Controller의 현재 완료-cycle 모델은 다음과 같다.

```text
CALC_CYCLES = K + ROWS + COLS + SRAM_READ_LATENCY + 2
```

기준값 `ROWS=5`, `COLS=5`, `SRAM_READ_LATENCY=1`일 때:

| Layer | K | Controller formula |
|---|---:|---:|
| Layer 1 | 784 | 797 cycles |
| Layer 2 | 30 | 43 cycles |
| Layer 3 | 20 | 33 cycles |

이 값은 controller 내부 완료 조건의 기준이다. start edge부터 done assertion까지의 관찰 cycle 수는 counter 비교와 상태 전이 cycle을 포함해 testbench assertion으로 별도 확정해야 한다.

## 9. 요구사항

- REQ-SYS-001: 기본 array는 5 row × 5 column의 25개 PE로 구성해야 한다.
- REQ-SYS-002: A operand는 row 방향, B operand는 column 방향으로 전달해야 한다.
- REQ-SYS-003: partial sum은 각 PE에 유지되는 output-stationary 방식이어야 한다.
- REQ-SYS-004: controller FSM은 `IDLE`, `RUN`, `DONE_STATE`로 구성해야 한다.
- REQ-SYS-005: `i_start` 수락 시 새 연산 전에 모든 accumulator를 clear해야 한다.
- REQ-SYS-006: `o_busy`는 RUN에서만 1이어야 한다.
- REQ-SYS-007: `o_done`은 DONE_STATE에서 1이고 `i_start`가 0이 될 때까지 유지해야 한다.
- REQ-SYS-008: input과 weight address는 row/column index에 따라 skew되어야 한다.
- REQ-SYS-009: memory valid가 없는 operand는 0으로 처리해야 한다.
- REQ-SYS-010: signed 8-bit operand의 partial sum은 signed 26-bit accumulator에 저장해야 한다.
- REQ-SYS-011: layer별 output group 수는 30/20/10 neuron을 모두 처리해야 한다.
- REQ-SYS-012: 완료-cycle 모델은 K와 memory latency를 parameter로 사용해야 한다.
- REQ-SYS-013: 모든 array read address는 current K dimension 범위를 벗어나면 안 된다.
- REQ-SYS-014: reset 후 FSM은 IDLE, accumulator와 control counter는 0이어야 한다.

## 10. 검증 필요 항목

- start가 pulse인지 level handshake인지 상위 controller와 일관성 확인
- formula 값과 실제 start-to-done 관찰 cycle의 정확한 관계
- memory valid 지연 시 고정 cycle 모델의 안전성
- signed overflow와 accumulator saturation/ wrap 정책
- array 크기 변경 시 partial group lane masking
- OS 결과와 reference neuron arithmetic의 layer별 bit-accurate 비교

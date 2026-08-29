# Legacy FC-MLP Reference Model Specification

- 문서 ID: REF-SPEC-001
- 버전: 0.1
- 상태: draft-for-review
- DUT top: `zyNet`
- 기준 구현: `inputs/reference_model/model/rtl`

## 1. 목적

이 문서는 MNIST inference를 수행하는 legacy FC-MLP RTL의 기능 및 인터페이스 계약을 정의한다. 후속 5×5 systolic accelerator는 내부 연산 구조를 변경하더라도 이 문서의 승인된 기능 결과를 보존해야 한다.

## 2. Network Topology

Reference model은 3개의 fully-connected computational layer로 구성된다.

| Layer | Input feature | Neuron | Activation |
|---|---:|---:|---|
| Layer 1 | 784 | 30 | sigmoid LUT |
| Layer 2 | 30 | 20 | sigmoid LUT |
| Layer 3 | 20 | 10 | sigmoid LUT |

Layer 3의 10개 출력은 `maxFinder`에 전달되며 가장 큰 score의 index가 class 0~9 결과가 된다. 비교는 strict `>`를 사용하므로 최대 score가 같은 경우 먼저 검사한 낮은 class index가 유지된다.

구현 계층:

```text
zyNet
├─ axi_lite_wrapper
├─ Layer_1 → neuron[30]
├─ Layer_2 → neuron[20]
├─ Layer_3 → neuron[10]
└─ maxFinder
```

## 3. Data Representation

- `include.v`의 `dataWidth`는 8이다.
- input, weight, bias 및 activation data path는 8-bit를 기준으로 한다.
- input과 activation은 signed Q1.7, weight는 signed Q4.4다.
- 각 neuron은 Q1.7 input과 Q4.4 weight를 곱해 Q5.11 product를 만들고, 16-bit `mul` 및 `sum` 경로에서 multiply-accumulate를 수행한다.
- product 누산과 bias 가산은 signed 16-bit 상한·하한에서 saturation 처리한다.
- accumulator는 Q5.11이며, Systolic Accelerator의 확장 accumulator는 같은 fractional 11-bit를 유지한 Q15.11이다.
- bias는 signed Q5.3이며 Q5.11 합에 더하기 전에 sign extension하고 8-bit left shift해 fractional bit를 정렬한다.
- sigmoid input은 Q5.5다. Reference RTL은 16-bit Q5.11 `sum`의 상위 10-bit인 `sum[15:6]`을 address로 사용해 `sigContent.mif` lookup table을 조회한다.
- sigmoid activation output은 signed Q1.7이다.

## 4. AXI-Stream Input

Reference DUT는 다음 입력을 제공한다.

| Signal | Width | 의미 |
|---|---:|---|
| `axis_in_data` | 8 | MNIST input feature |
| `axis_in_data_valid` | 1 | 입력 data 유효 표시 |
| `axis_in_data_ready` | 1 | DUT 수신 가능 표시 |

한 image는 784개의 feature를 순서대로 전달한다. 현재 `zyNet` 구현은 `axis_in_data_ready`를 항상 1로 구동한다. `tlast`와 `tkeep`은 제공하지 않으며 내부 연산이 입력 개수를 기준으로 layer 진행을 결정한다.

## 5. AXI-Lite Control/Result

Reference 구현의 AXI-Lite parameter는 다음과 같다.

| 항목 | 폭 |
|---|---:|
| `C_S_AXI_DATA_WIDTH` | 32 |
| `C_S_AXI_ADDR_WIDTH` | 5 |
| `AWPROT`, `ARPROT` | 3 |

32-bit는 AXI data channel 폭이고, 3-bit `AWPROT/ARPROT`는 AXI protection attribute 폭이다. 두 값은 같은 종류의 신호가 아니므로 32-bit와 3-bit의 차이 자체는 규격 오류가 아니다.

현재 ModelSim warning은 testbench 연결 폭 때문에 발생한다.

- `top_sim.v`의 `s_axi_awaddr`/`s_axi_araddr`는 32-bit지만 DUT address port는 5-bit다.
- testbench가 `s_axi_awprot`/`s_axi_arprot`에 연결한 unsized constant `0`은 32-bit로 해석되지만 DUT port는 3-bit다.
- 시뮬레이터가 상위 bit를 truncate하며 baseline 기능 결과는 정상 재현된다.

이 동작을 유지해야 한다는 뜻은 아니다. 후속 testbench에서는 address를 5-bit로 선언하고 protection constant를 `3'b000`으로 명시해 warning을 제거해야 한다.

## 6. Weight, Bias 및 Test Data

- Weight: `w_<layer>_<neuron>.mif`, 60개
- Bias: `b_<layer>_<neuron>.mif`, 60개
- Activation LUT: `sigContent.mif`
- Test vector: `test_data_0000.txt`~`test_data_0099.txt`

각 test vector는 784개 input entry와 마지막 expected label entry로 구성된다.

## 7. Verified Functional Baseline

- 대상 sample: 100개
- PASS: 99
- FAIL: 1
- Accuracy: 99.000000%
- 유일한 오분류: `test_data_0018.txt`, detected 8, expected 3
- compile errors: 0
- simulation errors: 0
- elaboration/simulation warnings: 65

## 8. 요구사항

- REQ-REF-001: DUT는 image당 784개 input feature를 순서대로 수신해야 한다.
- REQ-REF-002: network topology는 784→30→20→10이어야 한다.
- REQ-REF-003: Layer 1~3은 승인된 sigmoid LUT와 weight/bias를 사용해야 한다.
- REQ-REF-004: 최종 결과는 Layer 3 score 10개의 최대 index여야 한다.
- REQ-REF-005: 동일한 최대 score가 둘 이상이면 가장 낮은 class index를 결과로 선택해야 한다.
- REQ-REF-006: 100-sample baseline은 정확히 99 PASS / 1 FAIL과 99.000000%를 재현해야 한다.
- REQ-REF-007: `test_data_0018.txt`의 baseline 결과는 detected 8, expected 3이어야 한다.
- REQ-REF-008: AXI-Lite data width는 32-bit, address width는 5-bit, protection signal은 3-bit로 연결해야 한다.
- REQ-REF-009: 후속 testbench는 address 및 protection port-width warning을 발생시키지 않아야 한다.
- REQ-REF-010: numeric chain은 Input/Activation Q1.7 × Weight Q4.4 → Product/Accumulator Q5.11 + Bias Q5.3 → Sigmoid Input Q5.5 → Activation Output Q1.7이어야 한다.
- REQ-REF-011: neuron 연산은 signed 8×8 multiplication과 signed 16-bit saturating accumulation 및 bias addition 동작을 보존해야 한다.
- REQ-REF-012: Q5.3 bias는 accumulator 가산 전 8-bit left shift해 Q5.11로 정렬해야 한다.
- REQ-REF-013: sigmoid LUT address는 Q5.11 누산 결과의 `sum[15:6]`을 사용한 Q5.5여야 한다.

## 9. 알려진 제한

- input ready가 항상 1이어서 backpressure 동작을 검증하지 않는다.
- testbench는 단일 `top_sim.v` 구조이며 driver/monitor/scoreboard가 분리되어 있지 않다.
- AXI 연결 및 memory address width warning이 존재한다.
- MIF 기반 initialization은 ASIC 이식성을 보장하지 않는다.
- Q-format은 확정했지만 Systolic Accelerator의 26-bit Q15.11을 Q5.5로 축소할 때 범위 초과 처리 규칙은 별도 승인이 필요하다.

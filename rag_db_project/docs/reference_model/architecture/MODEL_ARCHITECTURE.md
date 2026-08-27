# FC-MLP Reference Architecture

- 문서 ID: REF-ARCH-001
- 상태: draft-for-review
- 기준일: 2026-08-27
- 구현 언어: Verilog
- DUT top: `zyNet`

## 기능

이 reference model은 MNIST 28×28 image의 784개 입력을 순차 수신하고 fully-connected MLP를 계산한 뒤 class 0~9를 반환한다.

```text
zyNet
├─ axi_lite_wrapper
├─ Layer_1: 784 → 30
│  └─ neuron[30] → Weight_Memory + Sig_ROM
├─ Layer_2: 30 → 20
│  └─ neuron[20] → Weight_Memory + Sig_ROM
├─ Layer_3: 20 → 10
│  └─ neuron[10] → Weight_Memory + Sig_ROM
└─ maxFinder: 10 scores → class
```

## 주요 설정

`include.v`의 원본 설정은 다음과 같다.

| 항목 | 값 |
|---|---:|
| data width | 8 bits |
| layers | 3 FC layers + hardmax output stage |
| Layer 1 | 784 inputs, 30 neurons, sigmoid |
| Layer 2 | 30 inputs, 20 neurons, sigmoid |
| Layer 3 | 20 inputs, 10 neurons, sigmoid |
| output | 10 inputs, hardmax |
| sigmoid address size | 10 bits |
| weight integer width | 4 bits |
| pretrained | enabled |

`top_sim.v` 안의 일부 `numNeurons` 배열 값은 오래된 설정 흔적을 포함하지만, `pretrained`가 정의되어 있으므로 runtime weight/bias configuration task는 실행되지 않는다. 실제 구조의 기준은 `include.v`와 `zyNet` 인스턴스 계층이다.

## 외부 인터페이스

- clock/reset: AXI clock과 active-low reset
- input: `axis_in_data`, `axis_in_data_valid`, `axis_in_data_ready`
- control/result: AXI-Lite
- completion: `intr`

정확한 timing, register map 및 fixed-point 산술 규칙은 후속 reference-model specification에서 requirement ID와 함께 승인해야 한다.

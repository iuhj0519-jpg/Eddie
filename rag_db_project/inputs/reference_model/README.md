# FC-MLP Reference Model

이 디렉터리는 MNIST FC-MLP 가속기의 기능 및 수치 기준이 되는 원본 Verilog 모델과 학습 파라미터를 보관한다. 이 모델은 이후 `systolic_prototype`을 생성할 때 입력 근거로 사용하며, 생성 결과물은 이 디렉터리에 저장하지 않는다.

## 모델 구성

- 입력: 28×28 MNIST image, 784개의 8-bit 값
- 네트워크: 784→30→20→10 fully-connected MLP
- Layer 1~3 activation: sigmoid LUT
- 출력: `maxFinder`가 선택한 class 0~9
- 설정: `model/rtl/include.v`
- DUT top: `zyNet`
- testbench: `model/tb/top_sim.v`

## 디렉터리

| 경로 | 내용 |
|---|---|
| `model/rtl/` | `zyNet`, AXI-Lite wrapper, Layer 1~3, neuron, activation 및 weight memory Verilog |
| `model/tb/` | 원본 단일 testbench `top_sim.v` |
| `weights/` | `w_<layer>_<neuron>.mif`, 총 60개 |
| `biases/` | `b_<layer>_<neuron>.mif`, 총 60개 |
| `activation/` | sigmoid lookup table `sigContent.mif` |
| `testdata/` | baseline에서 사용하는 `test_data_0000.txt`~`test_data_0099.txt` |
| `scripts/` | ModelSim 재현 스크립트 |

Verilog의 `$readmemb` 경로가 파일명만 사용하므로, 재현 스크립트는 RTL·MIF·test data를 임시 실행 디렉터리에 평탄화한 뒤 시뮬레이션한다. 원본 디렉터리 구조는 변경하지 않는다.

## 검증된 baseline

- 실행일: 2026-08-27
- Simulator: ModelSim - Intel FPGA Edition 10.5b
- Compile: error 0, warning 0
- Elaboration/simulation: error 0, warning 65
- 테스트: 100개
- 결과: 99 PASS / 1 FAIL
- Accuracy: 99.000000%
- 오분류: `test_data_0018.txt`, detected 8, expected 3
- 종료 simulation time: 873235 ns

65개 경고는 주로 AXI address/protection 및 weight-memory address 연결의 port-width 불일치다. baseline 기능 결과는 재현되었지만, 경고는 향후 사양화와 RTL 검토 대상이다.

## 실행

Git Bash에서 저장소 루트를 기준으로 실행한다.

```bash
bash rag_db_project/inputs/reference_model/scripts/run_modelsim.sh
```

기본 ModelSim 경로가 다르면 `MODELSIM_BIN`을 지정한다.

```bash
MODELSIM_BIN=/c/intelFPGA/18.1/modelsim_ase/win32aloem \
  bash rag_db_project/inputs/reference_model/scripts/run_modelsim.sh
```

결과 로그는 Git에서 제외되는 `.sim/` 아래에 생성된다. 공식 baseline의 근거와 원천 출처는 `../../docs/reference_model/`에서 관리한다.

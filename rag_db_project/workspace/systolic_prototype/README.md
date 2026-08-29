# Systolic Prototype

이 디렉터리는 승인된 Reference Model과 Systolic Accelerator SPEC만을 근거로 생성한 1차 RTL 결과다. Historical Baseline, 외부 Web 검색, 외부 LLM/API는 생성 근거로 사용하지 않았다.

## Architecture

- `zyNet`: Reference Model과 동일한 AXI Stream, AXI-Lite, `intr` Top Interface
- `input_buffer`: Image-Major 순서의 5×784 입력을 5개 Bank에 저장
- `systolic_array`: 25개 PE로 구성된 5×5 Output-Stationary Systolic Array
- `systolic_controller`: `IDLE`, `RUN`, `DONE_STATE`와 `start/busy/done` Handshake, `K+13` 실행 구간
- `weight_sram`, `bias_sram`: Layer/Group에 맞는 5개 Neuron의 MIF 데이터를 공급
- `activation_unit`: Q15.11 Accumulator에 Q5.3 Bias를 더하고 Q5.5 범위로 Saturation한 뒤 Sigmoid LUT를 조회
- `global_buffer`: Layer 1 결과를 Region A, Layer 2 결과를 Region B에 저장하는 Ping-Pong Buffer
- `max_finder`: Layer 3 Activation을 별도 Input Register에 저장하지 않고 열 단위로 직접 비교하며, 동점은 낮은 Class를 유지
- `dnn_scheduler`: Batch 입력부터 세 Layer, 12개 Group, 결과 Read 완료까지 전체 상태 전이 제어
- `axi_lite_result_interface`: Byte Address `0x08`에서 5개 Class를 순차 Read하고 다섯 번째 Read 후 다음 Batch를 준비

## Directory Roles

| Directory | Role |
|---|---|
| `rtl/` | 합성 대상 SystemVerilog RTL |
| `tb/` | 20 Batch, 100 Image 회귀 Testbench |
| `memory/` | 승인된 Weight 60개, Bias 60개, Sigmoid LUT 1개 |
| `scripts/` | ModelSim Compile/Simulation Script |
| `reports/` | 구현 근거와 검증 결과 |

## Core Dataflow

각 Tile에서 행은 Image 0~4, 열은 현재 Group의 Neuron 5개를 나타낸다. Input/Activation은 행의 왼쪽에서 오른쪽으로, Weight는 열의 위에서 아래로 이동한다. 각 PE는 곱을 26-bit Q15.11 Partial Sum에 누적한다. Controller의 완료 뒤 Activation Unit이 열 하나씩 5개 Image를 병렬 처리한다.

Layer 1/2 Activation만 Global Buffer에 저장한다. Layer 3 Activation은 MaxFinder로 직접 전달되므로 독립적인 Capture Register나 MaxFinder Input Register를 추가하지 않았다. 결과 5개는 `0x08`에서 Image 0부터 Image 4까지 읽으며, 다섯 번째 Read Handshake가 결과와 Read Index를 초기화한다. `intr`는 Batch당 한 Clock만 발생한다.

## Run

Git Bash에서 다음을 실행한다.

```bash
cd /c/Users/iuhj0/Eddie_rag_generation/rag_db_project/workspace/systolic_prototype
bash scripts/run_modelsim.sh
```

검증된 결과는 `reports/IMPLEMENTATION_AND_VERIFICATION.md`에 기록되어 있다.

# ModelSim Reference Baseline

- 문서 ID: REF-SIM-001
- 상태: verified
- Simulator: ModelSim - Intel FPGA Edition 10.5b
- 설치 기준: Intel FPGA 18.1
- Testbench top: `top_sim`

## 실행 대상

- design/include Verilog: 11개
- testbench: `top_sim.v` 1개
- weight MIF: 60개
- bias MIF: 60개
- activation LUT: 1개
- test vector: 100개

## 재현 명령

```bash
bash rag_db_project/inputs/reference_model/scripts/run_modelsim.sh
```

스크립트는 상대 `$readmemb` 경로를 보존하기 위해 실행 전용 `.sim/<run_id>` 디렉터리에 입력 파일을 평탄화한다.

## 결과

| 항목 | 결과 |
|---|---:|
| compile errors | 0 |
| compile warnings | 0 |
| simulation errors | 0 |
| elaboration/simulation warnings | 65 |
| samples | 100 |
| correct | 99 |
| incorrect | 1 |
| accuracy | 99.000000% |
| final simulation time | 873235 ns |

유일한 오분류:

```text
Filename: test_data_0018.txt
Sample sequence: 19
Detected number: 8
Expected number: 3
```

마지막 출력:

```text
100. Accuracy: 99.000000, Detected number: 9, Expected: 09
Accuracy: 99.000000
```

## 알려진 경고

65개 경고는 주로 다음 port-width 불일치다.

- `top_sim`의 32-bit AXI address/protection 연결과 `zyNet`의 5-bit/3-bit port
- `neuron`과 `Weight_Memory` 사이 read-address width
- `zyNet`과 `maxFinder` 사이 valid width

이 결과는 기존 동작의 baseline을 기록한 것이며, 경고를 승인하거나 올바른 설계라고 판정한 것은 아니다. 후속 이식 SPEC에서 각 width를 명시하고 prototype 검증 시 warning regression을 별도 평가한다.

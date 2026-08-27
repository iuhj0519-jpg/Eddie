# Reference Model Documentation

이 문서 계층은 `inputs/reference_model`에 저장된 원본 FC-MLP Verilog 모델을 설명한다. `dnn_optimization_project/docs`와 독립적으로 관리하며, 최초 systolic prototype 생성 단계의 승인 입력 문서가 된다.

## 문서 구성

| 경로 | 역할 |
|---|---|
| `architecture/MODEL_ARCHITECTURE.md` | 모델 계층, 데이터 흐름, 주요 parameter |
| `data/MEMORY_AND_TESTDATA.md` | weight/bias/LUT/test vector 형식과 파일 배치 |
| `simulation/MODELSIM_BASELINE.md` | 실행 환경, 명령, 99/1 결과와 알려진 경고 |
| `provenance/SOURCE_PROVENANCE.md` | 원본 경로, 선택·제외한 파일과 출처 정책 |

현재 문서는 원본 코드 및 실제 ModelSim 실행으로 확인한 As-Is 사실을 기록한다. Systolic array로의 이식 요구사항은 `inputs/specifications/02_systolic_accelerator`에서 별도로 정의해야 한다.

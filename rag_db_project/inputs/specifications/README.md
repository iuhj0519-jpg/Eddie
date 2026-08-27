# Design Specifications

이 디렉터리는 RAG Agent의 단계별 코드 생성과 검증에 사용하는 규범적 문서를 관리한다.

| 단계 | 디렉터리 | 역할 |
|---|---|---|
| 1 | `01_reference_model/` | legacy FC-MLP 기능, 인터페이스, 수치 및 baseline 계약 |
| 2 | `02_systolic_accelerator/` | 5×5 OS systolic array와 controller 요구사항 |
| 3 | `03_architecture_optimization/` | buffer, overlap, parameter화 등 최적화 요구사항 |
| 4 | `04_verification/` | testcase, assertion, coverage 및 회귀 요구사항 |

`02_systolic_accelerator`는 이식 과정의 작업 기록이 아니라 구현해야 할 systolic accelerator 아키텍처 자체를 정의한다.

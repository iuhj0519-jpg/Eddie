# Experiments

이 계층은 실행 원본이 아니라 실험의 판단과 재현 정보를 저장한다.

| 경로 | 역할 |
|---|---|
| `prototype_generation/` | Systolic Prototype 생성 Run과 Evidence Freeze 기록 |
| `optimization_generation/` | Optimized Accelerator 생성 Run과 승인 근거 |
| `automation_loop/` | 문제 탐지, Diagnosis, 승인, Patch, 재검증의 반복 이력 |
| `comparative_evaluation/` | 검증이 끝난 모델 간 성능 비교 |
| `verification_generation/` | 향후 검증 자산 생성 단계의 기록 |

`run_###` 번호는 특정 폴더 안에서만 증가한다. 원본 Log와 Report는 `artifacts/`에 두고, 여기에는 Artifact 경로와 Hash를 인용한 판정만 둔다.


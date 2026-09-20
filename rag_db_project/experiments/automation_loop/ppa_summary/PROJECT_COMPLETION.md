# 승인 기반 반자동화 Loop — 프로젝트 종료 및 통합

## 종료 승인과 통합 범위

개발자 요청 원문:

> 이제 승인 기반 반자동화 Loop 시스템에 대한 프로젝트가 완료되었습니다. 추가 디벨롭이 있을 시 나중에 다시 할 수 있기도 하겠지만, 우선은 분석이 끝났습니다. 모든 적용 부분을 Git에 push까지 완료하고 임시 프로젝트 git을 메인 Project_Git에 통합해주세요

- 통합 대상: `iuhj0519-jpg/Eddie` 저장소의 `Project_Git` 브랜치. `main` 브랜치나 원본 RTL을 대체하는 작업이 아니다.
- 개발 결과 브랜치: `rag/optimized-accelerator-v1`, 검증 결과 commit `459d1816b73538bfb9872bf91102ba9a73fad25a`.
- 기존 통합 브랜치의 별도 변경 `af205a1`(StallDistributor)을 보존한다. 개발 브랜치와 실패/승인/재검증 이력도 삭제하지 않는다.
- 이번 종료는 프로젝트 분석과 결과 패키지 통합이다. 승인 SPEC의 조건 완화, 미검증 항목의 PASS 처리, bitstream/보드 검증 완료 판정은 하지 않는다.
- 통합 상태에서 자동화 회귀 테스트 57개를 재실행하여 모두 통과했다. 실행 코드·입력 및 검증 원본은 결과 commit과 동일하게 유지한다.

## 결과와 증거 위치

| 항목 | 위치 / 결과 |
|---|---|
| 검토한 RTL/TB/메모리 | `workspace/rag_debug_output_001/` |
| 최종 수치·변경 설명 | `workspace/rag_debug_output_001/reports/diagnosis.md`, `design_evidence.md` |
| 승인 SPEC | `experiments/automation_loop/optimized_accelerator/spec_versions/spec_002/` |
| 성공 실행 | `experiments/automation_loop/optimized_accelerator/run_004/` |
| 도구 원본 | `artifacts/{verification,synthesis,implementation}/optimized_accelerator/run_004/` |
| 변경 전 동일 절차 재실행 | 같은 artifacts target의 `baseline_001/` |
| 후속 보완안 / 승인 대기 | `experiments/automation_loop/optimized_accelerator/analysis_006/spec_change_proposal.md`, `requirements.yaml`, `approval.yaml` |
| RTL 결과 | LUT 1,199 / FF 714 / DSP 25 / BRAM Tile 12.5 / Weight RAMB36 10 |
| Timing / 기능 | WNS +0.120 ns, TNS 0; 99% Accuracy, 원본과 100개 예측 동일; 161,735 Cycle |
| 전력 | 후보 SAIF 0.169 W, Medium confidence. 원본 자동화 재실행은 0.614 W이며 기존 사용자 보고서의 0.607 W와 다른 실행 |
| 에너지 | 수집 구간 1,617,525 ns; 0.169 × 1,617,525 / 1,000 = 273.361725 µJ, 실측 아님 |

자동 조건 16개 PASS와 사람 검토 조건 30개 UNKNOWN 기록을 보존한다. I/O 제약·DRC, reset/pipeline, 무작위 stall/reset 검증 및 SAIF 직접 매칭 한계는 향후 필요시 별도 승인 후 다룬다. 후속 실행을 이번 통합으로 자동 승인하지 않는다.

## GUI 확인 이후 수정된 체크포인트

통합 직전 로컬 `run_004/post_route.dcp`의 SHA-256이 검증 당시 Git 스냅샷과 달랐다. 파일 수정 원인을 단정하거나 새 검증 결과로 간주하지 않는다.

- 검증 당시 원본: `artifacts/implementation/optimized_accelerator/run_004/post_route.dcp`
- GUI 확인 이후 로컬 수정본 보관: `artifacts/implementation/optimized_accelerator/gui_review_001/post_route.dcp`
- 두 해시 및 제한: `gui_review_001/README.md`

검증 원본은 덮어쓰지 않는다. GUI 수정본에 기존 SAIF/Timing 결과가 그대로 대응한다고 주장하지 않는다.

## GUI 안내 정정과 지표 정의

- 자원 GUI: `report_utilization -name debug_utilization`. Vivado 2022.1에서는 `-hierarchical`과 `-name`을 동시에 쓰지 않는다. 계층별 텍스트 출력은 별도 `report_utilization -hierarchical`로 실행한다.
- Simulation 소스는 `workspace/rag_debug_output_001/rtl` 및 `tb/top_sim.sv`다. Design Top은 `zyNet`, Simulation Top은 `top_sim`. XSim 작업 디렉터리의 `memory/`와 `../../inputs/reference_model/testdata/`를 준비해야 한다.
- `.automation_debug/.../analysis_005/.../optimized_accelerator`는 패치된 격리 실행본의 역사적 경로다. 공개한 결과 코드와 해시를 대조했으며, 경로 이름이 원본 실행임을 뜻하지 않는다.
- `AXI_BACKPRESSURE_CYCLES=77977`은 입력 `VALID && !READY`인 대기 Cycle이다. 정상 전송 Cycle, Compute Cycle 또는 overlap Cycle과 같지 않다.
- SAIF 적용 전에도 활동을 가정한 동적 전력이 포함된다. 0.174 → 0.169 W는 같은 회로의 활동 정보 갱신 결과이지, 추가 RTL 최적화 효과가 아니다.

## 향후 재개

`analysis_006`의 근거와 SPEC 보완안을 재검토하여 새 승인을 기록한 뒤 다음 Loop를 실행한다. 새 최적화 결과는 `workspace/rag_debug_output_002`부터 보관하고 이번 결과·원본 입력·승인 SPEC을 덮어쓰지 않는다.

# Automated Verification And Debugging Loop

## 최신 최종 검토: 2026-09-08

[23개 Finding·SPEC 대조·Power 절차·구축 요약](final_review_20260908/diagnosis.md)을 확인한다.
승인 대상은 `optimized_accelerator/review_20260908/approval.yaml`이며 모두 pending이다.
이전 review_20260907은 이전 Runtime/Config에 바인딩되어 있어 승인 대상으로 사용하지 않는다.
승인 SPEC과 RTL은 변경하지 않았다. 아래 2026-09-07 설명은 구축 이력이다.

## 2026-09-07 탐지·실행 범위 보완

기존 4개 Finding은 예시 결과이지 탐지 허용 목록이 아니다. **Weight 메모리 접근 구조, 주소 계산,
큰 선택 회로, 파이프라인 및 Fanout**을 포함하여 모든 허용된 보고서와 미분류 경고를 검토한다.
추가 경로/DRC 탐지와 UNKNOWN coverage, 실제 도구 어댑터, 다음 Run 생성은
[실행 매뉴얼](../../rag/automation/README.md)을 따른다. 탐지의 완전성을 보장하지 않으며 측정이 없는 항목을 PASS로 처리하지 않는다.

review_20260907은 새로운 Post-Route 근거의 승인 전 검토이며 기존 run_001/run_002를 수정하지 않는다.
모든 Finding은 승인 대기다. 사용자가 Finding별 결정을 내리고 SPEC Requirement ID를 연결하기 전에는
Run is not approved for patch generation. 다음 run_003은 승인된 패치의 도구 실행 결과로 생성한다.

자동화 자체의 Fixture 테스트와 미수정 RTL 도구 실행은 artifacts/automation_system_tests에서 구분한다.
자동화 테스트 PASS는 DUT PPA/Timing 통과 또는 사용자 설계 승인과 다르다.

이 디렉터리는 현재 Workspace에서 발생한 문제를 탐지하고, 근거와 수정 이력을 Run 단위로 보존한다. 시행착오 기반 답변 제공은 별도 단계가 아니라 이 Loop가 축적한 검증 이력을 검색하는 기능이다.

## Algorithm

1. 승인 SPEC, Manifest, Workspace 입력의 Hash와 접근 정책을 확인한다.
2. Compile, Simulation, Assertion, Accuracy, Cycle, Vivado Timing·Power·Utilization·RAM 보고서를 `artifacts/`에서 수집한다.
3. 보고서를 공통 Schema로 정규화하고 모든 Detector를 실행한다.
4. 각 문제를 `SPEC Requirement ID → 실패 증거 → 수정 내용 → 재검증 결과` 체인으로 기록한다.
5. 검증된 과거 Workspace Run을 검색해 원인 후보와 수정 방향을 보강한다. 근거가 없으면 `unknown`으로 남긴다.
6. `approval.yaml`을 생성하고 사람의 승인 전에는 RTL, SPEC, Test 기대값을 변경하지 않는다.
7. 승인된 Finding만 격리 Debug Workspace에서 Patch 후보로 만든다.
8. Compile → Simulation → Protocol/Accuracy Regression → Synthesis/Implementation을 다시 실행한다.
9. 새 Artifact를 분석해 해결·Regression·새 Finding을 기록한다. Acceptance Criteria를 만족할 때까지 반복한다.

## Directory Contract

```text
experiments/automation_loop/
├── README.md
├── run_template/run_manifest.yaml
└── <target>/run_###/
    ├── run_manifest.yaml
    ├── analysis_result.json
    ├── findings.yaml
    ├── diagnosis.md
    ├── approval.yaml
    ├── spec_change_proposal.md
    ├── proposed_patch.diff
    └── revalidation_result.json
```

원본 Tool Log와 Report는 `artifacts/`에만 둔다. `experiments/`에는 원본에서 무엇을 판단하고 어떤 결정을 내렸는지를 둔다. `verification/`에는 반복 사용 가능한 Testbench, Assertion, Regression 정의를 둔다.

## Human Gate

읽기·수집·분석·문서화는 자동이다. RTL/SPEC/Test 기대값 변경, FSM·AXI·Fixed-Point·Memory 구조·Pipeline 변경은 사람 승인 후에만 허용한다. 승인 후에도 기존 Workspace를 즉시 덮어쓰지 않고 격리 공간에서 전 회귀 검증을 통과한 Patch만 승격 후보가 된다.

Historical Baseline은 최종 비교에만 사용한다. 자동 분석, 원인 추적, 답변 근거, Patch 생성 및 Debugging에는 사용하지 않는다.

## Commands

Repository의 `rag_db_project`에서 실행한다.

```bash
python rag/automation/run_loop.py analyze --target optimized_accelerator
python rag/automation/run_loop.py status --target optimized_accelerator
python rag/automation/run_loop.py approve --target optimized_accelerator --run-id run_002 --finding-id PPA-DSP-001 --decision approved --requirement-id REQ-PPA-DSP-001
python rag/automation/run_loop.py resume --target optimized_accelerator --run-id run_002
```

`analyze`가 Finding을 만들면 종료 코드 2와 함께 승인 대기 상태가 된다. `resume`은 승인이 없으면 실패하며, 승인 후에도 Agent가 승인 근거만으로 `proposed_patch.diff`를 만들 때까지 Patch를 적용하지 않는다.

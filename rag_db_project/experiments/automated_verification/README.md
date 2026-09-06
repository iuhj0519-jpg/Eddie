# Automated Verification And Debugging

이 디렉터리는 자동 검증 실험의 정책과 Run 정의를 보존한다. 실행 결과 자체는 `artifacts/verification/`에 저장한다.

자동화 순서는 다음과 같다.

1. 승인 SPEC과 Evidence Manifest의 Hash를 검증한다.
2. 허용된 RTL, TB, Memory만 Compile한다.
3. Batch Simulation과 Protocol Assertion을 실행한다.
4. 로그를 정형화해 `verification_result.json`을 생성한다.
5. 실패를 SPEC Requirement와 연결하여 `diagnosis.md`와 수정안을 생성한다.
6. 위험도가 낮은 수정만 자동 적용하고, FSM·Protocol·Q-format 변경은 사람의 승인을 기다린다.
7. 승인된 Patch를 적용한 뒤 전체 Regression을 다시 실행한다.
8. Acceptance Criteria를 만족하거나 반복 제한에 도달하면 종료한다.

한 줄 실행 명령은 Python Orchestrator가 제공하며, Testbench는 Stimulus, Assertion과 판정만 담당한다. Historical Baseline은 비교 단계에서만 사용하며 코드 생성·자동 Debugging의 검색 근거로 사용하지 않는다.

## 현재 단계: Experience QA

자동 Patch Loop를 활성화하기 전에 현재 Workspace에서 발생한 시행착오를 검색 가능한 경험으로 고정한다.

- `artifacts/`: Compile, Simulation, Synthesis와 PPA 도구가 생성한 원본 증거
- `experiments/automated_verification/<target>/run_###/`: 원본 증거에서 판정한 Finding, Diagnosis, 수정 방향과 승인 상태
- `verification/`: 수정 이후의 Regression과 최종 검증 결과
- `rag/config/experience_index.yaml`: 시행착오 질문을 Run과 Artifact 근거에 연결하는 검색 설정

현재 단계는 관측 결과와 재설계 방향을 답변하지만 RTL을 자동 수정하지 않는다. `pending_human_approval` Finding은 검증된 해결책처럼 표현하지 않으며, 승인 후 다음 Run에서 Patch와 재검증 결과를 생성한다.

모든 Finding은 다음 추적 체인을 따른다.

```text
Finding ID → 원본 Artifact → 원인 가설 → 수정 방향 → 사용자 승인 → Patch → 재검증 결과
```

향후 자동화 Loop는 Artifact Parser가 모든 Compile, Protocol, Accuracy, Cycle, Timing, Area, BRAM, DSP와 Power 기준을 검사하여 누락 없이 Finding을 생성하는 방식으로 확장한다.

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

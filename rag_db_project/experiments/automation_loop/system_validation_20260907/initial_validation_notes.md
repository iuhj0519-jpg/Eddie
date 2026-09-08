# Automation System Validation — 2026-09-07

이 기록은 자동화 실행 기반의 검증이며 실제 최적화 패치 승인 또는 DUT Timing PASS가 아니다.

## 실제로 발견하고 수정한 자동화 결함

첫 ModelSim 테스트는 Compile 성공 후 Simulation에서 100개 입력 파일을 찾지 못해 0 PASS/100 FAIL로 실패했다.
기존 TB가 `../../inputs/reference_model/testdata`를 사용하지만 격리 복사본에는 RTL/TB/Memory만 있었기 때문이다.
TB나 Golden은 수정하지 않았다. 격리 구조를 `project/workspace/<target>`과 `project/inputs/reference_model/testdata`로
맞추고 테스트 데이터까지 복사·해시 검증하도록 실행기를 수정했다.

재실행에서 두 모델 모두 99 PASS/1 FAIL, Golden 일치, Error/Warning 0이 확인되었다.
Optimized는 TOTAL_INFERENCE_CYCLES=161735, AXI_BACKPRESSURE_CYCLES=77977이다.
원본 실패/재실행 로그 및 실제 합성 실행 상태는 `artifacts/automation_system_tests/run_001/`에서 확인한다.

## 테스트 구분

- test_automation.py: 미승인 차단, 증거/설정 변경 시 승인 무효화, SPEC ID 누락, 경로 이탈,
  Compile 실패 후 Simulation/Synthesis 생략, 후속 Run 미승인 생성, 도구 성공과 증거 부족 구분,
  이전 샘플 예측 회귀, 반복/횟수 제한, 원본 불변, min/max Timing 파싱 등을 Fixture로 검증한다.
- smoke_tools.py: 사용자 Workspace를 변경하지 않고 복사본에서 실제 ModelSim/Vivado 어댑터를 실행한다.
- synthetic Fixture에서의 approved 표시는 테스트 전용이며 사용자 설계 승인 기록과 무관하다.

## 승인과 종료 경계

현재 모든 생산 Finding은 미승인이다. run_001/run_002는 보존하고 review_20260907로 최신 근거를 검토한다.
실제 생산 패치의 run_003은 사용자 승인 후 생성한다. 시스템 테스트 성공만으로 이를 미리 생성하지 않는다.
합성 성공은 Post-Route Timing Closure와 다르다. PE 활동·완전한 Protocol coverage 및 실측 Power는
현재 TB/자료에서 입증되지 않았으므로 UNKNOWN이다. 최종 Workspace 반영은 별도 사용자 수락이 필요하다.

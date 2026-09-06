# Automation Loop Runtime

이 Python 계층은 Testbench 안에 Debugging 로직을 넣는 방식이 아니라 외부 Orchestrator로 동작한다. Testbench는 Stimulus와 Assertion을 담당하고, Orchestrator는 Tool 실행·로그 수집·분석·승인 Gate·반복을 담당한다.

- `parsers.py`: Vivado 및 Simulation 결과를 공통 Metric으로 변환
- `detectors.py`: 설정 기반으로 기능, Protocol, Timing, Power, Resource, Memory, DSP 문제를 모두 탐지
- `run_loop.py`: Run 생성, 승인 기록, 격리 Patch 적용과 재검증 명령 실행
- `../config/automation_loop.yaml`: Acceptance Criteria, 임계값, Tool 명령, 반복 제한

Patch의 의미를 판단하고 SystemVerilog를 생성하는 작업은 AI Agent가 담당한다. Python은 `approval.yaml`이 승인 상태인지 확인하고, Agent가 만든 `proposed_patch.diff`를 격리 공간에만 적용한다. 따라서 한 줄 명령으로 전체 과정의 실행은 가능하지만 설계 변경은 사람 승인 없이 진행되지 않는다.


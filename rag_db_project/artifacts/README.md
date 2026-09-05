# Artifacts

이 디렉터리는 도구가 생성한 원본 실행 결과를 보존한다. 설계 근거와 생성 소스는 포함하지 않으며, 동일한 입력과 실행 조건으로 결과를 재현할 수 있어야 한다.

- `synthesis/`: Vivado Synthesis 보고서와 실행 요약
- `verification/`: Compile, Simulation, Assertion, Accuracy 및 Debugging 결과

각 실행은 `run_###`으로 구분한다. 보고서와 로그는 Git에 저장하고, 재생성 가능한 대용량 Checkpoint와 Waveform은 기본적으로 저장하지 않는다. 필요한 경우 Git LFS를 사용하고 SHA-256을 Run Manifest에 기록한다.

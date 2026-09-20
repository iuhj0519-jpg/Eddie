# Artifacts

도구가 직접 생성한 원본 실행 증거를 보존한다. 판단과 수정 이력은 `experiments/automation_loop/`에 둔다.

| 경로 | 역할 |
|---|---|
| `synthesis/<target>/run_###/` | Vivado Utilization, Hierarchical Utilization, RAM, Timing, Power Report와 Run Manifest |
| `implementation/<target>/run_###/` | Place/Route 이후 Timing, Power, Utilization, Route Status와 DRC 원본 |
| `verification/<target>/run_###/` | Compile/Elaboration Log, Simulation Log, Protocol Assertion, Accuracy/Cycle 결과 |

Run Manifest에는 Tool Version, Device, Clock Constraint, Source Hash와 실행 명령을 기록해야 한다. 큰 Checkpoint와 Waveform은 기본적으로 Git에 넣지 않고 필요 시 외부 보관 위치와 SHA-256만 기록한다.

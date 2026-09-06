# Verification Artifacts

Automation Loop가 Compile과 Simulation을 실제 실행했을 때 생성된 원본만 저장한다.

```text
verification/<target>/run_###/
├── compile.log
├── simulation.log
├── protocol_assertions.log
├── verification_result.json
└── run_summary.yaml
```

- `compile.log`: Compiler, Elaboration, Warning/Error와 종료 코드
- `simulation.log`: 100개 MNIST 추론 출력, Timeout과 Testbench 판정
- `protocol_assertions.log`: AXI Stream, `start/busy/done`, Batch당 `intr` Assertion 결과
- `verification_result.json`: 99 PASS/1 FAIL, Accuracy 99.0%, Cycle, Peak Active PE 등 정규화 Metric
- `run_summary.yaml`: Tool Version, 실행 명령, Source Hash, Exit Code와 위 파일들의 SHA-256

현재 Target 폴더의 `.gitkeep`은 출력 위치만 예약한다. 해당 Tool을 실행하지 않은 Run에는 빈 Log나 가짜 PASS 결과를 만들지 않는다. Diagnosis, 승인과 Patch는 원본 Artifact가 아니라 판단 기록이므로 `experiments/automation_loop/<target>/run_###/`에 둔다.

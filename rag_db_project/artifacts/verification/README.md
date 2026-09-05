# Verification Artifacts

자동 검증과 Debugging Loop가 생성한 원본 증거를 대상별·Run별로 저장한다.

```text
verification/
├─ systolic_prototype/run_###/
└─ optimized_accelerator/run_###/
```

각 Run에는 다음 결과를 저장할 수 있다.

- `compile.log`: RTL Compile 결과
- `simulation.log`: Batch Simulation 출력
- `verification_result.json`: 기계 판독 가능한 Pass/Fail, Accuracy, Cycle 결과
- `protocol_assertions.log`: AXI와 `start/busy/done`, `intr` 위반 기록
- `diagnosis.md`: SPEC Requirement와 실패 증거를 연결한 원인 분석
- `proposed_patch.diff`: 적용 전 검토할 수정안
- `run_summary.yaml`: 실행 입력, 상태, 산출물과 Hash

Waveform은 크기가 크므로 실패 재현에 필요한 Run만 보존한다.

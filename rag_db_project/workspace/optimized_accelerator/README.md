# Optimized Accelerator

이 디렉터리는 승인된 `OPT-SPEC-001 version 1.0`과 동결된 Optimization RAG 근거만 사용해 생성한 FC-MLP MNIST 가속기 최적화 결과물이다. 5×5 Output-Stationary Systolic Array, Reference Model의 AXI Stream/AXI-Lite 프로토콜, 고정소수점 연산과 797/43/33 Controller cycle을 유지한다.

## Optimization Summary

- `input_buffer`와 `global_buffer`의 역할을 5-Bank `unified_buffer`로 통합했다.
- Layer 1 입력영역과 Layer 1/2 결과용 중간영역 두 구간을 동일 Bank Array 안에 배치한다.
- Layer 1의 마지막 output group이 feature를 읽은 뒤에만 해당 입력주소를 다음 Batch에 반환한다.
- 다음 Batch의 AXI Stream은 현재 Batch compute와 중첩되며, 아직 안전하지 않은 주소에서는 `axis_in_data_ready`로 backpressure한다.
- Activation write가 AXI write보다 우선하며 Bank당 최대 1-read/1-write만 발생하도록 구성했다.

## Directory Roles

| Directory | Role |
|---|---|
| `rtl/` | Unified Buffer, Scheduler, Systolic Controller와 주변 RTL |
| `tb/` | 100개 MNIST 연속 Streaming, AXI-Lite 결과 read와 assertion |
| `memory/` | 승인된 Weight, Bias와 Sigmoid LUT MIF |
| `scripts/` | ModelSim compile/simulation 자동화 |
| `reports/` | 구조 선택 근거와 검증 결과 |

## Verification Result

- ModelSim compile: 0 errors, 0 warnings
- MNIST: PASS 99, FAIL 1, Accuracy 99.0%
- Interrupt: Batch당 1-cycle pulse, 총 20회
- Systolic Controller: Layer별 group당 797/43/33 cycle
- End-to-end inference: 161,735 cycle
- AXI backpressure: 77,977 cycle

실행 방법은 다음과 같다.

```bash
cd /c/Users/iuhj0/Eddie_rag_generation/rag_db_project/workspace/optimized_accelerator
bash scripts/run_modelsim.sh
```

PPA의 Area/Fmax/Power 수치는 합성 전에는 확정할 수 없다. 구조적 비교와 시뮬레이션 성능은 `reports/IMPLEMENTATION_AND_VERIFICATION.md`에 기록했다.

# Optimized Accelerator Run 001 PPA Diagnosis

## 상태

Vivado Synthesis 보고서를 정형 규칙으로 검사하여 두 개의 개선 필요 항목을 검출했다. 이 문서는 관측 결과와 수정 후보를 기록하며, 승인된 SPEC이나 RTL을 자동으로 변경하지 않는다.

## PPA-DSP-001 — PE 병렬성과 DSP Mapping

- 기대 구조: 5×5 Systolic Array, 25개 PE
- 관측 결과: DSP48 5개
- 원본 근거: `artifacts/synthesis/optimized_accelerator/run_001/utilization.rpt`
- 판정: 25개 PE가 각각 독립적인 DSP MAC으로 Mapping됐다고 입증할 수 없다.

DSP 개수는 PE Utilization 그 자체가 아니다. 후속 검증에서는 합성된 DSP48 개수와 함께 Cycle별 유효 MAC 수행 PE 수를 측정해야 한다.

검토할 수정 후보는 Signed Operand Width, 곱셈 Coding Pattern, Resource Sharing, DSP Inference 속성과 PE별 MAC 경계다. 이 변경은 Architecture와 Pipeline에 영향을 줄 수 있으므로 사람 승인 전에는 적용하지 않는다.

## PPA-WEIGHT-001 — Weight SRAM 병목

- 전체 LUT: 18,059
- Weight SRAM LUT: 13,930, 전체의 약 77.14%
- Weight SRAM F7/F8 MUX: 6,345/1,615
- Weight SRAM BRAM: 0
- 원본 근거: `artifacts/synthesis/optimized_accelerator/run_001/utilization_hierarchical.rpt`

Weight 저장 구조가 Block RAM보다 LUT와 깊은 MUX Network 중심으로 구현됐다. 이는 Area, Routing, Setup Timing과 확장성 병목 후보다.

검토할 수정 후보는 Synchronous Read Template, Memory Initialization 방식, Bank/Port 구조, Read Latency와 Controller 정렬이다. Interface와 Cycle이 바뀔 수 있으므로 사람 승인 전에는 적용하지 않는다.

## Human Gate

각 Finding은 다음 순서를 따라야 한다.

```text
SPEC Requirement ID → 실패 증거 → 수정 제안 → 사람 승인 → 격리 Patch → 재검증 결과
```

현재 상태는 `pending_human_approval`이며 RTL Patch는 생성하거나 적용하지 않았다.

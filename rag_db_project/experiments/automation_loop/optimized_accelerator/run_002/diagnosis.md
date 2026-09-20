# optimized_accelerator run_002 Diagnosis

이 문서는 도구가 수집한 원본 증거에서 자동 생성되었습니다.

## PPA-DSP-001

- Category: `architecture_parallelism`
- Severity: `high`
- State: `detected_pending_human_approval`
- Summary: The report does not demonstrate one independently mapped DSP MAC per PE; confirm with cycle-level PE activity before changing RTL.
- Evidence: `{"expected_concurrent_pe_count": 25, "observed_dsp48_count": 5.0, "artifact_path": "utilization.rpt"}`
- Required chain: `SPEC Requirement ID → 실패 증거 → 수정 내용 → 재검증 결과`

## PPA-WEIGHT-001

- Category: `hierarchical_lut_hotspot`
- Severity: `high`
- State: `detected_pending_human_approval`
- Summary: One hierarchy consumes more than the configured share of total LUT resources.
- Evidence: `{"instance": "weight_sram_instance", "instance_lut": 13930.0, "total_lut": 18059.0, "lut_ratio": 0.7714, "ramb18": 0.0, "artifact_path": "utilization_hierarchical.rpt"}`
- Required chain: `SPEC Requirement ID → 실패 증거 → 수정 내용 → 재검증 결과`

## PPA-TIMING-001

- Category: `setup_timing`
- Severity: `critical`
- State: `detected_pending_human_approval`
- Summary: Setup timing constraints are not met; implementation timing must be rechecked after an approved pipeline or memory-path change.
- Evidence: `{"wns_ns": -4.805, "tns_ns": -135.394, "setup_failing_endpoints": 41, "setup_total_endpoints": 3019, "wpws_ns": 4.5, "tpws_ns": 0.0, "pulse_failing_endpoints": 0, "artifact_path": "timing_summary.rpt"}`
- Required chain: `SPEC Requirement ID → 실패 증거 → 수정 내용 → 재검증 결과`

## PPA-POWER-001

- Category: `power_evidence_quality`
- Severity: `medium`
- State: `detected_pending_human_approval`
- Summary: Power confidence is low, so the value is directional and requires activity-based analysis before acceptance.
- Evidence: `{"total_on_chip_power_w": 0.268, "confidence": "Low", "dynamic_power_w": 0.161, "static_power_w": 0.107, "artifact_path": "power.rpt"}`
- Required chain: `SPEC Requirement ID → 실패 증거 → 수정 내용 → 재검증 결과`


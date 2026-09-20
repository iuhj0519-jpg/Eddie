# Approved additive SPEC spec_002

## REQ-LOOP-PPA-DSP-001
25 PE 각각 DSP48 MAC 1개. PE 계층별 매핑과 signed 26-bit 누산 결과 보존, 더미 DSP 금지.
Acceptance: [{"metric": "utilization.dsp", "op": "eq", "value": 25}, {"metric": "verification.peak_active_pe_count", "op": "eq", "value": 25}, {"metric": "review.REQ-LOOP-PPA-DSP-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-WEIGHT-001
Reduce Weight logic/selection overhead using banked storage; retain five-lane throughput and complete weight contents.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-WEIGHT-001", "op": "eq", "value": true}, {"metric": "utilization.lut", "op": "le", "value": 12642}, {"metric": "utilization.ff", "op": "le", "value": 2000}]

## REQ-LOOP-PPA-TIMING-001
Meet setup timing at the approved clock after routing; retain I/O and clock constraints.
Acceptance: [{"metric": "timing.wns_ns", "op": "ge", "value": 0}, {"metric": "timing.tns_ns", "op": "ge", "value": 0}, {"metric": "review.REQ-LOOP-PPA-TIMING-001", "op": "eq", "value": true}, {"metric": "timing.whs_ns", "op": "ge", "value": 0}, {"metric": "timing.wpws_ns", "op": "ge", "value": 0}]

## REQ-LOOP-PPA-POWER-001
Collect representative activity, mapping coverage and identical environment settings; report activity-based power with limitations.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-POWER-001", "op": "eq", "value": true}]

## REQ-LOOP-IMPL-DRC-001
Resolve or explicitly disposition IMPL-DRC-001 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-IMPL-DRC-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-MEMORY-MAPPING-001
Implement Weight storage in physical block memory with five-lane supply, correct initialization, capacity and synchronous read alignment.
Acceptance: [{"metric": "ram.weight_block_count", "op": "gt", "value": 0}, {"metric": "review.REQ-LOOP-PPA-MEMORY-MAPPING-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-ADDRESS-001
Restructure critical address arithmetic and bank decode with correct address/data/valid latency.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-ADDRESS-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-MUX-001
Reduce critical selection depth and check memory inference rather than hiding selection in equivalent logic.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-MUX-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-PIPELINE-001
Partition the critical combinational path and align scheduler, valid and memory latency.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-PIPELINE-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-ROUTE-DELAY-001
Reduce critical routing delay, checking placement and load distribution against the same constraints.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-ROUTE-DELAY-001", "op": "eq", "value": true}]

## REQ-LOOP-PPA-FANOUT-001
Reduce high-fanout timing impact by reviewing replicated/local control and address distribution.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-FANOUT-001", "op": "eq", "value": true}]

## REQ-LOOP-DRC-NSTD-1
Resolve or explicitly disposition DRC-NSTD-1 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-NSTD-1", "op": "eq", "value": true}]

## REQ-LOOP-DRC-UCIO-1
Resolve or explicitly disposition DRC-UCIO-1 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-UCIO-1", "op": "eq", "value": true}]

## REQ-LOOP-DRC-CHECK-3
Resolve or explicitly disposition DRC-CHECK-3 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-CHECK-3", "op": "eq", "value": true}]

## REQ-LOOP-DRC-DPIP-1
Resolve or explicitly disposition DRC-DPIP-1 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-DPIP-1", "op": "eq", "value": true}]

## REQ-LOOP-DRC-DPOP-1
Resolve or explicitly disposition DRC-DPOP-1 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-DPOP-1", "op": "eq", "value": true}]

## REQ-LOOP-DRC-DPOP-2
Resolve or explicitly disposition DRC-DPOP-2 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-DPOP-2", "op": "eq", "value": true}]

## REQ-LOOP-DRC-RBOR-1
Resolve or explicitly disposition DRC-RBOR-1 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-RBOR-1", "op": "eq", "value": true}]

## REQ-LOOP-DRC-REQP-1840
Resolve or explicitly disposition DRC-REQP-1840 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-REQP-1840", "op": "eq", "value": true}]

## REQ-LOOP-DRC-ZPS7-1
Resolve or explicitly disposition DRC-ZPS7-1 using the full DRC evidence and actual board/clock/reset contract.
Acceptance: [{"metric": "review.REQ-LOOP-DRC-ZPS7-1", "op": "eq", "value": true}]

## REQ-LOOP-PPA-CONSTRAINT-001
Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
Acceptance: [{"metric": "review.REQ-LOOP-PPA-CONSTRAINT-001", "op": "eq", "value": true}]

## REQ-LOOP-EVIDENCE-PROVENANCE-001
Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
Acceptance: [{"metric": "review.REQ-LOOP-EVIDENCE-PROVENANCE-001", "op": "eq", "value": true}]

## REQ-LOOP-EVIDENCE-COVERAGE-001
Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
Acceptance: [{"metric": "review.REQ-LOOP-EVIDENCE-COVERAGE-001", "op": "eq", "value": true}]

## REQ-LOOP-APPROVED-CYCLE-001
동일 100개 입력의 추론 Cycle 161735 이하, 그룹 797/43/33 및 기존 overlap 보존.
Acceptance: [{"metric": "verification.total_inference_cycles", "op": "le", "value": 161735}, {"metric": "review.REQ-LOOP-APPROVED-CYCLE-001", "op": "eq", "value": true}]

## REQ-LOOP-APPROVED-FUNCTION-001
100 sample 99 PASS/1 FAIL와 샘플별 Golden 보존. 계측 TB 복구 및 protocol/PE/interrupt 측정. 미계측은 UNKNOWN.
Acceptance: [{"metric": "verification.image_count", "op": "eq", "value": 100}, {"metric": "verification.failure_count", "op": "eq", "value": 1}, {"metric": "verification.protocol_errors", "op": "eq", "value": 0}, {"metric": "verification.interrupt_count_per_batch", "op": "eq", "value": 1}, {"metric": "review.REQ-LOOP-APPROVED-FUNCTION-001", "op": "eq", "value": true}]

## REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W
DSP 25-PE 최우선이며 균형형 PPA를 적용한다. 동일 SAIF 조건에서 평균 전력 0.544 W 이하 및 100 sample 에너지 900 uJ 이하. 추정치 한계 및 최종 사람 검토 유지.
Acceptance: [{"metric": "review.REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W", "op": "eq", "value": true}]

## REQ-LOOP-VERIFY-COMPILE-001
Investigate the cited evidence, preserve functional contracts, and resolve or document the finding.
Acceptance: [{"metric": "review.REQ-LOOP-VERIFY-COMPILE-001", "op": "eq", "value": true}]

## REQ-LOOP-EVIDENCE-MEMORY-MAPPING-001
Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
Acceptance: [{"metric": "review.REQ-LOOP-EVIDENCE-MEMORY-MAPPING-001", "op": "eq", "value": true}]

## REQ-LOOP-TOOL-WARNING-001
Investigate the cited evidence, preserve functional contracts, and resolve or document the finding.
Acceptance: [{"metric": "review.REQ-LOOP-TOOL-WARNING-001", "op": "eq", "value": true}]

## REQ-LOOP-VERIFY-EXECUTION-001
Investigate the cited evidence, preserve functional contracts, and resolve or document the finding.
Acceptance: [{"metric": "review.REQ-LOOP-VERIFY-EXECUTION-001", "op": "eq", "value": true}]
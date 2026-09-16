# SPEC change proposal — pending human approval

This is an additive overlay; baseline SPEC is not replaced or weakened.

Proposal digest: `3849cd8facb8c77b075bfb56b863061868e35f2b3dd1bac42b5c94d07d535180`

## REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W

- Type: optimization
- Findings: REGRESSION-TOTAL-ON-CHIP-POWER-W
- Before/evidence: {"evidence": "experiments/automation_loop/ppa_summary/SAIF_GATE_REVIEW.md", "systolic_power_w": 0.544, "optimized_power_w": 0.607, "systolic_duration_ns": 1837345, "optimized_duration_ns": 1617525, "comparison_status": "manual_report_comparison_pending_source_binding"}
- Required change: Developer must select average_power, energy_per_workload or balanced priority and approve explicit power and energy limits. Compare equivalent workloads and SAIF conditions. Review both limits before final acceptance; preserve functional and timing contracts.
- Acceptance: [{"metric": "review.REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W", "op": "eq", "value": true}]
- Verification: Review paired routed power reports, SAIF durations, activity coverage, source/workload hashes, P*t calculation and approved power_tradeoff limits. Rebind fresh evidence before any execution approval.
- Benefit: Prevent automatic acceptance of an average-power regression based on a small uncertain energy reduction.
- Risk: Medium confidence and low direct SAIF coverage; energy is estimated and target timing is not closed. PPA analysis closure is not design acceptance.

- Developer power/energy decision: {"priority": null, "max_average_power_w": null, "max_energy_per_workload_uj": null, "rationale": null}

## REQ-LOOP-PPA-DSP-001

- Type: compliance
- Findings: PPA-DSP-001
- Before/evidence: {"expected_concurrent_pe_count": 25, "observed_dsp48_count": 5.0, "artifact_path": "utilization_hierarchical.rpt"}
- Required change: Demonstrate the approved 25-PE independent MAC mapping and cycle-level concurrency; distinguish DSP allocation from PE activity.
- Acceptance: [{"metric": "utilization.dsp", "op": "ge", "value": 25}, {"metric": "verification.peak_active_pe_count", "op": "ge", "value": 25}, {"metric": "review.REQ-LOOP-PPA-DSP-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Count alone cannot prove PE mapping. Confirm DSP instance ownership and numeric equivalence.

## REQ-LOOP-PPA-WEIGHT-001

- Type: optimization
- Findings: PPA-WEIGHT-001
- Before/evidence: {"instance": "zyNet/weight_sram_instance", "instance_lut": 13955.0, "total_lut": 18060.0, "lut_ratio": 0.7727, "ramb18": 0.0, "artifact_path": "utilization_hierarchical.rpt"}
- Required change: Reduce Weight logic/selection overhead using banked storage; retain five-lane throughput and complete weight contents.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-WEIGHT-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-PPA-TIMING-001

- Type: compliance
- Findings: PPA-TIMING-001
- Before/evidence: {"wns_ns": -5.362, "tns_ns": -252.171, "setup_failing_endpoints": 104.0, "setup_total_endpoints": 3043.0, "whs_ns": 0.113, "ths_ns": 0.0, "hold_failing_endpoints": 0.0, "hold_total_endpoints": 3043.0, "wpws_ns": 4.5, "tpws_ns": 0.0, "pulse_failing_endpoints": 0.0, "pulse_total_endpoints": 1466.0, "artifact_path": "timing_summary.rpt"}
- Required change: Meet setup timing at the approved clock after routing; retain I/O and clock constraints.
- Acceptance: [{"metric": "timing.wns_ns", "op": "ge", "value": 0}, {"metric": "timing.tns_ns", "op": "ge", "value": 0}, {"metric": "review.REQ-LOOP-PPA-TIMING-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-PPA-POWER-001

- Type: compliance
- Findings: PPA-POWER-001
- Before/evidence: {"total_on_chip_power_w": 0.332, "confidence": "Low", "dynamic_power_w": 0.224, "static_power_w": 0.108, "artifact_path": "power.rpt"}
- Required change: Collect representative activity, mapping coverage and identical environment settings; report activity-based power with limitations.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-POWER-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: No arbitrary toggle-rate changes; power confidence is evidence quality, not a power budget.

## REQ-LOOP-IMPL-DRC-001

- Type: compliance
- Findings: IMPL-DRC-001
- Before/evidence: {"drc_violations": 0, "critical_warnings": 4, "unrouted_nets": 0, "routing_errors": 0, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition IMPL-DRC-001 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-IMPL-DRC-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-PPA-MEMORY-MAPPING-001

- Type: compliance
- Findings: PPA-MEMORY-MAPPING-001
- Before/evidence: {"module": "weight_sram", "storage": "block_ram", "requirement_id": "REQ-OPT-MEM-026", "requirement_state": "proposed_pending_final_approval", "instance": "zyNet/weight_sram_instance", "logic_lut": 13955.0, "lutram": 0.0, "ramb18": 0.0, "ramb36": 0.0, "artifact_path": "utilization_hierarchical.rpt"}
- Required change: Implement Weight storage in physical block memory with five-lane supply, correct initialization, capacity and synchronous read alignment.
- Acceptance: [{"metric": "ram.weight_block_count", "op": "gt", "value": 0}, {"metric": "review.REQ-LOOP-PPA-MEMORY-MAPPING-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: BRAM presence alone does not prove all weights are stored or five reads are supplied; verify bank coverage and data.

## REQ-LOOP-PPA-ADDRESS-001

- Type: optimization
- Findings: PPA-ADDRESS-001
- Before/evidence: {"paths": [{"slack_ns": -5.362, "artifact_path": "critical_paths.rpt", "line": 14, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[24]/D", "logic_levels": 17.0, "delay_ns": 15.216, "logic_ns": 5.506, "route_ns": 9.71, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.286, "artifact_path": "critical_paths.rpt", "line": 107, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[31]/D", "logic_levels": 15.0, "delay_ns": 15.143, "logic_ns": 5.249, "route_ns": 9.894, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.284, "artifact_path": "critical_paths.rpt", "line": 196, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[30]/D", "logic_levels": 15.0, "delay_ns": 15.142, "logic_ns": 5.249, "route_ns": 9.893, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.28, "artifact_path": "critical_paths.rpt", "line": 285, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[26]/D", "logic_levels": 17.0, "delay_ns": 15.142, "logic_ns": 5.472, "route_ns": 9.67, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.251, "artifact_path": "critical_paths.rpt", "line": 378, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[29]/D", "logic_levels": 17.0, "delay_ns": 15.202, "logic_ns": 5.496, "route_ns": 9.706, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.229, "artifact_path": "critical_paths.rpt", "line": 471, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[15]/D", "logic_levels": 18.0, "delay_ns": 15.187, "logic_ns": 5.671, "route_ns": 9.516, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.221, "artifact_path": "critical_paths.rpt", "line": 566, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[27]/D", "logic_levels": 16.0, "delay_ns": 15.141, "logic_ns": 5.066, "route_ns": 10.075, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.198, "artifact_path": "critical_paths.rpt", "line": 657, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[28]/D", "logic_levels": 15.0, "delay_ns": 15.068, "logic_ns": 5.285, "route_ns": 9.783, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.194, "artifact_path": "critical_paths.rpt", "line": 746, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[25]/D", "logic_levels": 16.0, "delay_ns": 15.059, "logic_ns": 5.352, "route_ns": 9.707, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.086, "artifact_path": "critical_paths.rpt", "line": 837, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[9]/D", "logic_levels": 17.0, "delay_ns": 15.027, "logic_ns": 5.532, "route_ns": 9.495, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.083, "artifact_path": "critical_paths.rpt", "line": 930, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[33]/D", "logic_levels": 16.0, "delay_ns": 15.034, "logic_ns": 5.181, "route_ns": 9.853, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.033, "artifact_path": "critical_paths.rpt", "line": 1021, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[10]/D", "logic_levels": 17.0, "delay_ns": 14.972, "logic_ns": 5.55, "route_ns": 9.422, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.011, "artifact_path": "critical_paths.rpt", "line": 1114, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[12]/D", "logic_levels": 18.0, "delay_ns": 14.957, "logic_ns": 5.632, "route_ns": 9.325, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.962, "artifact_path": "critical_paths.rpt", "line": 1209, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[13]/D", "logic_levels": 18.0, "delay_ns": 14.915, "logic_ns": 5.671, "route_ns": 9.244, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.953, "artifact_path": "critical_paths.rpt", "line": 1304, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[34]/D", "logic_levels": 16.0, "delay_ns": 14.949, "logic_ns": 5.43, "route_ns": 9.519, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.951, "artifact_path": "critical_paths.rpt", "line": 1395, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[11]/D", "logic_levels": 17.0, "delay_ns": 14.894, "logic_ns": 5.553, "route_ns": 9.341, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.94, "artifact_path": "critical_paths.rpt", "line": 1488, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[14]/D", "logic_levels": 18.0, "delay_ns": 14.889, "logic_ns": 5.671, "route_ns": 9.218, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.913, "artifact_path": "critical_paths.rpt", "line": 1583, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[18]/D", "logic_levels": 16.0, "delay_ns": 14.857, "logic_ns": 5.302, "route_ns": 9.555, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1674, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[37]/D", "logic_levels": 16.0, "delay_ns": 14.996, "logic_ns": 5.433, "route_ns": 9.563, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1765, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[36]/D", "logic_levels": 16.0, "delay_ns": 14.93, "logic_ns": 5.453, "route_ns": 9.477, "mux_present": true, "address_path": true, "dsp_present": true}]}
- Required change: Restructure critical address arithmetic and bank decode with correct address/data/valid latency.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-ADDRESS-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Extra registers, latency or area may be justified only by measured benefit under comparable workloads.

## REQ-LOOP-PPA-MUX-001

- Type: optimization
- Findings: PPA-MUX-001
- Before/evidence: {"paths": [{"slack_ns": -5.362, "artifact_path": "critical_paths.rpt", "line": 14, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[24]/D", "logic_levels": 17.0, "delay_ns": 15.216, "logic_ns": 5.506, "route_ns": 9.71, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.286, "artifact_path": "critical_paths.rpt", "line": 107, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[31]/D", "logic_levels": 15.0, "delay_ns": 15.143, "logic_ns": 5.249, "route_ns": 9.894, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.284, "artifact_path": "critical_paths.rpt", "line": 196, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[30]/D", "logic_levels": 15.0, "delay_ns": 15.142, "logic_ns": 5.249, "route_ns": 9.893, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.28, "artifact_path": "critical_paths.rpt", "line": 285, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[26]/D", "logic_levels": 17.0, "delay_ns": 15.142, "logic_ns": 5.472, "route_ns": 9.67, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.251, "artifact_path": "critical_paths.rpt", "line": 378, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[29]/D", "logic_levels": 17.0, "delay_ns": 15.202, "logic_ns": 5.496, "route_ns": 9.706, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.229, "artifact_path": "critical_paths.rpt", "line": 471, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[15]/D", "logic_levels": 18.0, "delay_ns": 15.187, "logic_ns": 5.671, "route_ns": 9.516, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.221, "artifact_path": "critical_paths.rpt", "line": 566, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[27]/D", "logic_levels": 16.0, "delay_ns": 15.141, "logic_ns": 5.066, "route_ns": 10.075, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.198, "artifact_path": "critical_paths.rpt", "line": 657, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[28]/D", "logic_levels": 15.0, "delay_ns": 15.068, "logic_ns": 5.285, "route_ns": 9.783, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.194, "artifact_path": "critical_paths.rpt", "line": 746, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[25]/D", "logic_levels": 16.0, "delay_ns": 15.059, "logic_ns": 5.352, "route_ns": 9.707, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.086, "artifact_path": "critical_paths.rpt", "line": 837, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[9]/D", "logic_levels": 17.0, "delay_ns": 15.027, "logic_ns": 5.532, "route_ns": 9.495, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.083, "artifact_path": "critical_paths.rpt", "line": 930, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[33]/D", "logic_levels": 16.0, "delay_ns": 15.034, "logic_ns": 5.181, "route_ns": 9.853, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.033, "artifact_path": "critical_paths.rpt", "line": 1021, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[10]/D", "logic_levels": 17.0, "delay_ns": 14.972, "logic_ns": 5.55, "route_ns": 9.422, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.011, "artifact_path": "critical_paths.rpt", "line": 1114, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[12]/D", "logic_levels": 18.0, "delay_ns": 14.957, "logic_ns": 5.632, "route_ns": 9.325, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.962, "artifact_path": "critical_paths.rpt", "line": 1209, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[13]/D", "logic_levels": 18.0, "delay_ns": 14.915, "logic_ns": 5.671, "route_ns": 9.244, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.953, "artifact_path": "critical_paths.rpt", "line": 1304, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[34]/D", "logic_levels": 16.0, "delay_ns": 14.949, "logic_ns": 5.43, "route_ns": 9.519, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.951, "artifact_path": "critical_paths.rpt", "line": 1395, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[11]/D", "logic_levels": 17.0, "delay_ns": 14.894, "logic_ns": 5.553, "route_ns": 9.341, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.94, "artifact_path": "critical_paths.rpt", "line": 1488, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[14]/D", "logic_levels": 18.0, "delay_ns": 14.889, "logic_ns": 5.671, "route_ns": 9.218, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.913, "artifact_path": "critical_paths.rpt", "line": 1583, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[18]/D", "logic_levels": 16.0, "delay_ns": 14.857, "logic_ns": 5.302, "route_ns": 9.555, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1674, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[37]/D", "logic_levels": 16.0, "delay_ns": 14.996, "logic_ns": 5.433, "route_ns": 9.563, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1765, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[36]/D", "logic_levels": 16.0, "delay_ns": 14.93, "logic_ns": 5.453, "route_ns": 9.477, "mux_present": true, "address_path": true, "dsp_present": true}]}
- Required change: Reduce critical selection depth and check memory inference rather than hiding selection in equivalent logic.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-MUX-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Extra registers, latency or area may be justified only by measured benefit under comparable workloads.

## REQ-LOOP-PPA-PIPELINE-001

- Type: optimization
- Findings: PPA-PIPELINE-001
- Before/evidence: {"paths": [{"slack_ns": -5.362, "artifact_path": "critical_paths.rpt", "line": 14, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[24]/D", "logic_levels": 17.0, "delay_ns": 15.216, "logic_ns": 5.506, "route_ns": 9.71, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.286, "artifact_path": "critical_paths.rpt", "line": 107, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[31]/D", "logic_levels": 15.0, "delay_ns": 15.143, "logic_ns": 5.249, "route_ns": 9.894, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.284, "artifact_path": "critical_paths.rpt", "line": 196, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[30]/D", "logic_levels": 15.0, "delay_ns": 15.142, "logic_ns": 5.249, "route_ns": 9.893, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.28, "artifact_path": "critical_paths.rpt", "line": 285, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[26]/D", "logic_levels": 17.0, "delay_ns": 15.142, "logic_ns": 5.472, "route_ns": 9.67, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.251, "artifact_path": "critical_paths.rpt", "line": 378, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[29]/D", "logic_levels": 17.0, "delay_ns": 15.202, "logic_ns": 5.496, "route_ns": 9.706, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.229, "artifact_path": "critical_paths.rpt", "line": 471, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[15]/D", "logic_levels": 18.0, "delay_ns": 15.187, "logic_ns": 5.671, "route_ns": 9.516, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.221, "artifact_path": "critical_paths.rpt", "line": 566, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[27]/D", "logic_levels": 16.0, "delay_ns": 15.141, "logic_ns": 5.066, "route_ns": 10.075, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.198, "artifact_path": "critical_paths.rpt", "line": 657, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[28]/D", "logic_levels": 15.0, "delay_ns": 15.068, "logic_ns": 5.285, "route_ns": 9.783, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.194, "artifact_path": "critical_paths.rpt", "line": 746, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[25]/D", "logic_levels": 16.0, "delay_ns": 15.059, "logic_ns": 5.352, "route_ns": 9.707, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.086, "artifact_path": "critical_paths.rpt", "line": 837, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[9]/D", "logic_levels": 17.0, "delay_ns": 15.027, "logic_ns": 5.532, "route_ns": 9.495, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.083, "artifact_path": "critical_paths.rpt", "line": 930, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[33]/D", "logic_levels": 16.0, "delay_ns": 15.034, "logic_ns": 5.181, "route_ns": 9.853, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.033, "artifact_path": "critical_paths.rpt", "line": 1021, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[10]/D", "logic_levels": 17.0, "delay_ns": 14.972, "logic_ns": 5.55, "route_ns": 9.422, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.011, "artifact_path": "critical_paths.rpt", "line": 1114, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[12]/D", "logic_levels": 18.0, "delay_ns": 14.957, "logic_ns": 5.632, "route_ns": 9.325, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.962, "artifact_path": "critical_paths.rpt", "line": 1209, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[13]/D", "logic_levels": 18.0, "delay_ns": 14.915, "logic_ns": 5.671, "route_ns": 9.244, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.953, "artifact_path": "critical_paths.rpt", "line": 1304, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[34]/D", "logic_levels": 16.0, "delay_ns": 14.949, "logic_ns": 5.43, "route_ns": 9.519, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.951, "artifact_path": "critical_paths.rpt", "line": 1395, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[11]/D", "logic_levels": 17.0, "delay_ns": 14.894, "logic_ns": 5.553, "route_ns": 9.341, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.94, "artifact_path": "critical_paths.rpt", "line": 1488, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[14]/D", "logic_levels": 18.0, "delay_ns": 14.889, "logic_ns": 5.671, "route_ns": 9.218, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.913, "artifact_path": "critical_paths.rpt", "line": 1583, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[18]/D", "logic_levels": 16.0, "delay_ns": 14.857, "logic_ns": 5.302, "route_ns": 9.555, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1674, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[37]/D", "logic_levels": 16.0, "delay_ns": 14.996, "logic_ns": 5.433, "route_ns": 9.563, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1765, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[36]/D", "logic_levels": 16.0, "delay_ns": 14.93, "logic_ns": 5.453, "route_ns": 9.477, "mux_present": true, "address_path": true, "dsp_present": true}]}
- Required change: Partition the critical combinational path and align scheduler, valid and memory latency.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-PIPELINE-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Extra registers, latency or area may be justified only by measured benefit under comparable workloads.

## REQ-LOOP-PPA-ROUTE-DELAY-001

- Type: optimization
- Findings: PPA-ROUTE-DELAY-001
- Before/evidence: {"paths": [{"slack_ns": -5.362, "artifact_path": "critical_paths.rpt", "line": 14, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[24]/D", "logic_levels": 17.0, "delay_ns": 15.216, "logic_ns": 5.506, "route_ns": 9.71, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.286, "artifact_path": "critical_paths.rpt", "line": 107, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[31]/D", "logic_levels": 15.0, "delay_ns": 15.143, "logic_ns": 5.249, "route_ns": 9.894, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.284, "artifact_path": "critical_paths.rpt", "line": 196, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[30]/D", "logic_levels": 15.0, "delay_ns": 15.142, "logic_ns": 5.249, "route_ns": 9.893, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.28, "artifact_path": "critical_paths.rpt", "line": 285, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[26]/D", "logic_levels": 17.0, "delay_ns": 15.142, "logic_ns": 5.472, "route_ns": 9.67, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.251, "artifact_path": "critical_paths.rpt", "line": 378, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[29]/D", "logic_levels": 17.0, "delay_ns": 15.202, "logic_ns": 5.496, "route_ns": 9.706, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.229, "artifact_path": "critical_paths.rpt", "line": 471, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[15]/D", "logic_levels": 18.0, "delay_ns": 15.187, "logic_ns": 5.671, "route_ns": 9.516, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.221, "artifact_path": "critical_paths.rpt", "line": 566, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[27]/D", "logic_levels": 16.0, "delay_ns": 15.141, "logic_ns": 5.066, "route_ns": 10.075, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.198, "artifact_path": "critical_paths.rpt", "line": 657, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[28]/D", "logic_levels": 15.0, "delay_ns": 15.068, "logic_ns": 5.285, "route_ns": 9.783, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.194, "artifact_path": "critical_paths.rpt", "line": 746, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[25]/D", "logic_levels": 16.0, "delay_ns": 15.059, "logic_ns": 5.352, "route_ns": 9.707, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.086, "artifact_path": "critical_paths.rpt", "line": 837, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[9]/D", "logic_levels": 17.0, "delay_ns": 15.027, "logic_ns": 5.532, "route_ns": 9.495, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.083, "artifact_path": "critical_paths.rpt", "line": 930, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[33]/D", "logic_levels": 16.0, "delay_ns": 15.034, "logic_ns": 5.181, "route_ns": 9.853, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.033, "artifact_path": "critical_paths.rpt", "line": 1021, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[10]/D", "logic_levels": 17.0, "delay_ns": 14.972, "logic_ns": 5.55, "route_ns": 9.422, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -5.011, "artifact_path": "critical_paths.rpt", "line": 1114, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[12]/D", "logic_levels": 18.0, "delay_ns": 14.957, "logic_ns": 5.632, "route_ns": 9.325, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.962, "artifact_path": "critical_paths.rpt", "line": 1209, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[13]/D", "logic_levels": 18.0, "delay_ns": 14.915, "logic_ns": 5.671, "route_ns": 9.244, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.953, "artifact_path": "critical_paths.rpt", "line": 1304, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[34]/D", "logic_levels": 16.0, "delay_ns": 14.949, "logic_ns": 5.43, "route_ns": 9.519, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.951, "artifact_path": "critical_paths.rpt", "line": 1395, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[11]/D", "logic_levels": 17.0, "delay_ns": 14.894, "logic_ns": 5.553, "route_ns": 9.341, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.94, "artifact_path": "critical_paths.rpt", "line": 1488, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[14]/D", "logic_levels": 18.0, "delay_ns": 14.889, "logic_ns": 5.671, "route_ns": 9.218, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.913, "artifact_path": "critical_paths.rpt", "line": 1583, "source": "systolic_controller_instance/cycle_count_reg[5]/C", "destination": "weight_sram_instance/read_data_reg[18]/D", "logic_levels": 16.0, "delay_ns": 14.857, "logic_ns": 5.302, "route_ns": 9.555, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1674, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[37]/D", "logic_levels": 16.0, "delay_ns": 14.996, "logic_ns": 5.433, "route_ns": 9.563, "mux_present": true, "address_path": true, "dsp_present": true}, {"slack_ns": -4.912, "artifact_path": "critical_paths.rpt", "line": 1765, "source": "systolic_controller_instance/cycle_count_reg[4]/C", "destination": "weight_sram_instance/read_data_reg[36]/D", "logic_levels": 16.0, "delay_ns": 14.93, "logic_ns": 5.453, "route_ns": 9.477, "mux_present": true, "address_path": true, "dsp_present": true}]}
- Required change: Reduce critical routing delay, checking placement and load distribution against the same constraints.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-ROUTE-DELAY-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Extra registers, latency or area may be justified only by measured benefit under comparable workloads.

## REQ-LOOP-PPA-FANOUT-001

- Type: optimization
- Findings: PPA-FANOUT-001
- Before/evidence: {"nets": [{"net": "weight_sram_instance/read_data1__0_n_100", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.908", "artifact_path": "high_fanout_nets.rpt", "line": 19}, {"net": "weight_sram_instance/read_data1__0_n_101", "fanout": 2415, "driver": "DSP48E1", "slack": "-5.033", "artifact_path": "high_fanout_nets.rpt", "line": 20}, {"net": "weight_sram_instance/read_data1__0_n_102", "fanout": 2415, "driver": "DSP48E1", "slack": "-5.099", "artifact_path": "high_fanout_nets.rpt", "line": 21}, {"net": "weight_sram_instance/read_data1__1_n_100", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.823", "artifact_path": "high_fanout_nets.rpt", "line": 22}, {"net": "weight_sram_instance/read_data1__1_n_101", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.702", "artifact_path": "high_fanout_nets.rpt", "line": 23}, {"net": "weight_sram_instance/read_data1__1_n_102", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.886", "artifact_path": "high_fanout_nets.rpt", "line": 24}, {"net": "weight_sram_instance/read_data1__2_n_100", "fanout": 2415, "driver": "DSP48E1", "slack": "-5.056", "artifact_path": "high_fanout_nets.rpt", "line": 25}, {"net": "weight_sram_instance/read_data1__2_n_101", "fanout": 2415, "driver": "DSP48E1", "slack": "-5.219", "artifact_path": "high_fanout_nets.rpt", "line": 26}, {"net": "weight_sram_instance/read_data1__2_n_102", "fanout": 2415, "driver": "DSP48E1", "slack": "-5.308", "artifact_path": "high_fanout_nets.rpt", "line": 27}, {"net": "weight_sram_instance/read_data1__3_n_100", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.688", "artifact_path": "high_fanout_nets.rpt", "line": 28}, {"net": "weight_sram_instance/read_data1__3_n_101", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.880", "artifact_path": "high_fanout_nets.rpt", "line": 29}, {"net": "weight_sram_instance/read_data1__3_n_102", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.872", "artifact_path": "high_fanout_nets.rpt", "line": 30}, {"net": "weight_sram_instance/read_data1_n_100", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.641", "artifact_path": "high_fanout_nets.rpt", "line": 31}, {"net": "weight_sram_instance/read_data1_n_101", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.758", "artifact_path": "high_fanout_nets.rpt", "line": 32}, {"net": "weight_sram_instance/read_data1_n_102", "fanout": 2415, "driver": "DSP48E1", "slack": "-4.774", "artifact_path": "high_fanout_nets.rpt", "line": 33}, {"net": "weight_sram_instance/read_data1__0_n_103", "fanout": 2410, "driver": "DSP48E1", "slack": "-5.018", "artifact_path": "high_fanout_nets.rpt", "line": 34}, {"net": "weight_sram_instance/read_data1__1_n_103", "fanout": 2410, "driver": "DSP48E1", "slack": "-4.828", "artifact_path": "high_fanout_nets.rpt", "line": 35}, {"net": "weight_sram_instance/read_data1__2_n_103", "fanout": 2410, "driver": "DSP48E1", "slack": "-5.291", "artifact_path": "high_fanout_nets.rpt", "line": 36}, {"net": "weight_sram_instance/read_data1__3_n_103", "fanout": 2410, "driver": "DSP48E1", "slack": "-4.931", "artifact_path": "high_fanout_nets.rpt", "line": 37}, {"net": "weight_sram_instance/read_data1_n_103", "fanout": 2410, "driver": "DSP48E1", "slack": "-4.797", "artifact_path": "high_fanout_nets.rpt", "line": 38}, {"net": "weight_sram_instance/read_data1__0_n_105", "fanout": 2401, "driver": "DSP48E1", "slack": "-5.154", "artifact_path": "high_fanout_nets.rpt", "line": 39}, {"net": "weight_sram_instance/read_data1__1_n_105", "fanout": 2401, "driver": "DSP48E1", "slack": "-4.913", "artifact_path": "high_fanout_nets.rpt", "line": 40}, {"net": "weight_sram_instance/read_data1__2_n_105", "fanout": 2401, "driver": "DSP48E1", "slack": "-5.362", "artifact_path": "high_fanout_nets.rpt", "line": 41}, {"net": "weight_sram_instance/read_data1__3_n_105", "fanout": 2401, "driver": "DSP48E1", "slack": "-5.083", "artifact_path": "high_fanout_nets.rpt", "line": 42}, {"net": "weight_sram_instance/read_data1_n_105", "fanout": 2401, "driver": "DSP48E1", "slack": "-4.604", "artifact_path": "high_fanout_nets.rpt", "line": 43}, {"net": "weight_sram_instance/read_data1__0_n_104", "fanout": 2400, "driver": "DSP48E1", "slack": "-5.229", "artifact_path": "high_fanout_nets.rpt", "line": 44}, {"net": "weight_sram_instance/read_data1__1_n_104", "fanout": 2400, "driver": "DSP48E1", "slack": "-4.907", "artifact_path": "high_fanout_nets.rpt", "line": 45}, {"net": "weight_sram_instance/read_data1__2_n_104", "fanout": 2400, "driver": "DSP48E1", "slack": "-5.259", "artifact_path": "high_fanout_nets.rpt", "line": 46}, {"net": "weight_sram_instance/read_data1__3_n_104", "fanout": 2400, "driver": "DSP48E1", "slack": "-5.061", "artifact_path": "high_fanout_nets.rpt", "line": 47}, {"net": "weight_sram_instance/read_data1_n_104", "fanout": 2400, "driver": "DSP48E1", "slack": "-4.826", "artifact_path": "high_fanout_nets.rpt", "line": 48}, {"net": "weight_sram_instance/read_data1__0_n_99", "fanout": 1269, "driver": "DSP48E1", "slack": "-4.669", "artifact_path": "high_fanout_nets.rpt", "line": 49}, {"net": "weight_sram_instance/read_data1__1_n_99", "fanout": 1269, "driver": "DSP48E1", "slack": "-4.450", "artifact_path": "high_fanout_nets.rpt", "line": 50}, {"net": "weight_sram_instance/read_data1__2_n_99", "fanout": 1269, "driver": "DSP48E1", "slack": "-4.921", "artifact_path": "high_fanout_nets.rpt", "line": 51}, {"net": "weight_sram_instance/read_data1__3_n_99", "fanout": 1269, "driver": "DSP48E1", "slack": "-4.476", "artifact_path": "high_fanout_nets.rpt", "line": 52}, {"net": "weight_sram_instance/read_data1_n_99", "fanout": 1269, "driver": "DSP48E1", "slack": "-4.330", "artifact_path": "high_fanout_nets.rpt", "line": 53}, {"net": "systolic_controller_instance/systolic_array_2d_instance/ARRAY_ROWS[4].ARRAY_COLUMNS[4].pe_systolic_cell_instance/mac_pe_instance/s_axi_aresetn", "fanout": 1262, "driver": "LUT1", "slack": "inf", "artifact_path": "high_fanout_nets.rpt", "line": 54}, {"net": "weight_sram_instance/read_data1__0_n_98", "fanout": 554, "driver": "DSP48E1", "slack": "-4.541", "artifact_path": "high_fanout_nets.rpt", "line": 55}, {"net": "weight_sram_instance/read_data1__1_n_98", "fanout": 554, "driver": "DSP48E1", "slack": "-4.427", "artifact_path": "high_fanout_nets.rpt", "line": 56}, {"net": "weight_sram_instance/read_data1__2_n_98", "fanout": 554, "driver": "DSP48E1", "slack": "-4.737", "artifact_path": "high_fanout_nets.rpt", "line": 57}, {"net": "weight_sram_instance/read_data1__3_n_98", "fanout": 554, "driver": "DSP48E1", "slack": "-4.272", "artifact_path": "high_fanout_nets.rpt", "line": 58}, {"net": "weight_sram_instance/read_data1_n_98", "fanout": 554, "driver": "DSP48E1", "slack": "-4.252", "artifact_path": "high_fanout_nets.rpt", "line": 59}]}
- Required change: Reduce high-fanout timing impact by reviewing replicated/local control and address distribution.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-FANOUT-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Extra registers, latency or area may be justified only by measured benefit under comparable workloads.

## REQ-LOOP-DRC-NSTD-1

- Type: compliance
- Findings: DRC-NSTD-1
- Before/evidence: {"rule": "NSTD-1", "severity": "Critical Warning", "count": 1, "line": 31, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-NSTD-1 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-NSTD-1", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-UCIO-1

- Type: compliance
- Findings: DRC-UCIO-1
- Before/evidence: {"rule": "UCIO-1", "severity": "Critical Warning", "count": 1, "line": 32, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-UCIO-1 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-UCIO-1", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-CHECK-3

- Type: compliance
- Findings: DRC-CHECK-3
- Before/evidence: {"rule": "CHECK-3", "severity": "Warning", "count": 1, "line": 33, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-CHECK-3 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-CHECK-3", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-DPIP-1

- Type: compliance
- Findings: DRC-DPIP-1
- Before/evidence: {"rule": "DPIP-1", "severity": "Warning", "count": 10, "line": 34, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-DPIP-1 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-DPIP-1", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-DPOP-1

- Type: compliance
- Findings: DRC-DPOP-1
- Before/evidence: {"rule": "DPOP-1", "severity": "Warning", "count": 5, "line": 35, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-DPOP-1 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-DPOP-1", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-DPOP-2

- Type: compliance
- Findings: DRC-DPOP-2
- Before/evidence: {"rule": "DPOP-2", "severity": "Warning", "count": 5, "line": 36, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-DPOP-2 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-DPOP-2", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-RBOR-1

- Type: compliance
- Findings: DRC-RBOR-1
- Before/evidence: {"rule": "RBOR-1", "severity": "Warning", "count": 5, "line": 37, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-RBOR-1 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-RBOR-1", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-REQP-1840

- Type: compliance
- Findings: DRC-REQP-1840
- Before/evidence: {"rule": "REQP-1840", "severity": "Warning", "count": 20, "line": 38, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-REQP-1840 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-REQP-1840", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-DRC-ZPS7-1

- Type: compliance
- Findings: DRC-ZPS7-1
- Before/evidence: {"rule": "ZPS7-1", "severity": "Warning", "count": 1, "line": 39, "artifact_path": "drc.rpt"}
- Required change: Resolve or explicitly disposition DRC-ZPS7-1 using the full DRC evidence and actual board/clock/reset contract.
- Acceptance: [{"metric": "review.REQ-LOOP-DRC-ZPS7-1", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-PPA-CONSTRAINT-001

- Type: evidence
- Findings: PPA-CONSTRAINT-001
- Before/evidence: {"no_input_delay": 20, "no_output_delay": 11}
- Required change: Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
- Acceptance: [{"metric": "review.REQ-LOOP-PPA-CONSTRAINT-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-EVIDENCE-PROVENANCE-001

- Type: evidence
- Findings: EVIDENCE-PROVENANCE-001
- Before/evidence: {"artifact_path": "run_manifest.yaml"}
- Required change: Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
- Acceptance: [{"metric": "review.REQ-LOOP-EVIDENCE-PROVENANCE-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-EVIDENCE-COVERAGE-001

- Type: evidence
- Findings: EVIDENCE-COVERAGE-001
- Before/evidence: {"unknown": ["interrupt_count_per_batch", "peak_active_pe_count", "protocol_errors", "ram", "utilization", "verification"]}
- Required change: Collect missing evidence/constraints and bind it to the exact source and run; UNKNOWN must not be treated as PASS.
- Acceptance: [{"metric": "review.REQ-LOOP-EVIDENCE-COVERAGE-001", "op": "eq", "value": true}]
- Verification: Compile/simulation Golden regression plus relevant same-source post-route report; attach reviewed evidence for this requirement.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

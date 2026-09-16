# SAIF PPA closure and pending developer Gate

Status: PPA analysis documented; **Run is not approved for patch generation.**
This comparison is a manual evidence supplement, not a new debugging Run and not a claim that the old analysis binding is fresh.

## Units and calculation

The SAIF headers specify TIMESCALE = 1 ps. Durations are 1,837,345,000 ps and 1,617,525,000 ps.
Thus the collection windows are **1,837,345 ns** and **1,617,525 ns**.
1,000,000 ns = 1 ms; the previous 1.837345 ms and 1.617525 ms values were equivalent, not unit errors.
Commas in the ns values are thousands separators; decimal points in W, seconds and milliseconds remain decimal points.

E[J] = P[W] * duration[ns] * 10^-9.
E[microjoule] = P[W] * duration[ns] * 10^-3.

| Metric | Systolic | Optimized |
|---|---:|---:|
| Average on-chip power estimate | 0.544 W | 0.607 W |
| Collection window (100 samples, includes TB overhead/reset) | 1,837,345 ns | 1,617,525 ns |
| Energy estimate | 999.515680 microjoule | 981.837675 microjoule |
| Direct SAIF mapping | 475/31,953 | 401/32,073 |
| Confidence | Medium | Medium |

Systolic: 0.544 * 1,837,345 * 10^-9 = 0.000999515680 J.
Optimized: 0.607 * 1,617,525 * 10^-9 = 0.000981837675 J.
Average power increased by 11.5809%; collection time decreased by 11.9640%; estimated energy decreased by 1.7687%.
Rounded reported power and low direct annotation do not establish a significant energy-efficiency improvement.
Both designs still fail setup timing at the intended clock. These are simulation/model estimates, not board measurements.

## Regression and pending choice

Finding: REGRESSION-TOTAL-ON-CHIP-POWER-W.
Evidence: systolic_power_saif.rpt, optimized_power_saif.rpt, saif_evidence.json in this directory.
Do not compare SAIF results with old vectorless numbers or silently replace historical reports.

The developer, not the agent, selects one priority:
- average_power: prioritize reducing average power, while specifying an acceptable energy limit.
- energy_per_workload: prioritize energy for the same workload, while specifying an acceptable average-power limit.
- balanced: explicitly specify both limits and the tradeoff rationale.

The pending draft is ../optimized_accelerator/analysis_003/requirements.yaml:
REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W.power_tradeoff.
priority, max_average_power_w, max_energy_per_workload_uj and rationale are intentionally unset.
approve-spec rejects missing choices/limits. A human evidence review remains mandatory for final acceptance.
Limits are reviewed against paired evidence; energy is not currently an automatically parsed/enforced metric.

## Gate monitoring checklist

| Check | Git record | Current boundary |
|---|---|---|
| All diagnosed issues | ../optimized_accelerator/analysis_003/findings.yaml and diagnosis.md | Historical generated diagnosis; SAIF regression supplemented here and in requirements.yaml |
| Proposed requirements and developer power choice | ../optimized_accelerator/analysis_003/requirements.yaml and spec_change_proposal.md | Draft; choice pending |
| Execution approval | ../optimized_accelerator/analysis_003/approval.yaml and gate_status.json | Not approved; old binding must be refreshed |
| Source, artifacts, tools and SPEC provenance | ../optimized_accelerator/analysis_003/run_manifest.yaml | Require source/workload/artifact hashes and fresh re-analysis before approval |
| Functional validation | Compile/simulation logs, sample results, protocol assertions in bound artifacts | Correct files, no X/missing data, expected results; preserve existing contracts |
| Timing and implementation | timing_summary.rpt, critical_paths.rpt, route_status.rpt, drc.rpt | Setup/hold/pulse, routing, constraints and critical DRC must satisfy acceptance |
| Area and architecture | utilization_hierarchical.rpt, ram_utilization.rpt, PE activity | Weight mapping, buffer resources, mux/address/fanout; DSP count alone does not prove concurrency |
| Power | Paired SAIF reports and metadata here, then copied/bound to new analysis artifacts | Match device, clock, workload, activity, environment; review low annotation limitation |
| Regression comparison | optimization_assessment.json | Refresh with SAIF context; old assessment is not this new comparison |
| Final implementation acceptance | requirement_reviews.yaml then final_acceptance.yaml | Created only after explicit review/acceptance; absent is not PASS |

PPA analysis completion does not authorize RTL modification or waive failing timing/DRC.
Carry this pending regression requirement into fresh analysis before approving SPEC or debugging.
Do not edit the generated finding history to pretend a full analysis has already been rerun.

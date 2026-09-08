# Pending review — not an approved SPEC

- PPA-DSP-001: The report does not demonstrate one independently mapped DSP MAC per PE; confirm with cycle-level PE activity before changing RTL.
- PPA-WEIGHT-001: One hierarchy consumes more than the configured share of total LUT resources.
- PPA-TIMING-001: Setup timing constraints are not met; implementation timing must be rechecked after an approved pipeline or memory-path change.
- PPA-POWER-001: Power confidence is low, so the value is directional and requires activity-based analysis before acceptance.
- IMPL-DRC-001: Post-Route DRC contains violations or critical warnings.
- PPA-ADDRESS-001: Failing path includes address/control generation. Review widths, arithmetic and memory access latency; cause remains a hypothesis until RTL/netlist review.
- PPA-MUX-001: Failing path traverses dedicated MUX resources. Review selection depth and BRAM inference without assuming a specific fix.
- PPA-PIPELINE-001: Deep failing combinational paths require pipeline review including valid, address and scheduler alignment.
- PPA-ROUTE-DELAY-001: Routing dominates a failing path. Review fanout and placement with logic changes; this is not proof of congestion.
- PPA-FANOUT-001: High-fanout drivers require load distribution and timing review.
- DRC-NSTD-1: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-UCIO-1: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-CHECK-3: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-DPIP-1: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-DPOP-1: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-DPOP-2: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-RBOR-1: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-REQP-1840: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- DRC-ZPS7-1: Review reported DRC rule before approval; pipeline/reset/I/O recommendations must not be applied blindly.
- PPA-CONSTRAINT-001: External I/O delays are missing; timing coverage is incomplete.
- EVIDENCE-PROVENANCE-001: Checkpoint identity is hashed, but its original RTL source hash was not recorded. Do not infer source equivalence from the model name.
- EVIDENCE-COVERAGE-001: Missing/unparsed evidence is UNKNOWN, never a pass. Collect evidence or request a human decision.

Assign an approved SPEC Requirement ID to each authorized change. No approved SPEC was modified.

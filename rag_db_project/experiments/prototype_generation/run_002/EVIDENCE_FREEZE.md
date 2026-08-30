# Systolic Prototype Run 002 Evidence Freeze

## Frozen Boundary

- Generation ID: `systolic_prototype_run_002`
- Source Tag: `rag-input-baseline-v1.1`
- Source Commit: `0f014e8e641dc6621f5b04aeda74cc49544d3d6b`
- Source Inventory SHA-256: `65b147ff1c6a08ab61af34530ff147fb3154dcd17200cff8a9f3c80b7100d0bf`
- Index ID: `prototype_generation_v2`
- Retrieval Sources/Chunks: 23/164
- Historical Baseline Index Chunks: 0
- Historical Baseline Visibility In Generation Worktree: false
- External Web/LLM/API: disabled

이 Run은 승인된 Reference Model, 변경되지 않은 Systolic Controller Reference RTL 4개, 승인 SPEC과 Direct Source Memory/Test Vector만 설계 근거로 사용했다. 승인 DB에 없는 설계 내용을 외부 지식으로 보완하지 않았다.

## Generation Query Set

| Query | Topic | Main Requirements |
|---|---|---|
| GEN-QRY-001 | AXI, Image-Major Batch, `0x08`, `intr` | REQ-REF-001, 008, 009; REQ-SYS-004, 020~024 |
| GEN-QRY-002 | 5×5 Output-Stationary Architecture | REQ-SYS-001, 002, 012, 013, 027 |
| GEN-QRY-003 | Input/Global Buffer Ping-Pong | REQ-SYS-003, 005~007 |
| GEN-QRY-004 | Controller FSM And Handshake | REQ-SYS-008, 011 |
| GEN-QRY-005 | Fixed-Point, SRAM, LUT, Saturation | REQ-REF-003, 010~013; REQ-SYS-009, 010, 014, 015, 019, 026 |
| GEN-QRY-006 | 797/43/33 Cycle Contract | REQ-SYS-016, 017 |
| GEN-QRY-007 | MaxFinder And Golden Baseline | REQ-REF-002, 004~007 |
| GEN-QRY-008 | RAG-Only And Naming Rules | REQ-SYS-018, 025, 029 |
| GEN-QRY-009 | Reference Controller Core Hierarchy | REQ-SYS-027 |
| GEN-QRY-010 | SRAM Streaming Without Matrix Latch | REQ-SYS-028 |

`retrieval_evidence.jsonl`은 각 Query의 Top Retrieval Chunk, Source Path와 Source Hash를 기계 판독 가능한 형식으로 보존한다.

## Implementation Decision

- Controller 내부에 `latched_mat_a`, `latched_mat_b` 또는 동등한 전체 Matrix Register를 만들지 않았다.
- `systolic_controller`의 RUN Counter와 Row/Column Skew가 SRAM 주소를 생성한다.
- Input/Global Buffer와 Weight SRAM의 1-Cycle Read 결과 중 5개 Input Lane과 5개 Weight Lane만 Array에 Streaming한다.
- Core 계층은 `systolic_controller → systolic_array_2d → pe_systolic_cell → mac_pe`로 구성했다.
- Reference Model에서 계승한 `zyNet`, `axi_lite_wrapper`, `maxFinder` Module 이름을 유지했다.
- Layer 3 Activation은 전체 Score Matrix Register 없이 `maxFinder`에 Column 단위로 직접 전달한다.

## Verification Outcome

- ModelSim Intel FPGA Edition 10.5b
- Compile: 0 Errors, 0 Warnings
- Simulation: 100 Samples, 20 Batches
- Result: 99 PASS, 1 FAIL, Accuracy 99.000000%
- Known Failure: Sample 18, Detected 8, Expected 3
- Controller Cycle Assertions: 797/43/33 PASS
- Interrupt Assertions: Batch당 1-Cycle, 총 20회 PASS
- Retrieval Smoke Test: 7/7 PASS
- Manifest Validation: 42/42 PASS

## Files

| File | Role |
|---|---|
| `generation_manifest.yaml` | Source/Index/Policy/Verification Gate를 기계 판독 가능하게 기록 |
| `retrieval_evidence.jsonl` | Query별 실제 검색 근거와 Source Hash 기록 |
| `EVIDENCE_FREEZE.md` | 설계 경계, 핵심 결정과 검증 결과를 사람이 검토하는 문서 |

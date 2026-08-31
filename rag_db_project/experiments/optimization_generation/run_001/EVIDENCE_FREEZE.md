# Optimized Accelerator Run 001 Evidence Freeze

## Frozen Boundary

- Generation ID: `optimized_accelerator_run_001`
- Source Tag: `rag-optimization-input-v1.0`
- Source Commit: `d12125885097914a8ed0be77c7fdfdf206ade78a`
- Approved Sources: 265
- Index ID: `optimization_generation_v1`
- Retrieval Sources/Chunks: 39/269
- Denied Chunks: 0
- External Web/LLM/API: disabled
- Historical Baseline: denied

본 Run은 승인된 세 SPEC, Reference RTL과 `run_002`에서 검증된 Systolic Prototype만 설계 근거로 사용했다. 근거가 없는 결정은 `unknown`으로 중단하는 정책을 적용했다.

## Generation Query Set

| Query | Topic | Covered Requirements |
|---|---|---|
| OPT-QRY-001 | Unified Buffer Capacity And Ownership | REQ-OPT-001~006 |
| OPT-QRY-002 | AXI Prefetch And Latency Hiding | REQ-OPT-007~012, 024 |
| OPT-QRY-003 | Preserved Functional Protocol | REQ-OPT-017~020 |
| OPT-QRY-004 | BRAM-Friendly Memory | REQ-OPT-014, 015, 021 |
| OPT-QRY-005 | Port Collision And Arbitration | REQ-OPT-016 |
| OPT-QRY-006 | Storage Reuse And Streaming | REQ-OPT-004, 005, 013 |
| OPT-QRY-007 | PPA Disadvantage Minimization | REQ-OPT-022, 023, 025 |
| OPT-QRY-008 | Verified Prototype Interfaces | REQ-OPT-001, 003, 012, 019 |

`retrieval_evidence.jsonl`은 각 Query의 실제 Top Chunk, Source Path, Source Hash와 Line을 보존한다. 25개 Requirement 전체가 한 개 이상의 Query에 연결되어 있다.

## Capacity Decision

두 후보를 구현 전에 비교했다.

1. Double-Batch Storage: Bank당 1,598 byte, 전체 7,990 byte
2. Lifetime-Reuse Storage: Bank당 834 byte, 전체 4,170 byte

두 번째 후보를 선택했다. Layer 1이 입력을 여섯 output group에서 반복 사용하므로 마지막 group에서 읽은 주소만 다음 Batch에 반환한다. Layer 1 결과 30개와 Layer 2 결과 20개는 서로 다른 중간영역에 두어 ping-pong dataflow를 보존한다. Activation write 우선순위와 ready backpressure로 Bank당 최대 1-read/1-write를 유지한다.

## Completed Output

- Output: `workspace/optimized_accelerator`
- RTL: 13 files, 분리형 Buffer 대신 `unified_buffer.sv`
- Testbench: 100개 MNIST 연속 Streaming과 AXI-Lite result read
- ModelSim: 0 errors, 0 warnings
- Functional result: PASS 99, FAIL 1, Accuracy 99.0%
- Controller cycle: 797/43/33 PASS
- Interrupt: 20회 PASS
- End-to-end inference: 161,735 cycle

생성과 검증이 끝난 뒤 격리 Worktree의 sparse-checkout을 해제했으며, 비교 분석용 디렉터리가 다시 물리적으로 보이는 상태임을 확인했다. 이 복원은 생성 근거에는 영향을 주지 않는다.

## Files

| File | Role |
|---|---|
| `generation_manifest.yaml` | Source, Index, Policy, Coverage, Generation과 Verification Gate |
| `retrieval_evidence.jsonl` | Query별 실제 Retrieval Chunk와 Source Hash |
| `EVIDENCE_FREEZE.md` | 사람이 검토하는 동결 경계, Query, 구현 결정과 완료 결과 |

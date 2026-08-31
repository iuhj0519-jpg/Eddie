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

본 Run은 승인된 세 SPEC, Reference RTL과 `run_002`에서 검증된 Systolic Prototype만 설계 근거로 사용한다. 근거가 없는 결정은 `unknown`으로 중단한다.

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

## Capacity Decision Gate

코드 생성 전에 최소 두 후보를 비교한다.

1. 보수적 Double-Batch Storage: Current Input과 Next Input을 독립 보존하고 Intermediate Storage를 별도 역할로 재사용
2. Lifetime-Reuse Storage: 이미 소비된 Current Input Address를 Next Batch Prefetch에 순차 반환하고 Layer Intermediate에 필요한 Bank-Local Storage만 유지

기능 안정성, Port 수와 Ready Critical Path를 고려해 선택하며 결정과 계산을 구현 보고서에 남긴다.

## Files

| File | Role |
|---|---|
| `generation_manifest.yaml` | Source, Index, Policy, Coverage와 Generation Gate |
| `retrieval_evidence.jsonl` | Query별 실제 Retrieval Chunk와 Source Hash |
| `EVIDENCE_FREEZE.md` | 사람이 검토하는 경계, Query와 구현 전 Decision Gate |

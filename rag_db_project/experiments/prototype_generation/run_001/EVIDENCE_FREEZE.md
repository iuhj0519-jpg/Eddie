# Systolic Prototype Evidence Freeze

> `run_001`은 `rag-input-baseline-v1.0`의 재현 가능한 기록으로 유지한다. 이후 Systolic Controller Reference RTL이 승인 입력에 추가되었으므로, 이 Freeze는 새로운 Controller 이식 코드의 근거로 재사용하지 않는다.

## External Knowledge Rule For This Run

Repository 운영 정책은 RAG 근거가 끝내 부족할 때 `unknown → 사용자 승인 → 외부 조사 → SPEC 반영 → 재인덱싱`을 허용한다. 그러나 `systolic_prototype_run_001`은 RAG-only 비교 실험이므로 외부 Web과 외부 LLM/API 최후 수단도 비활성화했다. 이 Run의 구현 결정은 고정된 T0/T1/Direct Source 근거만 사용했다.

## Implementation Outcome

- Output: `workspace/systolic_prototype/`
- ModelSim Compile: 0 Errors, 0 Warnings
- Functional Regression: 99 PASS / 1 FAIL / 99.000000%
- Known Failure: Sample 18, Detected 8, Expected 3
- Controller Cycle Assertions: Layer 1/2/3 = 797/43/33 PASS
- Interrupt Assertions: 1-Cycle Pulse, 20 Batches PASS

- Generation ID: `systolic_prototype_run_001`
- 상태: Ready For Code Generation
- Source Tag: `rag-input-baseline-v1.0`
- Index ID: `prototype_generation_v1`
- Requirement Coverage: 39/39 PASS
- Historical Baseline Index Chunk: 0
- Isolated Worktree: PASS
- Generation Branch: `rag/generate-systolic-prototype-v1`
- Generation Root: `C:/Users/iuhj0/Eddie_rag_generation`

## Query의 의미

Generation Query는 사용자가 다시 답해야 하는 설계 질문이 아니다. 승인 SPEC과 Reference RTL에서 코드 생성에 필요한 근거를 검색하고, Agent가 사용한 Chunk ID·Source Hash·Line을 재현 가능하게 고정하는 검색 계약이다. 모든 설계 내용은 이미 승인 원천에서 결정됐으며 미결정 질문은 없다.

## Minimal Package

| 파일 | 역할 |
|---|---|
| `generation_manifest.yaml` | Source/Index ID, 접근 금지, 프로토콜 보존, Query Set, Coverage와 생성 Gate를 기계 판독 가능하게 통합 |
| `retrieval_evidence.jsonl` | Query별 Top Retrieval과 39개 Requirement의 정확한 Chunk 근거를 한 줄씩 보존 |
| `EVIDENCE_FREEZE.md` | 사람이 검토할 Query, Coverage, 프로토콜 보존 원칙, Leakage Gate와 생성 계획을 통합 |

별도의 `retrieval_queries.yaml`, `requirement_coverage.md`, `conflict_report.md`, `leakage_audit.json`, `generation_plan.md`는 만들지 않았다. 이들의 내용은 위 세 파일에 중복 없이 통합했다.

## Generation Query Set

| Query | Topic | Covered Requirements |
|---|---|---|
| GEN-QRY-001 | External Interface And Batch Protocol | REQ-REF-001, REQ-REF-008, REQ-REF-009, REQ-SYS-004, REQ-SYS-020, REQ-SYS-021, REQ-SYS-022, REQ-SYS-023, REQ-SYS-024 |
| GEN-QRY-002 | Systolic Architecture And Parallelism | REQ-SYS-001, REQ-SYS-002, REQ-SYS-012, REQ-SYS-013 |
| GEN-QRY-003 | Input And Global Buffer Dataflow | REQ-SYS-003, REQ-SYS-005, REQ-SYS-006, REQ-SYS-007 |
| GEN-QRY-004 | Scheduler And Controller Handshake | REQ-SYS-008, REQ-SYS-011 |
| GEN-QRY-005 | Memory Fixed-Point And Saturation | REQ-REF-003, REQ-REF-010, REQ-REF-011, REQ-REF-012, REQ-REF-013, REQ-SYS-009, REQ-SYS-010, REQ-SYS-014, REQ-SYS-015, REQ-SYS-019, REQ-SYS-026 |
| GEN-QRY-006 | Target Cycle Contract | REQ-SYS-016, REQ-SYS-017 |
| GEN-QRY-007 | Classification And Functional Baseline | REQ-REF-002, REQ-REF-004, REQ-REF-005, REQ-REF-006, REQ-REF-007 |
| GEN-QRY-008 | Evidence Boundary And Naming | REQ-SYS-018, REQ-SYS-025 |

## Protocol Preservation Rule

Reference Model과 목표 SPEC의 성능 및 내부 아키텍처 차이는 예상된 개발 결과이며 mismatch가 아니다. 다음 항목이 승인 없이 바뀌는 경우만 Protocol Violation으로 처리한다.

- External AXI signal 이름, width와 valid/ready 의미
- Image-Major 입력 순서와 batch 경계
- AXI-Lite byte address `0x08`의 순차 결과 read
- batch당 1-cycle `intr` 의미
- Fixed-Point와 LUT data 계약
- Class 선택 및 tie rule

Neuron 연산부를 5×5 Output-Stationary Systolic Array로 교체하고 Input Buffer, Global Buffer, SRAM, SigROM, Activation Unit과 DNN Scheduler를 추가하는 것은 의도된 Target Architecture 변경이다. 보존 계약이나 목표 cycle을 지킬 수 없다고 판단되면 Agent는 코드를 먼저 작성하지 않고 관련 Requirement, 이유와 수정 계산식을 보고해야 한다.

## Requirement Coverage

| Requirement | Query | Evidence Chunk | Source |
|---|---|---|---|
| REQ-REF-001 | GEN-QRY-001 | `chunk-cdfb16e62103a58c3f1ce32a` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:102` |
| REQ-REF-002 | GEN-QRY-007 | `chunk-a7a1e6ccbc849b556ff16fa4` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:103` |
| REQ-REF-003 | GEN-QRY-005 | `chunk-52cc2b6f95684beae16f180e` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:104` |
| REQ-REF-004 | GEN-QRY-007 | `chunk-5a62bcf1682f02d044401f03` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:105` |
| REQ-REF-005 | GEN-QRY-007 | `chunk-f43ae2ce55b4611acb5e28bc` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:106` |
| REQ-REF-006 | GEN-QRY-007 | `chunk-21a50803705be4b402a96b56` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:107` |
| REQ-REF-007 | GEN-QRY-007 | `chunk-dc1b8cd0f5003ca1a76dc772` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:108` |
| REQ-REF-008 | GEN-QRY-001 | `chunk-6fdf315a27cd5c73bb76f777` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:109` |
| REQ-REF-009 | GEN-QRY-001 | `chunk-b62c735e142c0394448042bb` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:110` |
| REQ-REF-010 | GEN-QRY-005 | `chunk-5a980c5782490d34e8f1c89c` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:111` |
| REQ-REF-011 | GEN-QRY-005 | `chunk-cc2dfff6cda79732d4847fb9` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:112` |
| REQ-REF-012 | GEN-QRY-005 | `chunk-30bdeb16cab170ee7f76f86f` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:113` |
| REQ-REF-013 | GEN-QRY-005 | `chunk-3dd040b6f3026d152acbf8b6` | `inputs/specifications/01_reference_model/REFERENCE_MODEL_SPECIFICATION.md:114` |
| REQ-SYS-001 | GEN-QRY-002 | `chunk-a676586db863386a935f8ac5` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:284` |
| REQ-SYS-002 | GEN-QRY-002 | `chunk-c98a588372ee05b3f3a3e27c` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:285` |
| REQ-SYS-003 | GEN-QRY-003 | `chunk-7404c8fdfc5e6fc8231decee` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:286` |
| REQ-SYS-004 | GEN-QRY-001 | `chunk-4b8b55d739d5e32837eb48e2` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:287` |
| REQ-SYS-005 | GEN-QRY-003 | `chunk-c2f2fd9a8def3f514191e84c` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:288` |
| REQ-SYS-006 | GEN-QRY-003 | `chunk-8a2c19aadd0083369d3fea50` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:289` |
| REQ-SYS-007 | GEN-QRY-003 | `chunk-ead2c5775bd6ffae3a671463` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:290` |
| REQ-SYS-008 | GEN-QRY-004 | `chunk-ed8100c5086a50ce20944c6c` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:291` |
| REQ-SYS-009 | GEN-QRY-005 | `chunk-4259541d69e605e7accfcec5` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:292` |
| REQ-SYS-010 | GEN-QRY-005 | `chunk-1bc4c2226335ee9d463537e1` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:293` |
| REQ-SYS-011 | GEN-QRY-004 | `chunk-74524673da9a060247f34fe8` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:294` |
| REQ-SYS-012 | GEN-QRY-002 | `chunk-f4fc408b8190720dc7e9880b` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:295` |
| REQ-SYS-013 | GEN-QRY-002 | `chunk-91bedbc92638eb2c7624430b` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:296` |
| REQ-SYS-014 | GEN-QRY-005 | `chunk-f3cb51bab853aafdd32ccc8b` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:297` |
| REQ-SYS-015 | GEN-QRY-005 | `chunk-56aed183d84c8d9244f8f036` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:298` |
| REQ-SYS-016 | GEN-QRY-006 | `chunk-11902b6db93883d436229d4e` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:299` |
| REQ-SYS-017 | GEN-QRY-006 | `chunk-9a1629808a97f0e4b2cbb336` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:300` |
| REQ-SYS-018 | GEN-QRY-008 | `chunk-e99a76b5e0ce0c545d4ceda0` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:301` |
| REQ-SYS-019 | GEN-QRY-005 | `chunk-ac01011bdc7ea8cd2ce0efc1` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:302` |
| REQ-SYS-020 | GEN-QRY-001 | `chunk-e1a2b18069a27d9a91e926b8` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:303` |
| REQ-SYS-021 | GEN-QRY-001 | `chunk-ec8cc88eae6aedb13cd9a7f3` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:304` |
| REQ-SYS-022 | GEN-QRY-001 | `chunk-1c0477e9a67eb083ea1b1c50` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:305` |
| REQ-SYS-023 | GEN-QRY-001 | `chunk-46ed6fc7fc42070538fb1f50` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:306` |
| REQ-SYS-024 | GEN-QRY-001 | `chunk-302e60336fc2c076f0b42cfd` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:307` |
| REQ-SYS-025 | GEN-QRY-008 | `chunk-3a0d99c24101c979092488d4` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:308` |
| REQ-SYS-026 | GEN-QRY-005 | `chunk-845fd55e739eff7d8346612c` | `inputs/specifications/02_systolic_accelerator/SYSTOLIC_ACCELERATOR_SPECIFICATION.md:309` |

## Historical Baseline Leakage Gate

- `phase_access_policy.yaml`에서 `historical_baselines/**` 차단
- SQLite Index 내 금지 경로 Chunk: 0
- Evidence JSONL 내 금지 경로: 0
- 코드 생성 시 격리 Worktree에서 Historical Baseline을 물리적으로 숨김
- 외부 Web 검색 금지
- 근거가 없는 설계 결정은 `unknown`으로 보고
- 모든 설계 결정에 Chunk ID 또는 Direct Source Hash 인용

Primary Repository의 `historical_baselines/`는 삭제하거나 변경하지 않는다. 격리 Worktree만 실험 중 사용하고 코드 생성·검증 종료 후 격리 Worktree를 제거하면 Primary Repository에서 Historical Baseline이 그대로 보인다.

## Generation Plan

완료된 준비 작업:

1. 격리 Worktree 생성 및 Historical Baseline 비가시성 검사
2. 동일 Source와 Manifest로 RAG Index 재생성
3. 241개 Source checksum과 41개 Manifest 검사 통과
4. 143개 Dense/FTS row와 금지 경로 0개 Smoke Test 통과
5. `generation_manifest.yaml`의 Isolated Worktree Gate를 PASS로 변경

다음 코드 생성 명령에서 수행할 작업:

1. Query Evidence를 먼저 읽고 Requirement-to-Module 구현 계획 작성
2. `workspace/systolic_prototype/`에만 RTL, memory wiring, script와 보고서 생성
3. 모든 설계 결정에 Evidence Chunk 또는 Direct Source Hash 기록
4. 근거 부족 시 `unknown`, 보존 계약 변경 필요 시 구현 전 보고
5. Lint, Compile, Simulation 이후에만 Verified 상태 부여

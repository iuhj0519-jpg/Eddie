# RAG Chunking And Ingestion

이 디렉터리는 승인된 설계 근거를 Chunking하고 로컬 Hybrid Index에 Ingestion하는 재현 가능한 Pipeline이다. Prototype과 Optimization은 같은 코드·Schema·Manifest 계층을 재사용하고, Phase별 설정과 Access Policy만 구분한다.

## Evidence Sufficiency와 외부 지식 처리

검색 반복의 종료 조건은 임의의 신뢰도 점수가 아니다. 다음 조건을 모두 만족해야 한다.

- 대상 Requirement가 승인된 Chunk 또는 Direct Source Hash에 연결됨
- 서로 충돌하는 승인 문서가 없음
- 금지 경로의 검색 결과가 0개임
- 구현 결정이 인용된 근거의 범위를 벗어나지 않음

조건을 만족하지 못하면 검색어를 보완하고, 근거가 계속 없으면 `unknown`으로 중단한다. 일반 Run에서는 사용자 승인 후 외부 LLM/API를 최후의 수단으로 사용할 수 있지만 결과를 SPEC에 편입하고 재인덱싱하기 전까지 설계 근거가 아니다. 현재 Prototype과 Optimization Generation Run은 외부 접근을 비활성화했다.

## Runtime

- Ubuntu WSL과 Python 3
- Python 표준 라이브러리 `sqlite3`, `hashlib`, `json`
- PyYAML
- Sparse Retrieval: SQLite FTS5 BM25
- Dense Retrieval: 384차원 deterministic feature hashing

Dense Index는 외부 API key나 model download 없이 같은 입력에서 같은 vector를 재생성한다. Learned Embedding Model은 아니며 Git의 승인 SPEC과 Source Manifest가 정본이고 Index는 재생성 가능한 파생 데이터다.

## Files

| 경로 | 역할 |
|---|---|
| `config/prototype_index.yaml` | 1차 Systolic Prototype용 Phase와 검색 설정 |
| `config/optimization_index.yaml` | Optimized Accelerator용 Phase와 검색 설정 |
| `schemas/chunk.schema.json` | Chunk metadata 구조 |
| `rag_index.py` | Hash, tokenizer와 dense feature 공통 함수 |
| `ingest/build_index.py` | Manifest 검증, Chunking, checksum 검사와 SQLite Ingestion |
| `retrieve/search.py` | BM25+dense Hybrid Retrieval CLI |
| `tests/smoke_test.py` | 검색 품질과 금지 경로 누출 검사 |
| `data/<index_id>/` | 생성된 Chunk와 SQLite Index; Git 제외 |
| `runs/<index_id>/` | Smoke Test 결과; Git 제외 |

Manifest YAML을 새로 늘리지 않고 기존 `source_manifest.yaml`, `phase_access_policy.yaml`, `baseline_manifest.yaml`, `index_manifest.yaml`에 Phase별 Section을 통합했다. `optimization_index.yaml`은 Manifest가 아니라 동일 Pipeline이 Optimization Phase와 Index ID를 선택하기 위한 실행 설정이다.

## Chunking Policy

- Markdown: Heading 단위, `REQ-*`는 Requirement별 독립 Chunk
- Verilog/SystemVerilog: Module signature context와 Symbol/Procedural Block 단위
- MIF/Test Vector: 수치 전체를 embedding하지 않고 Source Catalog와 checksum만 등록
- Phase Access Policy에서 차단한 경로: Index에서 제외

각 Chunk는 Source Path/Hash, Document ID/Version/Status, Trust Tier, Module/Symbol, Line 범위, Requirement ID와 인접 Chunk ID를 가진다.

## Optimization Build And Smoke Test

```bash
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/iuhj0/Eddie_rag_generation && python3 rag_db_project/rag/ingest/build_index.py --config rag_db_project/rag/config/optimization_index.yaml"
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/iuhj0/Eddie_rag_generation && python3 rag_db_project/rag/tests/smoke_test.py --config rag_db_project/rag/config/optimization_index.yaml"
```

검색 결과의 `source_path`, `source_hash`, `doc_id`, `line_start`, `line_end`는 Agent의 Evidence 기록에 보존한다.

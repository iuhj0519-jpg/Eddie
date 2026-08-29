# RAG Chunking And Ingestion

이 디렉터리는 승인된 `prototype_generation` 입력을 chunking하고 로컬 Hybrid Index에 ingestion하는 재현 가능한 Python pipeline을 제공한다.

## Runtime

- Ubuntu WSL
- Python 3
- Python 표준 라이브러리: `sqlite3`, `hashlib`, `json`
- Ubuntu Python package: `PyYAML`
- Sparse retrieval: SQLite FTS5 BM25
- Dense retrieval: 384차원 deterministic feature hashing

Dense index는 외부 API key나 model download 없이 같은 입력에서 같은 vector를 재생성하기 위한 초기 구현이다. Learned embedding model은 아니므로 자연어 의미 유사성 평가가 필요해지는 단계에서 교체할 수 있다. Git의 승인 SPEC과 source manifest가 정본이며 index는 언제든 다시 만들 수 있는 파생 데이터다.

## Files

| 경로 | 역할 |
|---|---|
| `config/prototype_index.yaml` | chunk 크기, index 방식과 Hybrid Retrieval 가중치 |
| `schemas/chunk.schema.json` | chunk metadata 구조 |
| `rag_index.py` | hash, tokenizer와 dense feature 공통 함수 |
| `ingest/build_index.py` | manifest 검증, chunking, checksum 검사와 SQLite ingestion |
| `retrieve/search.py` | BM25+dense Hybrid Retrieval CLI |
| `tests/smoke_test.py` | retrieval 품질의 기본 조건과 금지 경로 누출 검사 |
| `data/prototype_generation_v1/` | 생성된 chunk와 SQLite index; Git에서 제외 |
| `runs/prototype_generation_v1/` | smoke test 결과; Git에서 제외 |

## What Is Indexed

`phase_access_policy.yaml`의 `prototype_generation.retrieval_allow`만 읽는다.

- Markdown: heading 단위, `REQ-*`는 requirement별 독립 chunk
- Verilog: module signature context를 포함한 procedural block 또는 최대 100-line segment
- MIF/test vector/TB/script: embedding하지 않고 승인 source catalog와 checksum으로만 등록
- Historical Baseline, workspace, verification, experiments, artifacts: 검색 index에서 제외

각 chunk는 source path/hash, document ID/version/status, trust tier, module/symbol, line 범위, requirement ID, parent와 adjacent chunk ID를 가진다.

## Build

Git Bash 또는 PowerShell에서 Repository root를 기준으로 실행한다.

```bash
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/iuhj0/Eddie && python3 rag_db_project/rag/ingest/build_index.py"
```

## Smoke Test

```bash
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/iuhj0/Eddie && python3 rag_db_project/rag/tests/smoke_test.py"
```

## Search Example

```bash
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/iuhj0/Eddie && python3 rag_db_project/rag/retrieve/search.py 'REQ-SYS-024 result storage clear' --top-k 5"
```

검색 결과의 `source_path`, `source_hash`, `doc_id`, `line_start`, `line_end`를 Agent의 근거 citation과 audit log에 보존해야 한다.

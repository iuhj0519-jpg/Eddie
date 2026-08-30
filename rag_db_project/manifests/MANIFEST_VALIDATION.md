# Manifest Validation Report

- 상태: PASS
- 검증 범위: 승인 입력, 접근 정책과 prototype-generation RAG index
- 검증 명령: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File rag_db_project/manifests/validate_manifests.ps1`

## Validation Result

총 42개 검증 항목이 모두 통과했다.

| 검증 대상 | 결과 |
|---|---|
| 필수 manifest와 checksum inventory 존재 | PASS |
| YAML tab 미사용, schema version 및 status 존재 | PASS |
| 승인 원천 파일 수 | 246개 |
| 승인 원천 파일 존재 및 SHA-256 일치 | PASS |
| 금지 경로의 checksum inventory 혼입 | 없음 |
| 폴더별 기대 파일 수 | 모두 일치 |
| Reference Model SPEC 상태 | `approved`, version `1.0` |
| Systolic Accelerator SPEC 상태 | `approved`, version `1.1` |
| Systolic Controller Reference | 변경되지 않은 SystemVerilog 4개 + README |
| 단계별 접근 정책 | default deny |
| Historical Baseline의 prototype 생성 단계 접근 | 차단 |
| Reference Model 기능 Baseline | 99 PASS / 1 FAIL / 99.0% |
| RAG index 상태 | `built` |
| Retrieval 원천 | 23개 |
| 생성·ingestion된 chunk | 164개 |
| Dense vector / FTS5 row | 164개 / 164개 |
| 금지 경로 chunk | 0개 |
| Retrieval smoke test | PASS |

## Approved Source Counts

| 원천 그룹 | 파일 수 |
|---|---:|
| RTL Verilog | 11 |
| Testbench | 1 |
| Weight MIF | 60 |
| Bias MIF | 60 |
| Activation LUT | 1 |
| Test vector | 100 |
| Baseline 재현 script | 1 |
| Systolic Controller Reference RTL/README | 5 |
| Reference Model SPEC 문서 | 2 |
| Systolic Accelerator SPEC 문서 | 2 |
| Input navigation 문서 | 3 |
| 합계 | 246 |

## Integrity Identifier

`checksums/source_files.sha256` 파일 자체의 SHA-256은 다음과 같다.

```text
65b147ff1c6a08ab61af34530ff147fb3154dcd17200cff8a9f3c80b7100d0bf
```

이 값은 승인된 246개 원천의 경로와 개별 Checksum 목록을 식별한다. 원천 파일이나 승인 SPEC이 바뀌면 Checksum Inventory와 이 보고서를 다시 생성하고 검증해야 한다.

## Gate Decision

입력 동결, Chunking, Ingestion과 Systolic Controller 검색을 포함한 Retrieval Smoke Test를 통과했다. 기존 `run_001` 결과는 v1.0 근거로 생성된 기능 Baseline으로 보존하며, Reference Controller 이식본은 v1.1 근거와 새로운 Evidence Freeze로 다시 생성해야 한다.

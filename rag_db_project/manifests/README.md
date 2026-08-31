# RAG Input Manifests

이 디렉터리는 RAG DB의 승인 원천, 단계별 접근 범위, 기능 Baseline과 생성된 index의 상태를 기계가 읽을 수 있는 YAML로 관리한다. Vector DB는 파생 데이터이므로 이 manifest와 Git tag가 정본이다.

## Shared Staged Manifest

Prototype과 Optimization에 별도 Manifest 파일을 만들지 않는다. 기존 네 YAML을 유지하면서 단계별 내용을 함께 관리한다.

- `source_manifest.yaml`: 모든 승인 Source Group을 한 번 정의
- `phase_access_policy.yaml`: Prototype과 Optimization Allowlist를 분리
- `baseline_manifest.yaml`: Reference Baseline과 검증된 Systolic Prototype을 함께 고정
- `index_manifest.yaml`: 두 Index의 Provenance를 구분해 기록

`rag/config/prototype_index.yaml`과 `rag/config/optimization_index.yaml`은 Manifest가 아니라 동일 Builder의 Phase와 출력 Index ID를 선택하는 실행 설정이다.

## YAML Documents

| 파일 | 의미 | 변경 시점 |
|---|---|---|
| `source_manifest.yaml` | 승인된 원천 파일 그룹, 기대 파일 수, checksum inventory와 제외 범위 | 입력 파일 또는 SPEC이 바뀔 때 |
| `phase_access_policy.yaml` | 각 Agent 단계에서 retrieval과 direct file access가 허용·차단되는 경로 | 단계별 정보 공개 범위가 바뀔 때 |
| `baseline_manifest.yaml` | Reference Model의 simulator, test 수, 99/1 결과와 승인 SPEC 버전 | 기능 Baseline 또는 도구 조건이 바뀔 때 |
| `index_manifest.yaml` | chunker, embedding, vector/sparse index와 source checksum 상태 | ingestion을 실행하거나 index를 재생성할 때 |
| `checksums/source_files.sha256` | 승인된 입력 파일 265개의 SHA-256과 상대 경로 | 승인 입력이 바뀔 때 |
| `validate_manifests.ps1` | 파일 존재, count, hash, 승인 상태와 금지 경로를 재검증하는 PowerShell script | manifest 또는 입력이 바뀔 때 |
| `MANIFEST_VALIDATION.md` | manifest, checksum, 접근 정책 검증 결과 | 입력 동결 검증을 다시 수행할 때 |

## Source Of Truth

1. 승인 SPEC, Reference Model과 Systolic Controller Reference 원본 파일
2. `source_manifest.yaml`과 checksum inventory
3. 단계별 Git tag: `rag-input-baseline-v1.1`, `rag-optimization-input-v1.0`
4. 위 원천으로 생성한 RAG index

Index에만 존재하고 원천 파일이나 manifest에서 확인할 수 없는 내용은 설계 근거로 사용할 수 없다.

## Retrieval And Direct Access

- Markdown과 Verilog는 retrieval 대상으로 chunking한다.
- MIF와 test vector의 전체 숫자 배열은 embedding하지 않는다.
- 정확한 weight, bias, LUT와 test value는 checksum으로 추적한 원본 파일을 direct access로 읽는다.
- ModelSim 실행 스크립트는 Baseline 재현 도구이며 설계 지식 chunk로 사용하지 않는다.

## Update Rule

승인 입력이 바뀌면 기존 index를 계속 사용하지 않는다. Source checksum을 다시 만들고 manifest 검증을 통과한 뒤 새 Git tag와 새 index를 생성한다.

## Validation Command

Repository root에서 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File rag_db_project/manifests/validate_manifests.ps1
```

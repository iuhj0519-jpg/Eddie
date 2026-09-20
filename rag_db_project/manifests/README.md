# Manifests And Git Policy

Manifest는 승인 Source, 단계별 접근 범위, 생성된 Index와 자동화 Loop의 변경 권한을 기계 판독 가능한 YAML로 고정한다. Index는 파생 데이터이고 Manifest와 Source Hash가 정본이다.

| 파일 | 역할 |
|---|---|
| `source_manifest.yaml` | 승인된 Reference Model, Systolic Controller, SPEC Source Group |
| `baseline_manifest.yaml` | 기능 Baseline과 승인 SPEC 버전 |
| `phase_access_policy.yaml` | 각 단계의 Allowlist/Denylist. 모든 생성·Debugging 단계에서 Historical Baseline과 외부 지식을 차단 |
| `index_manifest.yaml` | Prototype, Optimization, Automation Loop Index의 Provenance와 상태 |
| `automation_loop_manifest.yaml` | 검색 가능한 Workspace Run 이력과 원본 Artifact 범위 |
| `automation_loop_policy.yaml` | 분석→승인→격리 Patch→재검증 State Machine, 승인 Gate, Git 보호 규칙 |
| `checksums/source_files.sha256` | 설계 입력 Source 무결성 |
| `checksums/automation_loop_files.sha256` | Automation Loop 검색 Source 무결성 |
| `validate_manifests.ps1` | Source 파일 존재, Hash, 금지 경로를 검사하는 기존 Validator |

Automation Loop Manifest와 Policy를 분리한 이유는 전자가 “무엇을 검색하는가”, 후자가 “언제 무엇을 변경할 수 있는가”를 담당하기 때문이다. 기존 Prototype/Optimization Manifest 계층은 변경하지 않았다.

## Mandatory Debugging Chain

```text
SPEC Requirement ID → 실패 증거 → 승인된 수정 내용 → 재검증 결과
```

Finding이 있어도 승인 전에는 RTL, SPEC, Test 기대값을 수정하거나 Push하지 않는다. `main`과 `Project_Git`은 보호 Branch이며 자동화 대상이 아니다.

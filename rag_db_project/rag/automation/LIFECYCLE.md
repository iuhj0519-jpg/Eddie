# 요구사항/SPEC 진화형 승인 Loop (2026-09-13)

구현 권한과 실제 RTL 최적화 승인은 다르다. 이 작업에서는 실제 SPEC 개정 승인, Finding 승인,
RTL 패치, 최종 수락 또는 run_003 실행을 하지 않는다. 기존 승인 SPEC과 과거 Run은 보존한다.

## 상태와 파일

| 단계 | 명령/파일 | 목적 |
|---|---|---|
| 요구사항 접수 | intake; requests/request_NNN/request.md | 개발자 원문 보존 |
| 구조화·Chunking | requirements.yaml; 기존 build_index.py | 단락별 고유 ID, 이후 요구사항별 Chunk 생성; 자연어의 의미를 임의 확정하지 않음 |
| SPEC 제안 | 각 Run/spec_change_proposal.md | 모든 Finding의 변경 전·후, 수용 조건, 검증, 이득과 위험 |
| SPEC 승인 | approve-spec; spec_versions/spec_NNN/{spec.yaml,SPEC.md,approval.yaml} | 정확한 초안 digest를 사람이 승인, 기존 SPEC의 불변 추가 명세 생성 |
| 실행 연결 | bind-spec; run_manifest.yaml | 승인 SPEC 버전/해시를 아직 미승인인 Run에 한 번만 연결 |
| Finding 승인 | approve; approval.yaml | 실제 SPEC에 존재하며 해당 Finding과 연결된 ID만 허용 |
| 디버깅 | resume; patch_request.json, proposed_patch.diff, patch_trace.yaml | 현재 Agent가 승인된 코드만 생성하고 격리 적용 |
| 재검증 | Compile → Simulation → Synthesis | 실제 명령 실행, 실패/Timeout이면 후속 단계 중지 |
| 다음 반복 | child Run; requirements_result.json, optimization_assessment.json | 요구사항 PASS/FAIL/UNKNOWN, 지표 변화, 새 개선안과 재승인 대기 |
| 증거 검토 | review-requirement; requirement_reviews.yaml | 이름을 남긴 사용자가 해당 Run의 증거 파일을 검토; 해시가 달라지면 무효 |
| 최종 수락 | accept; final_acceptance.yaml | 동일 소스 전체 도구 실행+Post-Route+SPEC 조건 확인 후 사용자 수락. 자동 승격은 안 함 |

RAG는 이벤트마다 기존 로컬 인덱서로 갱신한다. 상태는 rag/runs/lifecycle_sync.yaml에 기록된다.
아직 승인/최종 수락이 없어 관련 파일이 없는 것은 정상이며, allowlist의 명시적 optional 패턴만 허용한다.
인덱서 오류 시 성공으로 숨기지 않고 중단한다. 파일은 보존되므로 원인 해결 후 sync로 재시도한다.

## 실제 사용 순서 (명령은 프로젝트 루트에서 실행)

```powershell
python rag/automation/run_loop.py intake --target optimized_accelerator --request-id request_001 --request-file <개발자-원문.md>
python rag/automation/run_loop.py analyze --target optimized_accelerator --artifact-root artifacts/implementation/optimized_accelerator/run_002 --run-id <새-review-ID>
```

intake의 자연어는 단락 단위로 보존/구조화한다. Agent가 acceptance를 구체화해야 하며 빈 조건으로는 승인할 수 없다.
설계 요구사항을 분석 초안에 합치려면 analyze에 `--request-id request_NNN`을 추가한다.
현재 request_001은 이번 자동화 구축/진단 요청 기록이며, 이를 설계 RTL의 합격 조건으로 임의 적용하지 않았다.
수용 조건은 `{metric: timing.wns_ns, op: ge, value: 0}` 같은 안전한 비교식이다.
임의 코드 실행/eval은 사용하지 않는다. `review.<Requirement-ID> == true`는 자동 측정치가 아니라 명시적인 사람의 증거 검토다.
모든 자동 Finding 제안에도 검토 조건이 포함되므로 원인 가설을 확정 진단으로 오인하지 않는다.

```powershell
# requirements.yaml을 검토/보완한 후 그 정확한 digest를 계산
python -c "from pathlib import Path; from rag.automation.lifecycle import read,digest; print(digest(read(Path('<초안폴더>/requirements.yaml'))))"
# 다음 명령은 실제 사용자가 해당 SPEC 변경안을 승인한 뒤에만 실행
python rag/automation/run_loop.py approve-spec --target optimized_accelerator --proposal <초안폴더> --reviewer <승인자> --expected-digest <digest>
python rag/automation/run_loop.py bind-spec --target optimized_accelerator --run-id <검토Run> --spec-revision spec_001
python rag/automation/run_loop.py approve --target optimized_accelerator --run-id <검토Run> --finding-id <Finding> --decision approved --requirement-id <승인SPEC의-ID>
python rag/automation/run_loop.py resume --target optimized_accelerator --run-id <검토Run>
```

모든 Finding마다 승인/거절 결정이 있어야 한다. 패치가 없으면 waiting_for_agent_patch에서 중지한다.
패치 작성 후 resume을 다시 실행하면 도구 실행과 다음 Run 생성으로 이어진다.
다음 Run은 부모 SPEC을 물려받으며 새 개선 요구를 추가한 다음 SPEC 초안을 자동 생성한다.
새 SPEC을 승인했거나 소스/도구/정책이 달라졌으면 새 analyze에 `--spec-revision spec_NNN`을 지정한다.
기존 binding/승인 이후의 SPEC 바꿔치기는 차단된다. 승인 SPEC 조건 삭제·완화는 추가 개정 기능에서 금지한다.

## SPEC이 SRAM만 있었던 이유 및 수정

기존 상세 보완안은 Weight의 기능적 SRAM 요구와 물리 BRAM 합격 조건의 차이만 수작업으로 작성했다.
나머지 Finding은 ID/요약 목록만 있었다. 이는 개선 대상에서 제외한 것이 아니라 제안 생성기의 부족이었다.
이제 모든 Finding에 구조화된 제안을 생성한다. 종류는 compliance/optimization/evidence로 구분한다.
임계값은 최적화의 정답이 아니며, 자원 증가가 처리량 개선에 필요한 경우 같은 조건의 측정값과
사용자의 tradeoff 수락 근거가 필요하다. 동작 정확도나 승인된 필수조건을 임의 완화하지 않는다.

## 최종 검증과 한계

현재 자동 도구 단계는 Compile/Simulation/Synthesis다. Post-Route 자동 실행까지 추가된 것은 아니다.
사용자가 생성한 Post-Route/SAIF 및 Simulation 로그를 같은 소스의 artifact 묶음으로 수집한 뒤 analyze한다.
수정 후보의 추가 보고서를 분석할 때는 `analyze --parent-run <부모Run> --artifact-root <새증거폴더> --run-id <새Run>`을 사용한다.
부모의 격리된 source workspace와 SPEC을 물려받으므로 기본 workspace RTL로 잘못 연결하지 않는다.
`comparison_context.json`에 stage, clock_period_ns, workload_sha256, activity_kind를 실제 실행 조건으로 기록한다.
전후 조건이 누락되거나 다르면 수치 차이는 보여주되 개선으로 확정하지 않는다.
최종 accept는 execution_result.json의 source_hashes와 compile/simulation/synthesis/implementation 성공 기록,
실제 route_status.rpt, 완전한 coverage, routing error 0, Setup/Hold/Pulse 통과, 정상 simulation 완료를 요구한다.
수집되지 않은 기록은 만들거나 PASS로 표시하지 않는다. 기존 ppa_final의 원본 소스 연결 누락도 그대로 남는다.

```powershell
python rag/automation/run_loop.py review-requirement --target optimized_accelerator --run-id <Run> --requirement-id <ID> --decision pass --reviewer <이름> --rationale <검토근거> --evidence <해당Run-artifact-파일>
python rag/automation/run_loop.py accept --target optimized_accelerator --run-id <Run> --reviewer <이름> --rationale <비교조건과-절충판단>
```

규칙 기반 검출/조건 평가를 구현했지만 모든 결함 발견이나 최적해를 보장하지 않는다.
초안의 의미 해석과 패치 작성은 현재 Agent, SPEC/Finding 승인과 최종 수락은 개발자가 담당한다.
신규 SPEC 버전은 `inputs/specifications`의 기존 문서를 지우는 대신 버전별 추가 명세로 합성한다.
Runtime은 baseline과 ancestor hash, Requirement ID, Finding 연결을 검증한다.
Git Commit/Push는 별도 사용자 요청 범위이며 자동 최적화 루프가 무단 Push하지 않는다.

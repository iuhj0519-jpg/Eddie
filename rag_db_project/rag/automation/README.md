# 승인 기반 RTL 자동화 Loop

## 개발자가 볼 두 문서

- [탐지 결과·PPA 최종 표](../../experiments/automation_loop/ppa_summary/diagnosis.md)
- [다음 Gate 최적화 범위·수치 제안](../../experiments/automation_loop/ppa_summary/spec_change_proposal.md)

실행별 보완안은 `experiments/automation_loop/<target>/analysis_NNN/spec_change_proposal.md` 또는 `run_NNN/spec_change_proposal.md`에 한국어 표로 자동 생성한다.
JSON/YAML은 기계 판정·출처·승인 digest용이므로 키와 도구 식별자는 영문을 유지한다.

## 동작 방식

SPEC md 접수 → 현재 Agent의 정책 허용 로컬 DB 검색 → 요구사항/근거 ID와 보완안 → 개발자 모니터링/Gate 승인 → 현재 Agent의 RTL 패치 → 격리 검증 → 회귀 탐지/보완안 → 재승인.

외부 LLM API 호출, 외부 웹 정보의 RTL 설계 근거 사용, historical_baselines의 디버깅 근거 사용은 금지한다.
현재 대화 Agent가 문서 해석·설계·패치 작성을 담당한다. Python은 LLM이 아니며 코드만 실행해서 새로운 Agent 세션을 스스로 시작하지 않는다.
Agent가 활성화된 승인 작업 중에는 waiting_for_agent_patch를 확인하고 승인된 범위의 패치와 trace를 작성한 뒤 resume을 이어간다. 개발자가 패치를 수동 작성할 필요는 없다.
현재 세션이 종료되면 자동 백그라운드 설계가 계속된다고 주장하지 않는다. 외부 LLM/API 없는 독립 상주 RTL 생성 서비스는 포함하지 않는다.

## 자동 Vivado 실행

`run_loop.py resume`의 승인 검증을 통과한 격리 복사본에서 다음 순서로 실행한다.

| 단계 | 자동 처리 | 보관 위치 |
|---|---|---|
| compile | Vivado XPR 생성, RTL/헤더/TB·Top 지정, XSim compile | artifacts/verification/<target>/run_NNN |
| simulation | memory/testdata 상대경로 자동 배치, XSim 시작, SAIF 수집, Golden 결과 검사 | 같은 verification 폴더 |
| synthesis | 동일 소스 합성, 자원/RAM/Timing/DRC/Power 보고서, DCP | artifacts/synthesis/<target>/run_NNN |
| implementation | 동일 합성 DCP에서 opt/place/phys_opt/route, 최종 보고서와 DCP | artifacts/implementation/<target>/run_NNN |
| power | 동일 Routed DCP에 SAIF 적용, 매칭 보고서·전력·에너지 계산 | 같은 implementation 폴더 |

프로젝트와 임시 도구 상태는 기존 `.automation_debug`의 격리 workspace 내부 `.vivado_flow`에 둔다. 원본 workspace를 덮어쓰지 않는다.
보고서 분석용 묶음도 implementation에 둔다. 앞으로 `artifacts/automation_loop` 또는 `artifacts/power` 같은 새 분류를 만들지 않는다.
합성 직후 결과와 Post-Route 결과는 별도 폴더에 보존하고 전력 분석은 power_post_route.rpt를 우선 사용한다.
오류/Timeout/입력 누락/Golden 실패 시 후속 단계를 중지한다. 도구 종료 코드 0은 Timing/DRC 합격을 뜻하지 않는다.
Bitstream 생성과 보드 프로그래밍은 실행하지 않는다. 보드 pin/IOSTANDARD/I/O delay를 임의 생성해 경고를 숨기지 않는다.
현재 기본 part=xc7z020clg400-1, clock=10 ns이며 승인된 constraints/*.xdc가 있으면 함께 사용/해시한다.
SAIF는 Behavioral 활동 기반 추정이다. 실측이나 100% 내부 활동 매칭으로 표현하지 않는다.

## 승인 경계

1. SPEC 보완안을 개발자가 승인하면 immutable SPEC 버전과 digest를 확정한다.
2. 현재 소스/입력/도구/증거/정책에 연결된 모든 Finding에 승인 또는 거절 결정을 기록한다.
3. Agent는 승인 Finding→SPEC ID→수정 파일→검증의 patch_trace를 작성한다.
4. 재검증에서 새 문제가 생기면 다음 Run의 보완안을 작성하고 다시 승인을 기다린다.
5. 최종 accept는 기능·Timing·DRC·coverage·동일 소스 실행 출처·SPEC 조건을 요구한다. 사용자 승인만으로 UNKNOWN/FAIL을 PASS로 바꾸지 않는다.

전력 회귀는 개발자의 `average_power / energy_per_workload / balanced` 선택, 전력·에너지 상한과 근거를 요구한다. 수치 제안은 별도 문서이며 미승인 상태다.
승인된 power_tradeoff의 두 상한은 자동 평가한다. 한 지표의 개선으로 다른 지표의 초과를 면제하지 않으며 값이 없으면 UNKNOWN이다. 증거 품질에 대한 최종 Gate 검토는 유지한다.
계측되지 않은 PE 동시 동작·protocol·interrupt 조건은 UNKNOWN이다. 필요한 계측 추가도 승인 범위에 명시해야 한다.

## 기존 계층 유지

`artifacts/{verification,synthesis,implementation}` / `experiments/{prototype_generation,optimization_generation,automation_loop,comparative_evaluation,verification_generation}` / `manifests` / `rag/{automation,config}` / `workspace/<target>/{rtl,tb,memory,scripts,reports}`를 유지한다.
analysis_NNN은 분석 결과이며 실제 패치 실행이 아니다. run_NNN은 실행 이력을 구분한다. 기존 run_001/002의 생성 당시 의미는 과거 manifest가 기준이다.
요청 접수·승인 SPEC 버전 폴더는 해당 이벤트가 발생할 때만 필요한 기록이다. 날짜 폴더나 중복 리뷰 폴더를 만들지 않는다.
기존 증거와 승인 이력은 삭제하지 않는다. 변경된 해시로 과거 승인을 다시 유효화하지 않는다.
`__init__.py`는 Python 패키지 파일이며 유지한다. `tool_flow.py`, `vivado_flow.tcl`, `lifecycle.py`, 테스트 파일은 자동 실행에 필요하므로 유지한다.

## Agent 내부 명령 흐름

개발자가 직접 명령을 입력하는 대신 Agent가 단계별 상태를 확인해 실행한다. 승인 명령은 실제 사용자 승인 이후에만 사용한다.

```text
intake → sync → analyze → (개발자 검토)
approve-spec → bind-spec → approve → resume
waiting_for_agent_patch → 승인된 패치/trace 작성 → resume
새 run의 diagnosis/spec_change_proposal → (개발자 재검토)
review-requirement → accept
```

실제 인자는 `run_loop.py --help`와 각 서브명령의 `--help`를 사용한다. 원문 요구와 조건을 임의로 승인하지 않는다.
approval.yaml, gate_status.json, run_manifest.yaml이 승인·출처 기준이며 requirements_result.json과 optimization_assessment.json이 충족/회귀 기록이다.
RAG 갱신은 refresh_automation_inventory.ps1과 build_index.py를 통해 로컬에서 수행한다. 실패 시 숨기지 않고 중지한다.

## 통합된 시뮬레이션 진단

과거 expected=x/파일 열기 실패는 `$readmemb` 상대경로가 XSim 실행 폴더와 달라서 발생했다. 자동 어댑터가 같은 구조로 memory와 testdata를 복사한다.
Design Top=zyNet, Simulation Top=top_sim을 자동 지정하여 테스트벤치가 합성되는 문제를 방지한다.
SAIF 객체는 `/top_sim/device_under_test/*`이며 없으면 실패 처리한다. read_saif strip_path는 선행 / 없이 사용한다.
reset_switching_activity/report_switching_activity는 명시적인 객체 목록을 전달한다.
수동 해결책 설명은 이 절로 통합했으므로 SIMULATION_DIAGNOSIS.md는 삭제한다. 과거 내용은 Git 이력으로 복구할 수 있다.

## 검증 및 현재 상태

실제 가속기 RTL 최적화는 미승인이다. 자동화 프로그램 테스트와 실제 회로 최적화 성공을 구분한다.
작은 독립 테스트 회로에서 Vivado 전체 흐름을 검증하고 결과를 기존 system_validation_002에 기록한다.
최신 Gate 전 증거 재분석/해시 바인딩이 필요하다. 기존 분석이 현재 코드에 이미 승인된 것으로 처리하지 않는다.
**Run is not approved for patch generation.**

# 승인 기반 RTL 자동화 Loop

## 승인된 디버깅 실행 기록

이번 실행의 권한 원문은 `experiments/automation_loop/optimized_accelerator/requests/request_002/request.md`에 보존한다. 개발자가 TB 수정도 별도로 승인했다. 기존 SPEC·MNIST·Golden·Accuracy·클록·Timeout 완화는 허용되지 않는다.

기본 패치 범위는 기존 RTL이며, 승인 SPEC의 `patch_scope.additional_existing_files`에 명시된 경우에만 기존 `tb/top_sim.sv` 한 파일을 추가 허용한다. 다른 TB·메모리·입력·constraints 경로를 이 방법으로 변경할 수 없다. 패치 trace와 소스/도구/증거 hash 검사는 유지된다.

`run_003`은 Agent의 TB 계측 중복 삽입으로 Compile 실패했다. 원본 TB 누락이라는 초기 진단은 오류이며, 원본 Compile 재실행으로 정상임을 확인했다. 원본을 결함 코드로 분류하지 않는다. 실패 기록을 삭제하지 않고 `request_003`의 명시적 재승인으로 후속 검증을 연결한다.

`workspace/rag_debug_output_001`의 결과 보관은 개발자 검토용 후보 공개이며 최종 수락이나 `Project_Git` 승격이 아니다. 원본 `workspace/optimized_accelerator`는 보존한다. `.automation_debug`는 로컬 도구 작업 공간으로 Git에서 제외하고 실행 로그/보고서/패치/승인 및 출력 소스는 별도 보존한다.

최신 동일 조건 재측정 비교와 잔여 Gate 표는 `workspace/rag_debug_output_001/reports/diagnosis.md`에 있다. 후속 SPEC 보완안은 `experiments/automation_loop/optimized_accelerator/analysis_006/spec_change_proposal.md`이며 아직 승인하지 않았다.

## 디버깅 전 구축 상태 확인

승인 기반 반자동 실행 경로는 구현되어 있고 가속기 run_004의 5단계 도구 실행도 완료했다. 다만 독립 상주 Agent 서비스나 최종 자동 승격을 의미하지 않으며 DRC/외부 제약과 사람의 최종 수락은 미결이다. 프로그램 자동 처리와 활성 Agent의 설계 판단, 개발자 승인을 구분한다.

| 순서 | 알고리즘 단계 | 자동화 구분 | 실제 구현과 한계 |
|---|---|---|---|
| 1 | 개발자 요구사항 입력 | 개발자 | SPEC/목표와 변경 범위를 제공한다. |
| 2 | 원문 보존·ID·Chunking·RAG 등록 | 프로그램 자동 + Agent 검토 | intake/sync가 문서·인덱스를 생성한다. 의미 해석과 검증 조건 구체화는 Agent가 수행한다. |
| 3 | 실행 증거 분석·Finding 문서화 | 프로그램 자동 | parsers/detectors가 지원 보고서를 분석한다. 누락은 UNKNOWN이며 모든 RTL 결함을 증명하는 것은 아니다. |
| 4 | 구체적인 SPEC 변경안 | 자동 초안 + Agent | 유형별 제안/표는 자동 생성한다. 구조 선택과 실현 가능한 수치 설계는 Agent가 검토한다. |
| 5 | 개발자 SPEC 승인 | 개발자 | 자동 승인하지 않는다. 전력/에너지 우선순위와 상한도 승인 대상이다. |
| 6 | 승인 SPEC 버전 확정·Run 연결 | 프로그램 자동 | approve-spec/bind-spec에서 버전·digest·요구사항을 연결한다. 명령 호출은 승인 후 Agent가 담당한다. |
| 7 | 수정할 Finding 승인 | 개발자 + 자동 검사 | 각 Finding 결정과 승인 SPEC 연결, 최신 hash를 검사한다. |
| 8 | Agent 패치 작성 | 활성 Agent | resume는 패치가 없으면 waiting_for_agent_patch로 멈춘다. Python이 Agent를 자체 호출하지 않는다. |
| 9 | 격리 소스에 적용 | 프로그램 자동 | 패치 범위·trace 검증 후 격리 복사본에 적용한다. 현재 허용 범위는 기존 RTL 파일 변경이다. |
| 10 | Compile | 프로그램 자동 | Vivado 프로젝트·Design/Simulation Top 및 파일 목록을 구성한다. |
| 11 | Simulation·SAIF 수집 | 프로그램 자동 | 입력 데이터 배치, XSim 실행, Golden 결과 확인과 SAIF 수집. 미계측 검증 항목은 UNKNOWN이다. |
| 12 | Synthesis | 프로그램 자동 | 자원/RAM/Timing/DRC 보고서와 합성 DCP를 생성한다. |
| 13 | Implementation·Post-Route | 프로그램 자동 | 배치·배선 및 보고서를 생성한다. 종료 코드 0만으로 타이밍 합격 처리하지 않는다. |
| 14 | SAIF 적용·Power/Energy | 프로그램 자동 | Routed DCP에 SAIF를 적용하고 전력 및 구간 에너지를 추정한다. 실측 전력이 아니다. |
| 15 | 요구사항 충족·PPA 회귀 분석 | 프로그램 자동 + Agent/개발자 판단 | 비교 조건 및 수치 상한을 검사한다. PPA 절충 선택과 미확정 조건 결정은 자동화하지 않는다. |
| 16 | 개선 필요: 다음 Run·SPEC 초안 | 프로그램 자동 → 재승인 대기 | 후속 분석을 생성하되 새로운 디버깅 권한을 자동 부여하지 않는다. |
| 17 | 충분함: 최종 증거 확인·수락 | 자동 검사 + 개발자 수락 | accept가 동일 소스 실행, 기능/Timing/DRC/coverage/SPEC 조건을 검사한다. FAIL/UNKNOWN은 수락할 수 없다. |
| 18 | 결과 코드 공개 | 자동 배포 미구현 | 현재 promoted=False다. 번호별 결과 폴더는 준비하며 실제 코드 게시와 출처 연결은 승인 작업에서 Agent가 수행해야 한다. |

### 구축 구성요소와 검증 범위

| 구성 | 구체적인 역할 | 코드/기록 |
|---|---|---|
| 증거 분리 | 원본 도구 로그와 분석·승인 기록을 구분한다. | artifacts/{verification,synthesis,implementation}, experiments/automation_loop |
| 탐지 확장 | 자원·Timing·메모리 매핑·주소/MUX·Fanout·DRC·증거 누락·SAIF 전력/에너지 회귀를 검사한다. 원인 가설과 입증된 수치를 구분한다. | parsers.py, detectors.py, lifecycle.py |
| 추적 연결 | Requirement/Finding/패치 trace/재검증 및 소스·입력·정책·도구 hash를 연결한다. | run_loop.py, lifecycle.py, run_manifest.yaml |
| 승인 보호 | 승인 없는 패치, 오래된 바인딩, 허용 밖 파일 변경을 차단한다. 원본 workspace에 바로 적용하지 않는다. | approval.yaml, gate_status.json, validate_patch |
| 실행 연결 | Vivado compile/simulation/synthesis/implementation/power 5단계를 실행하고 실패·Timeout 시 중단한다. | tool_flow.py, vivado_flow.tcl, rag/config/automation_loop.yaml |
| 반복 구성 | 재검증을 다음 분석·제안으로 연결하고 재승인을 기다린다. 반복 한도와 동일 문제 반복을 검사한다. | run_loop.py, lifecycle.py |
| 경험 검색 | 허용된 로컬 문서와 실패/수정/검증 이력을 인덱스에 반영한다. 외부 LLM API 및 historical_baselines 근거를 사용하지 않는다. | manifests, rag/config/automation_loop_index.yaml |
| 시스템 검증 | 57개 Python 테스트 통과. 독립 소형 회로 검증과 별개로 가속기 run_004의 Vivado 5단계도 완료했다. I/O 제약과 최종 증거 수락은 미결이다. | experiments/automation_loop/system_validation_002/diagnosis.md |

### 번호별 디버깅 결과 폴더

`workspace/rag_debug_output_001/{rtl,tb,memory,scripts,reports}`에는 run_004에서 실행한 후보와 검증 출처가 보관되어 있다. 원본 `optimized_accelerator`의 직접 하위 폴더 구성과 같고 출력 소스의 해시 일치를 확인했다.
현재 실행기는 logical target인 optimized_accelerator와 격리 workspace를 사용한다. 새 폴더를 독립 실행 target으로 등록하거나 자동 export를 구현한 것은 아니다.
다음 승인에 따른 별도 디버깅 결과는 002, 003 순서로 보존하며 기존 결과를 덮어쓰지 않는다. output 번호와 analysis/run 번호는 별개다.
게시 시 reports에 원본 target·승인 SPEC·Finding·실행 Run·소스 hash·검증 상태를 연결해야 한다. 실패한 결과도 성공으로 표시하지 않는다.

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

첫 최적화와 TB 수정/재시도는 request_002/003으로 승인되었으며 spec_001/002에 연결했다. run_003의 Compile 실패는 보존하고 run_004의 Compile/Simulation/Synthesis/Implementation/SAIF Power는 모두 종료 코드 0이다.
57개 자동화 회귀 테스트를 재실행했고 원본과 후보의 100개 MNIST 예측이 모두 동일함을 확인했다. 증거는 workspace/rag_debug_output_001/reports와 artifacts에 보관한다.
수치 조건과 사람의 최종 증거 검토는 다르다. 남은 DRC/외부 제약 및 추가 보완안에는 새 승인이 필요하다. 승인 없이 다음 RTL 패치나 Project_Git 승격을 실행하지 않는다.

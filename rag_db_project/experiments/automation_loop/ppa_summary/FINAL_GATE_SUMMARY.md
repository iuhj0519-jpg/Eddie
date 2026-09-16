# 자동화 Loop 구축 정리 및 최종 실행 Gate

상태: **PPA 분석 종료 / 승인 기반 Loop 구현 / 실행 승인 대기**.
**Run is not approved for patch generation.** 이 문서는 승인서가 아니며 RTL 패치나 run_003 실행을 허가하지 않는다.
완전 무인 End-to-End 시스템으로 표현하지 않는다. Post-Route/SAIF 수집은 수동이고, 패치는 사용자 승인 후 현재 Agent가 작성한다.

## 1. 탐지 범위, 자동 판단, 개발자 승인

아래 수치는 기존 analysis_003의 자동 진단과 최종 SAIF 보완 근거를 구분해 합친 검토 표다.
23개 기존 Finding에 SAIF 전력 회귀 보완 요구가 추가되었다. 이는 독립적 결함 24개를 의미하지 않는다.
원인별 중복 증거가 있고 일부는 원인 가설/증거 부족이다. 자동 분석을 새로 수행한 것으로 표시하지 않는다.

| 범위 / Finding | 관측 근거 및 Loop 판단 | Gate에서 결정/확인할 내용 |
|---|---|---|
| PE/DSP: PPA-DSP-001 | 기대 25 PE 대비 DSP 5개. PE 비활성이나 DSP 부족을 확정한 것은 아님 | PE 병렬성·수치 정합성 검증, LUT MAC 허용 여부 또는 DSP 매핑 목표. 현재 초안 DSP>=25 조건도 승인 전 확인 |
| Weight 자원: PPA-WEIGHT-001 | Weight LUT 13,955 / 전체 18,060 = 약 77.27%; 자원 집중 | Weight 접근/선택 구조 최적화 범위 및 자원 목표 |
| 물리 RAM: PPA-MEMORY-MAPPING-001 | Weight BRAM/LUTRAM 0; SRAM 모듈명이 물리 RAM 구현 증거는 아님 | 물리 BRAM 요구를 SPEC으로 확정; 5-bank 공급, 용량, 초기화, 동기 read latency 보존 |
| Setup: PPA-TIMING-001 | WNS -5.362 ns, TNS -252.171 ns, 실패 Endpoint 104 | 목표 clock 유지, 파이프라인/latency 변경 허용 범위; 최종 수락에는 timing 통과 필요 |
| 주소: PPA-ADDRESS-001 | controller cycle_count → Weight read 경로에 주소/제어 계산 관측 | 주소 연산·폭·뱅크 decode 수정 승인; 원인 가설을 RTL/netlist로 검증 |
| 선택/단계: PPA-MUX-001, PPA-PIPELINE-001 | 실패 경로에 MUX와 깊은 논리 경로 | 선택 회로 축소, pipeline 추가와 valid/data/scheduler 정렬 승인 |
| 배선/Fanout: PPA-ROUTE-DELAY-001, PPA-FANOUT-001 | 최악 경로 delay 15.216 ns 중 route 9.710 ns; Weight 신호 fanout 2,415 사례 | 복제·로컬 제어·파이프라인의 area/latency 비용 판단; 높은 fanout 자체만으로 원인 확정 금지 |
| DRC: IMPL-DRC-001 및 DRC-* | 집계 critical warnings 4; NSTD-1, UCIO-1, CHECK-3, DPIP-1, DPOP-1/2, RBOR-1, REQP-1840, ZPS7-1 검토 대상 | 실제 보드 pin/IOSTANDARD와 reset/DSP 등록 조건 결정; 경고 억제로 PASS 처리 금지 |
| I/O 제약: PPA-CONSTRAINT-001 | 입력 delay 누락 20, 출력 delay 누락 11 | 외부 인터페이스 timing contract 결정. clock만 맞췄다고 전체 timing coverage 통과로 처리하지 않음 |
| 전력 증거: PPA-POWER-001 | 과거 Low는 SAIF 보완에서 Medium으로 개선; 직접 매칭은 약 1.49% / 1.25% | 추정치 한계 검토. 기존 자동 finding 기록을 무단 PASS로 바꾸지 않고 재분석에 최신 증거 사용 |
| SAIF 회귀: REGRESSION-TOTAL-ON-CHIP-POWER-W | 수동 보완 비교 0.544 → 0.607 W, +11.58%; 구간 에너지 추정 약 -1.77% | 개발자가 평균 전력/작업당 에너지/균형 우선순위, 두 허용 상한, 판단 근거 선택. 자동 면제 없음 |
| 기능·성능 보존 | 별도 simulation 결과 99/100, 완료 시간 1,837,345 → 1,617,525 ns; 같은 inference-cycle 계측값 비교는 아님 | sample별 결과, protocol, batch interrupt, overlap/backpressure 검증 기준 유지. 99%만으로 기능 동등성 전체 입증 불가 |
| 출처/누락: EVIDENCE-PROVENANCE-001, EVIDENCE-COVERAGE-001 | checkpoint 생성 당시 RTL hash 연결 누락; 기존 분석 묶음의 RAM/verification/flat utilization 등 UNKNOWN | 같은 source/run의 로그·보고서를 수집하고 fresh binding 생성. 다른 폴더에 자료가 있다는 이유만으로 자동 PASS 금지 |

Weight/Bias를 모두 동일한 규모의 병목으로 보지 않는다. 위 물리 BRAM 강제 요구는 Weight 대상이며 Bias의 구현 정책은 별도 SPEC 판단이다.
버퍼 LUT 143→60(-58.04%)와 전체 LUT 18,029→18,060(+0.17%)를 구분한다. 버퍼 BRAM 2.5 Tile은 그대로다.

## 2. Loop 단계와 구현 경계

| 단계 | 구현 / 기록 | 경계 |
|---|---|---|
| 요구사항 접수 | intake → requests/request_NNN, 요구사항 ID | 자연어 의미와 수용 조건은 사람이 검토; 무조건 자동 SPEC 승인 아님 |
| Chunking/RAG | lifecycle sync → 로컬 인덱서, 체크섬, allowlist | 외부 LLM/API 및 historical_baselines를 디버깅 근거로 사용하지 않음 |
| 탐지/분석 | parsers.py, detectors.py, analyze → findings/diagnosis/coverage | 규칙 기반; 모든 결함/최적해 보장 아님 |
| SPEC 보완 | requirements.yaml, spec_change_proposal.md | 모든 Finding을 승인 조건과 연결; SAIF tradeoff 별도 개발자 판단 |
| SPEC 승인 | approve-spec, 버전 및 digest 고정 | 우선순위/상한/근거 미정이면 전력 회귀 SPEC 승인 차단 |
| 실행 승인 | bind-spec + approve → approval.yaml | 모든 Finding의 승인/거절 결정, 승인 SPEC ID와 fresh hash 필요 |
| 패치 작성 | resume → patch_request.json → Agent patch + trace | 패치 없으면 waiting_for_agent_patch; 무인 LLM 서비스 자동 호출 아님 |
| 격리 실행 | resume → Compile / Simulation / Synthesis | 원본 workspace 자동 덮어쓰기 금지; 실패 시 중단 |
| 재분석/반복 | 후속 run_NNN, 비교·SPEC 제안·재승인 | 추가 개선은 새 승인 대상; 최초 승인이 모든 반복의 포괄 승인 아님 |
| Post-Route/SAIF | 사용자가 수집한 같은 source 증거 | 현재 자동 실행 stage 아님 |
| 최종 설계 수락 | review-requirement → accept → final_acceptance.yaml | 요구사항, 기능, Timing/DRC/출처/coverage 검증 및 사람의 절충 판단. 에너지는 현재 수동 증거 검토 |

## 3. 이번 Git 반영과 아직 필요한 승인 준비

- SAIF 비교 보고서 두 개, 원본 SAIF 해시/시간 메타데이터, ns→J 계산, 전력 회귀 초안을 기존 ppa_summary/analysis_003에 보관했다.
- 요구사항의 power_tradeoff는 priority, max_average_power_w, max_energy_per_workload_uj, rationale을 미정으로 유지한다.
- 기존 자동 진단/coverage/optimization_assessment는 과거 실행 기록으로 보존한다. 새 SAIF 비교를 이미 자동 재분석한 것으로 표시하지 않는다.
- 다음 실행 승인 전에 최신 증거의 source/workload/조건 연결 및 재분석이 필요하다. 분석 재생성 시 SAIF 회귀 보완 요구를 반드시 함께 이관해야 한다.
- 출처를 복원할 수 없다면 기존 source hash를 추측해 채우지 않는다. 승인 후 검증 실행으로 새 증거를 확보하며, 최종 설계 수락은 그 전까지 차단한다.
- 현재 Timing 실패는 수정 실행을 승인할 이유일 수 있지만 최종 설계 수락 조건을 만족한다는 뜻은 아니다.
- SPEC/실행 승인을 실제로 수행하지 않았으며 run_003, proposed_patch.diff, final_acceptance.yaml을 이번 정리 작업에서 만들지 않았다.

## 4. Git 탐색 위치

| 목적 | 프로젝트 루트 rag_db_project 기준 경로 |
|---|---|
| 이 최종 표 | experiments/automation_loop/ppa_summary/FINAL_GATE_SUMMARY.md |
| PPA 종료 근거·계산 | experiments/automation_loop/ppa_summary/SAIF_GATE_REVIEW.md, saif_evidence.json, *_power_saif.rpt |
| 기존 탐지/진단 | experiments/automation_loop/optimized_accelerator/analysis_003/findings.yaml, diagnosis.md |
| 미승인 SPEC 및 전력 선택 | 같은 analysis_003/requirements.yaml, spec_change_proposal.md |
| 실행 승인 및 source binding | 같은 analysis_003/approval.yaml, gate_status.json, run_manifest.yaml |
| 요구 충족/비교 기록 | 같은 analysis_003/requirements_result.json, optimization_assessment.json, coverage.json |
| Loop 설명 | rag/automation/README.md, LIFECYCLE.md, DIRECTORY_POLICY.md |
| 실행/검출/승인 구현 | rag/automation/run_loop.py, parsers.py, detectors.py, lifecycle.py |
| 도구·임계값·물리 메모리 제안 | rag/config/automation_loop.yaml |
| 접근 정책·출처 검증 | manifests/automation_loop_policy.yaml, phase_access_policy.yaml, checksums/automation_loop_files.sha256 |

## 5. 검증

자동화/승인 회귀 테스트 47개 통과(격리 Fixture). 테스트 안의 approved 출력은 실제 설계 승인과 무관하다.
실제 도구 adapter 이전 검증과 구분하며, 이번 정리에서 Compile/Simulation/Synthesis/Post-Route를 다시 실행하지 않았다.
최종 상태: pending_human_approval. 미해결 항목을 사용자 승인만으로 검증 PASS로 치환하지 않는다.

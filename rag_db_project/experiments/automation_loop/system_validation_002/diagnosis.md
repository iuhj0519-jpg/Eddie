# 자동화 시스템 검증 기록

이 문서는 DUT 최적화 결과가 아니라 자동화 프로그램 검증이다. 실제 Gate/승인 SPEC은 변경하지 않았고 run_003을 생성하지 않았다.

| 검사 | 결과 | 범위 |
|---|---|---|
| Python 회귀 테스트 | 56개 PASS | 승인 차단, 오래된 hash, 실패 중단, 5단계 실행 연결, 미승인 자식 Run, SAIF 단위·에너지 계산, 에너지 회귀/승인 상한, XSim 입력 경로 |
| 실제 Vivado 프로젝트/compile | 종료 코드 0 | 독립 8-bit 테스트 회로, XPR/Top/include 생성 |
| 실제 XSim + SAIF | 종료 코드 0 | 테스트 회로 100회 연산, 메모리/입력 상대경로 로딩 확인, SAIF 파일 생성 |
| 실제 Vivado synthesis | 종료 코드 0 | 동일 fixture의 DCP/보고서 생성 |
| 실제 Vivado implementation | 종료 코드 0 | opt/place/phys_opt/route 및 DCP/route 보고서 생성 |
| 실제 SAIF power | 종료 코드 0 | Routed DCP에 activity 적용 및 전력/에너지 보고서 생성 |

원본 로그: `artifacts/automation_system_tests/run_002/vivado_<stage>.log`.
실행 결과: 같은 폴더 `vivado_flow_result.json`, `vivado_activity_metrics.json`.
소스 fixture: 같은 폴더 `vivado_fixture_rtl.sv`, `vivado_fixture_tb.sv`.
가속기 전체의 물리 구현 결과나 성능 통과가 아니다. 가속기 실제 최적화·5단계 실행은 다음 Gate 이후 수행한다.
테스트 회로는 보드 I/O 제약 미지정 경고가 있을 수 있으며 도구 실행 성공과 DRC 최종 합격을 구분한다.

## 기존 검증 이력

기존 Lifecycle 42개/47개 회귀 테스트와 6개 RAG 검색 검증은 과거 검증 기록이며 원본은 기존 artifacts/automation_system_tests에 보존한다.
예전 expected=x 및 잘못된 top/source 문제는 새 자동 입력 배치와 project 생성으로 재발 방지 경로를 추가했다.
외부 웹은 사용자가 요청한 블로그 계층 확인에만 접근을 시도했으며, 실제 RTL 설계/디버깅 근거로 사용하지 않았다.
현재 Agent는 로컬 정책/DB와 승인된 SPEC만으로 설계한다. 추가 외부 LLM API를 호출하지 않는다.

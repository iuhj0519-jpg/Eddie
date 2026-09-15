# Loop 디렉터리 이름과 생성 규칙

달력 날짜를 디렉터리 식별자로 사용하지 않는다. 승인 시간 등 감사용 timestamp는 메타데이터에 보존한다.

| 위치 | 목적 | 생성 조건 |
|---|---|---|
| `<target>/analysis_NNN/` | 기존 증거에 대한 분석, Finding, SPEC 초안, 승인 대기 | 새 증거/규칙으로 명시적인 분석을 수행할 때 |
| `<target>/run_NNN/` | 승인된 패치의 도구 실행과 후속 분석 | Gate 승인 + 패치 적용 후 Compile/Simulation/Synthesis 실행 시 |
| `<target>/requests/request_NNN/` | 사용자 원문과 요구사항 | 새로운 요구사항 접수 시 |
| `<target>/spec_versions/spec_NNN/` | 승인된 추가 SPEC 버전 | 명시적인 SPEC 승인 시 |
| `system_validation_NNN/` | Loop 프로그램 자체의 검증 경과 | 시스템 기능 변경과 테스트 시 |
| `ppa_summary/` | PPA 최종 요약과 Power 절차 | 해당 요약 문서 갱신 시; 날짜별 폴더를 추가하지 않음 |

analysis는 RTL을 실행했다는 뜻이 아니다. 분석을 열람하거나 설명하는 것만으로 새 폴더를 만들지 않는다.
현재 analysis_001~003은 각각 이전 Post-Route 재분석/탐지기 보완/SPEC Lifecycle 보완의 기록이다.
내용이 동일한 복사본은 아니며, 새로운 DUT 실행 3회를 의미하지도 않는다.
기존 run_001/run_002는 초기 구축 방식으로 작성된 기록이므로 이름을 보존한다. 앞으로의 생성 규칙과 혼동하지 않는다.
승인 후의 child Run 안에 분석/다음 SPEC 제안을 함께 저장하며 별도 analysis를 매번 중복 생성하지 않는다.

## 이번 정리의 상태

기존 날짜형 review 3개를 analysis_001~003으로 이름만 옮기고 문서/인덱스 참조를 수정했다.
추가 분석/디버깅 Run을 만들지 않았으며 원본 RTL/TB/Memory/보고서/로그를 수정하지 않았다.
이름/Runtime 변경 후 과거 binding은 이전 실행의 해시 증거이므로 임의 재서명하지 않는다.
다음 승인 전에 명시적으로 재분석해야 한다. 현재 승인 상태는 모두 not_approved이다.
변경 전 이름과 내용은 Git 이력으로 추적할 수 있다.

기본 analyze 명령은 analysis 순번만 소비한다. resume의 자동 재검증은 run 순번만 소비한다.
미래 코드에서 날짜형 review ID는 거부한다. status는 analysis와 run을 모두 표시한다.

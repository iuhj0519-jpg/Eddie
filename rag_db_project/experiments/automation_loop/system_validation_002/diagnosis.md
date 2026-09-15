# SPEC Lifecycle 시스템 검증 — 2026-09-13

상태: 시스템 기능 구현/fixture 검증 완료. 실제 설계 SPEC/Finding 승인은 미실행.
최신 대상: optimized_accelerator/analysis_003. Run is not approved for patch generation.

- 요구사항 intake: 이번 요청을 requests/request_001에 보존. 이 요청은 자동화 구축/진단 지시이며 RTL 설계 제약으로 자동 승인하지 않았다.
- 보고서 분석: 기존 Post-Route 원본에서 23개 Finding 및 상세 요구사항 23개를 생성했다. 신규 simulation 결과를 만들지 않았다.
- 각 요구사항: 변경 전 증거, 변경 목표, acceptance, 검증 방법, 효과, 위험을 기록한다.
- SPEC 개정: baseline을 보존하는 승인된 versioned overlay. 실제 승인 버전은 아직 생성하지 않았다.
- 승인/실행: 실제 Requirement ID/Finding 연결, source/spec/runtime/evidence hash, fresh human decision을 요구한다.
- 반복: 부모 SPEC/격리 소스 승계, 재검증, 새 초안 생성, 재승인. 조건이 다른 PPA 비교는 확정 개선으로 보지 않는다.
- 최종 수락: 같은 소스의 compile/simulation/synthesis/implementation 및 실제 증거가 필요하다. 자동 승격 안 함.
- 테스트: 설치본 unittest 42개 PASS. 기존 RAG 검색 6개 PASS, 금지 출처 Chunk 0.
- 시스템 테스트의 승인/수락은 TemporaryDirectory fixture 내부에서만 이루어졌다. 생산 RTL의 승인/run_003가 아니다.

검증 원본: artifacts/automation_system_tests/lifecycle_validation_001/unittest.log 및 verification_result.json.
초기 작업 중 RAG가 아직 없는 승인 문서 패턴을 필수로 취급해 실패했다. 명시적인 optional allowlist로 해결했으며
없는 승인/성공 문서를 가짜로 만들지 않았다. initial_draft/second_draft는 작업 중간 스냅샷으로 보존하며 RAG 검색에서 제외된다.

Vivado: XPR이 Git optimized 대신 작업폴더 루트 소스를 참조하고 Design Top=top_sim이었다.
첫 오류는 Weight_SRAM.sv:39 string 선언. 실행 Tcl은 run 1000ns; simulate.log는 0 byte.
올바른 source/top으로 실행한 Console/Simulation 로그가 오면 별도 증거로 수집해야 한다.

사용 매뉴얼: rag/automation/LIFECYCLE.md, rag/automation/SIMULATION_DIAGNOSIS.md.
외부 Web/LLM/API 및 Historical Baseline을 디버깅 근거로 사용하지 않았다.

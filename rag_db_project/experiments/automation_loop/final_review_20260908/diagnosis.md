# 자동화 Loop 최종 승인 전 정리 — 2026-09-08

상태: pending_human_approval. Run is not approved for patch generation.
최신 기계 판독 결과는 ../optimized_accelerator/review_20260908/findings.yaml,
승인은 같은 디렉터리의 approval.yaml을 사용한다. review_20260907은 이전 코드/설정에 바인딩되어 있으므로 승인 대상으로 사용하지 않는다.
run_001/run_002의 과거 기록과 실제 Debugging용 run_003은 그대로 보존/미생성 상태다.

## SPEC 대조

승인 Systolic SPEC §8 및 REQ-SYS-009에는 Weight/Bias 5-bank SRAM 요구가 있다.
OPT-SPEC-001 §10.1 및 REQ-OPT-014는 Unified Buffer의 BRAM-Friendly 구현을 명시한다.
Weight의 물리 BRAM primitive 매핑을 별도 필수 합격 조건으로 명시한 조항은 없었다.
따라서 `SRAM이라는 이름 = FPGA BRAM 구현 보장`으로 해석하지 않는다.
[보완안](spec_change_proposal.md)의 REQ-OPT-MEM-026은 최종 승인 대기이며 기존 승인 SPEC을 변경하지 않았다.

## 최신 탐지 테이블

이전 그림의 13,930 LUT / WNS -4.805 ns / 0.268 W는 합성 단계 결과다.
아래는 2026-09-08 ppa_final 원본을 사용한 Post-Route 결과이며 혼합하지 않는다.
23개 Finding은 독립적인 결함 23개라는 뜻이 아니다. 원인의 중복 증거 및 증거 품질 문제도 포함한다.

| Finding | 자동 검출 결과 | 설명 / 승인 후 검토 |
|---|---|---|
| PPA-DSP-001 | DSP48 5개, 모두 Weight 계층 | 25 PE의 DSP MAC 매핑을 입증하지 않음. PE Utilization 20%라는 뜻은 아님 |
| PPA-WEIGHT-001 | Weight LUT 13,955 / 전체 18,060 ≈ 77.27% | 자원 집중 문제 |
| PPA-MEMORY-MAPPING-001 | Weight RAMB18=0, RAMB36=0, LUTRAM=0, Logic LUT=13,955 | 요청한 Block Memory 물리 매핑 부재. LUT 점유율 임계값과 독립 탐지 |
| PPA-TIMING-001 | WNS -5.362 ns, TNS -252.171 ns, 실패 104/3043 | 100 MHz Setup 미충족 |
| PPA-POWER-001 | Total 0.332 W, Dynamic 0.224 W, Static 0.108 W, Low | SAIF 없음. 활동 기반 재분석 필요 |
| PPA-ADDRESS-001 | cycle_count → Weight read_data 경로에 주소/제어 계산 포함 | 주소식·폭·bank decode·read latency 검토 |
| PPA-MUX-001 | 실패 경로에 MUXF7/MUXF8 포함 | Weight LUT 전체가 MUX라는 뜻은 아님. 큰 선택 회로와 storage 구조를 함께 검토 |
| PPA-PIPELINE-001 | 최악 경로 Logic Levels 17 | 분할 시 Valid/주소/Scheduler/Cycle 계약 정렬 필수 |
| PPA-ROUTE-DELAY-001 | 지연 15.216 ns 중 Route 9.710 ns ≈ 63.8% | 배선 지연 우세, 곧바로 congestion 확정은 아님 |
| PPA-FANOUT-001 | 최대 보고 Fanout 2,415 | Weight DSP 출력의 많은 부하; 부하 분산 및 주소/선택 회로 검토 |
| IMPL-DRC-001 | DRC 요약 경고 존재 | 아래 개별 Rule의 집계 Finding |
| DRC-NSTD-1 | 1건, IOSTANDARD 미지정 | 보드 I/O 전기 조건 필요 |
| DRC-UCIO-1 | 1건, LOC 미지정 | 보드 pin 제약 필요 |
| DRC-CHECK-3 | 1건, Rule 보고 제한 도달 | 표시된 수가 모든 위반 수를 보장하지 않음 |
| DRC-DPIP-1 | 10건, DSP 입력 파이프라인 | DSP 입력 register 검토 |
| DRC-DPOP-1 | 5건, DSP PREG 출력 파이프라인 | 출력 단계 검토 |
| DRC-DPOP-2 | 5건, DSP MREG 파이프라인 | 내부 연산 단계 검토 |
| DRC-RBOR-1 | 5건, BRAM 출력 register | read latency 정렬 포함 검토 |
| DRC-REQP-1840 | 20건, BRAM 비동기 제어 | reset의 BRAM 입력 경로 영향 검토 |
| DRC-ZPS7-1 | 1건, PS7 구성 | Zynq 보드 통합 범위에서 검토 |
| PPA-CONSTRAINT-001 | Input Delay 미설정 20, Output Delay 미설정 11 | 외부 Interface Timing 검증 미완료 |
| EVIDENCE-PROVENANCE-001 | 원래 DCP 생성 시 Source Commit/Hash 연결 미기록 | 최신 Workspace와 동일 소스라고 이름만으로 추정하지 않음 |
| EVIDENCE-COVERAGE-001 | 새 보고 묶음에 RAM/Verification/단독 Utilization 보고서 및 PE/Protocol 계측 부재 | 전체 자원은 hierarchy로 유도. 없는 자료를 이전 Run에서 몰래 대체하지 않음 |

근거: ../../../artifacts/implementation/optimized_accelerator/run_002/ 의 7개 원본 rpt 및 run_manifest.yaml.
각 상세 경로/행 번호는 review_20260908/findings.yaml에 기록되어 있다.

## 구축 과정 요약

1. artifacts=원본 증거, experiments=분석·승인·수정·재검증, manifests=정책, rag/automation=실행기로 분리했다.
2. 요약 수치 탐지를 상세 Timing 경로·주소·MUX·Fanout·DRC·물리 메모리 매핑·UNKNOWN coverage로 확장했다.
3. `SPEC Requirement ID → 실패 증거 → 승인된 수정 → 재검증`을 기준으로 Source/Testdata/SPEC/Config/Runtime/Report 해시를 연결했다.
4. 승인 전 RTL/SPEC/TB/Memory 변경을 차단하고 승인 후 기존 RTL 파일만 격리 복사본에 패치하도록 했다.
5. ModelSim Compile → Simulation → Vivado Synthesis를 연결했다. 실패/Timeout이면 후속 도구를 생략한다.
6. 결과를 다음 Run으로 자동 분석하고 새 승인을 기다리며, 반복/횟수 제한과 자동 승격 금지를 적용했다.
7. 실제 격리 입력 경로 실패를 발견·수정하고 두 모델 99/1 Golden을 재확인했다. Optimized 합성 어댑터도 종료 코드 0으로 검증했다.
8. 이번 메모리 탐지를 포함해 자동화 테스트 23개가 통과했다. 생성된 이력은 로컬 RAG로 검색하며 외부 LLM/API와 Historical Baseline을 사용하지 않는다.

규칙 기반 탐지로 모든 결함 발견을 보장하지 않는다. 전체 보고서·미분류 경고 검토와 사람의 승인 단계가 필요하다.
패치 생성은 현재 Agent가 담당하며 Python이 외부 LLM을 호출하는 구조가 아니다.
자동화 기반 테스트 통과는 승인된 생산 패치의 회귀검증 통과 또는 DUT Timing Closure와 다르다.

## Power 분석 종료 절차

[POWER_SAIF_GUIDE.md](POWER_SAIF_GUIDE.md)를 따른다. 아직 SAIF 분석은 실행하지 않았다.
활동 파일·매칭률·환경 조건·새 Power Report를 보관하고, 한계를 명시한 비교표까지 작성하면 현재 버전의 PPA 분석을 종료한다.
Timing/Memory/DSP 수정 및 수정 후 Post-Route 검증은 최종 승인 후의 별도 단계다.

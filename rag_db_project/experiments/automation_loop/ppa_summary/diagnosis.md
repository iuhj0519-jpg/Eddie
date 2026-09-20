# 자동화 Loop 탐지 결과 및 PPA 최종 정리

## 승인된 디버깅 결과 안내

이 문서 아래의 표는 디버깅 전 PPA 종료 기록으로 보존한다. 최신 실행은 `../optimized_accelerator/run_004/`이며 검토용 소스와 결과는 `../../../workspace/rag_debug_output_001/README.md`에 있다.
기존 수치 제안은 개발자의 request_002 및 별도 TB 승인으로 spec_001에 반영되었고, request_003의 재시도 승인은 spec_002에 연결되었다. 승인 문서의 원래 스냅샷은 수정하지 않는다.
run_004의 5단계 실행은 완료했으며 DSP 25개, Post-Route LUT 1,199 / FF 714 / WNS +0.120 ns, SAIF 전력 0.169 W와 에너지 273.361725 µJ를 관측했다. 100개 예측과 추론 161,735 Cycle은 원본과 동일하다.
잔여 DRC/외부 I/O 제약, reset Fanout 및 추가 검증은 후속 보완안에서 다룬다. 디버깅 완료와 설계 최종 수락/Project_Git 통합은 구분한다.

동일 조건으로 재실행한 원본과의 비교: LUT 18,094 → 1,199(93.37% 감소), FF 1,536 → 714(53.52% 감소), WNS −4.576 → +0.120 ns, 전력 0.614 → 0.169 W(72.48% 감소), 에너지 993.16035 → 273.361725 µJ. 과거 화면의 0.607 W와 섞지 않는다. [최종 비교·해석 제한](../../../workspace/rag_debug_output_001/reports/diagnosis.md), [다음 미승인 SPEC 보완안](../optimized_accelerator/analysis_006/spec_change_proposal.md)을 확인한다.

## 아래는 디버깅 전 승인 대기 기록

**상태: 사용자 승인 대기. Run is not approved for patch generation.**
이 표는 기존 analysis_003의 자동 진단과 SAIF 수동 보완 증거를 구분해 정리한 것이다. 최신 자동 재분석 완료를 뜻하지 않는다.
[다음 Gate 수치 제안](spec_change_proposal.md)과 [자동 실행 설명](../../../rag/automation/README.md)을 함께 검토한다.

## 최신 탐지 표

| 탐지 범위 / Finding | 관측 결과 | Loop의 판단 및 승인 후 검토 |
|---|---|---|
| PPA-DSP-001 | DSP 5개, Weight 계층 소속 | 25 PE의 DSP MAC 매핑 입증 안 됨. PE 20% 활용이라는 의미 아님 |
| PPA-WEIGHT-001 | Weight LUT 13,955 / 전체 18,060 = 약 77.27% | 자원 집중. 저장·주소·선택 구조 함께 검토 |
| PPA-MEMORY-MAPPING-001 | Weight BRAM/LUTRAM 0 | 모듈명이 SRAM인 것과 물리 RAM 구현은 다름. Weight BRAM 명세는 승인 필요 |
| PPA-TIMING-001 | WNS -5.362 ns, TNS -252.171 ns, 실패 104개 | 100 MHz Setup 미충족. Hold/Pulse는 보고된 범위에서 통과 |
| PPA-ADDRESS-001 | controller cycle_count → Weight read 주소 경로 | 원인 가설. 주소 폭·산술·bank decode 검증 |
| PPA-MUX-001 / PPA-PIPELINE-001 | MUX 포함 깊은 논리 경로 | 메모리 구조와 pipeline/valid 정렬 개선 검토 |
| PPA-ROUTE-DELAY-001 / PPA-FANOUT-001 | 최악 경로 15.216 ns 중 배선 9.710 ns, fanout 2,415 사례 | 배치·부하 분산 검토. fanout 수만으로 모든 실패 원인 확정 불가 |
| IMPL-DRC-001 / DRC-* | critical warning 집계 4; NSTD-1, UCIO-1 및 DSP/reset 관련 규칙 | 실제 보드·인터페이스 계약을 바탕으로 수정. 경고 억제 금지 |
| PPA-CONSTRAINT-001 | 입력 delay 누락 20, 출력 delay 누락 11 | 외부 timing coverage 부족. 조건을 임의 생성하지 않음 |
| PPA-POWER-001 | 기존 Low → SAIF 후 Medium | 활동 근거 개선. 직접 annotation은 여전히 낮으므로 실측으로 표현하지 않음 |
| REGRESSION-TOTAL-ON-CHIP-POWER-W | 0.544 → 0.607 W, 11.58% 증가 | 전력 회귀. 에너지 약 1.77% 추정 감소로 자동 승인하지 않음 |
| EVIDENCE-PROVENANCE-001 / EVIDENCE-COVERAGE-001 | 과거 source 해시 연결·일부 보고서/계측 UNKNOWN | 새 자동 실행에서 같은 소스의 전 단계를 연결. 과거 자료를 새 PASS로 변조하지 않음 |

## PPA 종료 수치

| 지표 | Systolic | Optimized | 해석 |
|---|---:|---:|---|
| 테스트 완료 시간 | 1,837,345 ns | 1,617,525 ns | 11.96% 감소; 정확한 동일 inference-cycle 계측 비교와 구분 |
| 정확도 | 99% | 99% | 샘플별 정합성도 별도 검증 |
| 버퍼 LUT | 143 | 60 | 58.04% 감소 |
| 버퍼 FF / BRAM Tile | 64 / 2.5 | 75 / 2.5 | FF 증가, BRAM 동일 |
| 전체 LUT / FF | 18,029 / 1,433 | 18,060 / 1,455 | 전체 면적 감소로 표현하지 않음 |
| 평균 전력(SAIF) | 0.544 W | 0.607 W | 11.58% 증가 |
| 수집 구간 에너지 추정 | 999.515680 µJ | 981.837675 µJ | 약 1.77% 감소, 유의미한 실측 개선 확정 아님 |
| SAIF 직접 매칭 | 475 / 31,953 | 401 / 32,073 | 약 1.49% / 1.25%, 모두 Medium |

SAIF TIMESCALE=1 ps, DURATION=1,837,345,000 및 1,617,525,000이므로 각각 위 ns 값이다.
1,837,345 ns = 1.837345 ms = 0.001837345 s. 쉼표는 천 단위 구분이다.
E[J]=P[W]×t[ns]×10^-9, E[µJ]=P[W]×t[ns]/1,000.
Systolic: 0.544×1,837,345/1,000=999.515680 µJ.
Optimized: 0.607×1,617,525/1,000=981.837675 µJ.
기능 시뮬레이션/추정 전력의 곱이며 실제 보드 소비 에너지가 아니다. 목표 Timing도 미충족이다.

## Gate 모니터링 위치

| 내용 | 위치 |
|---|---|
| 현재 수치 목표 제안 | 이 폴더/spec_change_proposal.md (미승인, 정책 미반영) |
| 정확한 기존 Finding | ../optimized_accelerator/analysis_003/findings.yaml |
| 요구사항·한국어 보완 표 | 같은 analysis_003/requirements.yaml, spec_change_proposal.md |
| 항목별 승인·Gate 상태 | 같은 analysis_003/approval.yaml, gate_status.json |
| 소스·도구·증거 연결 | 같은 analysis_003/run_manifest.yaml |
| 비교·충족·누락 | 같은 analysis_003/optimization_assessment.json, requirements_result.json, coverage.json |
| 최종 SAIF 원본 보고서 | 이 폴더/systolic_power_saif.rpt, optimized_power_saif.rpt |
| SAIF 해시·시간 | 이 폴더/saif_evidence.json |
| 자동화 검증 | ../system_validation_002/diagnosis.md |

승인 전에 최신 증거 재분석 및 바인딩이 필요하다. PPA 분석 종료는 디버깅 실행 허가나 설계 최종 수락이 아니다.
출처 기록과 이전 Run은 보존한다. 중복 설명 문서는 이 파일과 rag/automation/README.md로 통합했다.

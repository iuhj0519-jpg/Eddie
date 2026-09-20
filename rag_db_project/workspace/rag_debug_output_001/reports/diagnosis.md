# 승인된 디버깅 결과 — 최종 수락 대기

외부 LLM API 없이 저장소 SPEC·RAG 근거로 수정했다. 승인된 재시도 run_004에서 Compile → Simulation/SAIF → Synthesis → Implementation → SAIF Power가 모두 종료 코드 0으로 완료됐다. 원본과 데이터·기준 SPEC은 변경하지 않았다.

## 동일 조건 재측정 비교

변경 전은 이번에 재실행한 `workspace/optimized_accelerator`이다. `systolic_prototype`이나 출처 미연결 과거 스크린샷과 섞지 않는다. 같은 Vivado 2022.1, xc7z020clg400-1, 10 ns, 동일 MNIST 100개, 같은 자동화 어댑터의 Behavioral SAIF 전체 구간 조건이다. 원본 증거는 `artifacts/{verification,synthesis,implementation}/optimized_accelerator/baseline_001`, 후보는 같은 target의 `run_004`다.

| 항목 | 변경 전 원본 | 디버깅 후보 | 변화 |
|---|---:|---:|---|
| 전체 LUT | 18,094 | 1,199 | 93.37% 감소 |
| FF | 1,536 | 714 | 53.52% 감소 |
| DSP | 5 | 25 | 400.00% 증가 |
| BRAM Tile | 2.5 | 12.5 | 400.00% 증가 |
| WNS (ns) | -4.576 | 0.12 | +4.696 |
| TNS (ns) | -208.111 | 0 | +208.111 |
| 추론 Cycle | 161,735 | 161,735 | 동일 |
| SAIF 전력 (W) | 0.614 | 0.169 | 72.48% 감소 |
| 구간 에너지 (µJ) | 993.16035 | 273.361725 | 72.48% 감소 |

두 실행의 수집 시간은 1,617,525 ns이며 100개 예측이 전부 같다. MNIST Accuracy는 양쪽 99%다. Cycle 개선을 새로 주장하지 않는다. BRAM 증가는 LUT/MUX 기반 Weight를 물리 메모리로 옮긴 의도된 자원 교환이며, 전체 BRAM 사용량 감소는 아니다.

Behavioral simulation의 10 ns Cycle 수와 실제 하드웨어에서의 100 MHz 동작 가능성은 다르다. 원본의 Timing 위반을 무시한 실측 처리량 개선으로 해석하지 않는다. 후보도 내부 제약 경로 통과와 미지정 외부 I/O 경로를 구분한다.

에너지 식: E[J] = P[W] × t[s], E[µJ] = P[W] × t[ns] / 1,000. 후보는 0.169 × 1,617,525 / 1,000 = 273.361725 µJ이다. 전력과 에너지는 SAIF 기반 추정치이며 실측값이 아니다. Confidence Medium과 직접 annotation 부족을 함께 보고한다. 구조 변화로 매칭률이 달라질 수 있어 비율을 완전한 물리 실측 개선율로 해석하지 않는다.

## 적용과 검증

| 승인 범위 | 적용 및 근거 |
|---|---|
| 25-PE DSP MAC | 각 PE에 DSP 1개, 총 25개. 동시 활성 PE 25, MAC shadow 누산 검증 |
| Weight BRAM / 큰 선택 회로 | 5-bank 동기 ROM, Weight LUT 0 / RAMB36 10. 24,320 byte 전체 원본 MIF 대조 |
| 주소 산술 | bank 주소 padding/간단한 조합 및 임시 index 10-bit화. 5-lane·1-cycle 정합 보존 |
| 유휴 토글 | invalid operand data register 유지. valid 및 797/43/33 Cycle 계약 보존 |
| TB | 승인된 계측 추가. Accuracy·MNIST·Golden·timeout 기준 미변경. AXIS stall/AXI read 안정성 범위 protocol error 0 |

## 자동 판정과 다음 Gate

16개 자동 수치/기능 검사 PASS, 실패 0이다. 30개 사람 검토 조건은 UNKNOWN을 유지하므로 요구사항 전체의 최종 PASS/수락을 의미하지 않는다.

Finding 개수는 독립적인 결함 개수가 아니다. 해결된 DSP/Weight 수치에도 최종 증거 검토 조건이 남아 `SPEC-CHECK-*`로 표시될 수 있으며, 이것을 DSP/Weight 실패가 재발했다는 의미로 해석하지 않는다.

| 잔여 범위 | 다음 검토 |
|---|---|
| 외부 I/O 계약 | NSTD-1/UCIO-1, 입력 delay 20 / 출력 delay 11개 미지정. 보드/PS 담당자의 실제 pin·IOSTANDARD·외부 지연 계약 필요 |
| reset / pipeline | DSP accumulator reset을 동기로 변경했다. reset이 유효 클록 에지까지 유지되는 통합 조건과 짧은 reset pulse 경계는 별도 검토한다. reset Fanout 561 및 DSP/BRAM pipeline·async-control 경고도 남아 있다. |
| 검증 범위 | 모든 무작위 stall/reset 경계를 검증한 것은 아님. 이번 계측 통과와 전체 protocol 증명을 구분 |
| 전력 증거 | 후보 직접 annotation 352/3,408 net. 필요시 post-implementation SAIF 교차 검증 |

승인 SPEC `experiments/automation_loop/optimized_accelerator/spec_versions/spec_002/SPEC.md`는 보존한다. 새 결과와 미승인 후속 보완안은 같은 target의 `analysis_006/{diagnosis.md,requirements.yaml,spec_change_proposal.md}`이며 이 폴더의 reports에도 복사했다. 추가 RTL 실행과 최종 수락은 개발자 재승인 대상이다. Project_Git 통합은 하지 않았다.

## 추적성과 실패 기록

첫 계측 패치의 중복 선언은 Agent 오류이며 run_003 Compile 실패로 보존했다. 사용자 재승인 request_003 후 run_004에서 수정·검증했다. baseline 원본 로그는 생성 당시 run_004/reference 경로를 포함하지만 최종 보관은 baseline_001로 분리했으며 원본 바이트는 유지했다. 후보 source_manifest와 staged Git 소스 해시를 대조한다. 원본 증거와 실행 소스 스냅샷에는 줄바꿈 자동변환 제외 규칙을 적용했다.

격리 작업 폴더 `.automation_debug`는 Git에 포함하지 않는다. 실행 당시 경로는 기록용이며 재현 시 `rag_debug_output_001` 소스와 기록된 어댑터/입력을 사용한다. 이 결과를 덮어쓰지 않고 다음 별도 승인 최적화는 rag_debug_output_002에 둔다.

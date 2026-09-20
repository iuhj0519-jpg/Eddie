# rag_debug_output_001 — 검증 실행 완료 / 최종 수락 대기

이 폴더에는 승인된 최적화 후보의 실제 실행 소스가 들어 있다. 원본 `workspace/optimized_accelerator`는 변경하지 않았다. `Project_Git` 통합 및 최종 수락은 수행하지 않았다.

## 실행과 승인 연결

- 승인 요청: `../../experiments/automation_loop/optimized_accelerator/requests/request_002/request.md`
- TB 수정 재승인: 같은 target의 `requests/request_003/request.md`
- 승인 SPEC: 같은 target의 `spec_versions/spec_002/SPEC.md` (spec_001의 수치·기능 조건 유지)
- 실행: 같은 target의 `run_004/revalidation_result.json`
- 출력 파일 해시·원본 보존 확인: `reports/source_manifest.yaml`
- 샘플별 원본 대조: `reports/golden_comparison.json`
- 구체적인 변경 근거: `reports/design_evidence.md`
- 후속 SPEC 보완안: `reports/spec_change_proposal.md` (추가 실행은 재승인 필요)

## 검증 결과

| 항목 | 결과 |
|---|---|
| Compile / Simulation / Synthesis / Implementation / SAIF Power | 모두 종료 코드 0 |
| MNIST | 100개 중 99 PASS / 1 FAIL, Accuracy 99% |
| 원본 대비 샘플별 예측 | 100개 모두 동일 |
| 추론 Cycle | 161,735, 원본과 동일 |
| 동시 활성 PE | 25 |
| DSP | 25, 각 PE 계층에 1개 |
| 전체 Weight 내용 | 24,320 byte 모두 원본 MIF와 일치 |
| Weight 구현 | LUT 0, RAMB36 10개 |
| Post-Route 전체 자원 | LUT 1,199 / FF 714 / BRAM Tile 12.5 |
| Post-Route Timing | 10 ns, WNS +0.120 ns / TNS 0 / WHS +0.027 ns / WPWS +4.500 ns |
| SAIF 전력 추정 | Total 0.169 W, Dynamic 0.063 W, Static 0.106 W, Confidence Medium |
| 수집 구간 에너지 추정 | 0.169 × 1,617,525 / 1,000 = 273.361725 µJ |

## 미결과 해석 제한

- 보드 pin/IOSTANDARD 및 외부 I/O delay 미정: NSTD-1/UCIO-1 등의 DRC와 timing coverage 미결. 임의 제약이나 경고 억제를 추가하지 않았다.
- 최대 Fanout 561(reset 경로), DSP/BRAM pipeline 및 async-control 경고가 남는다. Timing 숫자 통과가 모든 경고 해소를 의미하지 않는다.
- 직접 SAIF annotation은 352/3,408 net(약 10.33%)이다. 나머지는 확률적 추정이며 실제 보드 전력/에너지 측정값이 아니다.
- Protocol error 0은 이번 TB의 AXIS stall 안정성·AXI read response 안정성 및 관련 계측 범위다. 모든 AXI 동작·무작위 stall·모든 reset scenario의 완전 검증을 의미하지 않는다.
- 원본의 정상 TB를 누락으로 잘못 판단하여 첫 계측 패치가 중복 선언을 만들었다. `run_003` Compile 실패는 Agent 오류이며 재승인 후 수정했다. 실패 기록은 보존한다.

## 폴더

`rtl`, `tb`, `memory`, `scripts`는 실행한 격리 소스와 해시가 일치한다. `reports`는 분석·출처 연결 문서다. 실제 도구 원본은 `../../artifacts/{verification,synthesis,implementation}/optimized_accelerator/run_004/`에 보관한다.

다음 별도 최적화 반복 결과는 개발자 재승인 후 `rag_debug_output_002`에 보관하며 이 후보를 덮어쓰지 않는다.

## 최종 동일 조건 비교

[수치 비교·잔여 Gate 정리](reports/diagnosis.md), [기계 판독 비교](reports/paired_comparison.json). 최신 후속 분석은 `../../experiments/automation_loop/optimized_accelerator/analysis_006/`이다.

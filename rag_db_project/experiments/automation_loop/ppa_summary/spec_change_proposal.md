# 다음 Gate 최적화 범위 제안 — 미승인 / 정책 미반영

이 문서는 개발자가 한 번에 검토할 제안이다. 아래 수치로 requirements.yaml, 승인 SPEC, 임계값 또는 RTL을 변경하지 않았다.

## 우선순위와 목표

| 순서 | 범위 | 현재 근거 | 제안 합격 기준 | 수정 방향과 주의점 |
|---|---|---|---|---|
| 1 | PE DSP MAC | DSP 총 5개, Weight 계층 소속. PE 매핑 입증 없음 | **25개 PE 각각 DSP48 MAC 1개**; PE 계층 합계 25개. 주소 연산 DSP 제거를 통해 총 25개를 목표 | signed 폭·곱셈/누산 패턴·파이프라인 검토. 총개수만 맞추는 불필요한 DSP 삽입 금지. 25 PE 동시 유효 연산 계측 |
| 2 | Weight SRAM | LUT 13,955, BRAM/LUTRAM 0 | Weight 저장 데이터 전체의 물리 BRAM 매핑 및 5-bank 공급 검증 | 동기 RAM 추론, 주소 분리, 읽기 valid 지연 정렬. BRAM 1개 존재만으로 성공 판정 금지 |
| 3 | Timing | 100 MHz, WNS -5.362 ns, 실패 Endpoint 104 | 10 ns에서 WNS/TNS≥0, WHS/WPWS≥0, 실패 Endpoint 0 | 주소/MUX/배선/Fanout 개선과 필요한 pipeline. 단순 clock 완화 금지 |
| 4 | LUT·FF | 전체 LUT 18,060, FF 1,455 | 전체 LUT **≤12,642(30% 감소 목표)**, FF **≤2,000(파이프라인 여유 상한)** | 전체 감소와 버퍼 감소 구분. FF 증가는 Timing/DSP 개선과 함께 검토 |
| 5 | 처리 성능 | total_inference_cycles=161,735, 수집시간 1,617,525 ns | 같은 계측 기준 cycles **≤161,735**, 동일 100개 입력·결과 유지 | AXI 입력/Compute overlap 보존. cycle과 전체 테스트 시간 혼동 금지 |
| 6 | 평균 전력 | 최적화 0.607 W, Systolic 0.544 W | 최종 목표 **≤0.544 W** (현재 대비 약 10.38% 감소) | 같은 source·workload·clock·SAIF 조건. 추정치 한계 명시 |
| 7 | 작업당 에너지 | 981.84 µJ 추정 | 동일 100개 작업 **≤900 µJ** (약 8.33% 감소 목표) | 단위 E[µJ]=P[W]×t[ns]/1,000. 작은 차이를 실측 개선으로 표현하지 않음 |
| 필수 | 기능·증거 | 정확도 99%, 일부 계측 UNKNOWN | 기존 샘플별 출력·정답 기준 보존, protocol error 0, 배치 interrupt 정상, 같은 source의 전 단계 출처 | 계측용 TB/probe 추가 범위는 승인에 포함하되 Golden/Timeout 완화 금지 |

권장 절충안은 **DSP 25-PE 매핑 최우선 + 균형형(balanced) PPA**다. 이는 보장되는 결과가 아닌 제안 목표다.
총 DSP가 25개를 초과하면 PE 25개와 부가 DSP를 분리 보고하고 재검토한다. DSP 수를 맞추기 위해 잘못된 연산이나 더미 자원을 만들지 않는다.
전력 목표를 만족하지 못해도 다음 반복 제안은 가능하지만, Agent가 기준을 완화하거나 성공 처리하지 않는다.
기능적 SRAM과 물리 FPGA RAM 요구를 구분한다. Bias는 Weight와 동일 규모의 병목으로 단정하지 않는다.

## 승인에 포함할 범위

PE/MAC, Weight 메모리, 주소/MUX, pipeline/valid 정렬, Fanout 및 관련 제어를 하나의 최적화 범위로 제안한다.
모델 가중치·입력 데이터·정답 기준 변경, clock 하향, 경고 억제, bitstream/보드 프로그램은 제외한다.
실제 보드 pin/IOSTANDARD/input-output delay를 모르면 Agent가 임의 작성하지 않는다. 다음 Gate에 보드/인터페이스 조건을 함께 제공하거나 미결로 명시해야 한다.
계측용 TB 수정과 constraints 변경은 현재 RTL-only 패치 권한 밖이므로 별도 명시적 승인과 안전 검증 확장이 필요하다.

## 현재 상태

승인되지 않았다. power_tradeoff는 여전히 null이며 기존 실행 조건을 바꾸지 않았다.
다음 명령에서 개발자가 이 범위와 수치를 승인하면, 먼저 최신 증거를 연결한 SPEC 초안과 실행 바인딩을 확정한다.
조건 일부를 바꾸고 싶으면 그 부분만 지정할 수 있다. 현재 문서 게시가 승인이나 run_003 생성은 아니다.

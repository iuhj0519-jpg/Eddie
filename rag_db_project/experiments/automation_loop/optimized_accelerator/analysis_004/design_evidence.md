# 승인된 첫 번째 디버깅 설계 근거

설계 근거는 Git의 SYS-SPEC-001 §§7~9/14, OPT-SPEC-001 §§7/9/10 및 ppa_summary/spec_change_proposal.md다. 대화는 승인 권한 기록에만 사용하며 외부 API/웹/과거 비교용 구현을 설계 근거로 사용하지 않는다.

| 변경 | 근거·선택 | 유지 계약 |
|---|---|---|
| Weight 5-bank 동기 ROM | 공유 배열의 5-read MUX 대신 열별 독립 bank. 후보 A: 조밀한 4,864 byte/bank 주소 곱셈. 후보 B: 6,336 byte/bank padding과 concat/작은 가산. B를 선택하여 기존 주소 산술 병목 제거; 물리 BRAM 비용은 합성에서 확인 | 원본 60개 MIF, 전체 24,320 byte, 각 column의 group*5+column neuron 순서, 1-cycle read |
| 실제 DSP MAC | mac_pe의 signed 곱셈/26-bit 누산에 DSP 추론 지정 및 동기 accumulator reset | PE 25개, clear/enable 우선순위, Q-format, 누산 width, 추가 pipeline Cycle 없음 |
| operand 유휴 토글 | invalid input일 때 operand data register 갱신 정지; valid 전달은 기존대로 | 유효 operand의 이동 및 MAC enable 동일 |
| 주소 폭 | 32-bit 임시 reduction index를 실제 10-bit로 제한 | 기존 RUN/K-range/row-column skew 조건 유지 |
| TB 복구·계측 | 누락된 선언·DUT 시작 복구. 25개 MAC shadow 누산, 전체 Weight 내용, 797/43/33 Cycle, AXIS/AXI read stall, intr pulse 검사 | 100개 MNIST, 99 PASS/1 FAIL, 기대 label, 10 ns clock, 10 ms timeout 보존 |

Weight 논리 주소: L1=group*1024+feature, L2=6144+group*32+feature, L3=6272+group*32+feature. Group 범위 6/4/2와 feature 범위 784/30/20을 유지한다. Padding은 새로운 가중치가 아니며 읽히지 않는다.

Unified Buffer의 기존 용량/ownership/prefetch 구조와 1-cycle 동기 읽기는 변경하지 않는다. Bias 소용량 저장을 Weight와 같은 대형 병목으로 간주하지 않는다.

보드 pin/IOSTANDARD/I/O delay는 근거가 없어 임의 생성하지 않는다. 남은 DRC/coverage/Timing 또는 승인 목표 미충족은 다음 보완안에 기록하고 최종 승인으로 위장하지 않는다.

# Weight 저장 구조의 물리 구현 합격 기준 보완안

- 상태: proposed_pending_final_approval
- 기존 승인 OPT-SPEC-001 v0.2 및 RTL은 변경하지 않았다.
- 기존 근거: Systolic SPEC §8, REQ-SYS-009는 Weight/Bias 5-bank SRAM을 요구한다.
- OPT SPEC §10.1, REQ-OPT-014는 특히 Unified Buffer의 BRAM-Friendly 구조를 요구한다.
- 기존 문구는 Weight SRAM의 FPGA BRAM primitive 사용을 독립적인 필수 합격 기준으로 명시하지 않았다.

## 제안 Requirement

REQ-OPT-MEM-026: FPGA 대상에서 Weight 저장 데이터는 Block RAM으로 추론/매핑되는 5-lane 공급 가능한
bank 구조로 구현해야 한다. 읽기 전용 초기화 Weight는 BRAM 기반 ROM 구현을 허용한다.
`weight_sram`이라는 모듈 이름이나 출력 Register만으로 합격으로 판정하지 않는다.

## 합격 증거

1. 계층별 보고서에서 Weight storage에 RAMB18/RAMB36이 사용됨을 확인한다.
2. RAM report/Netlist에서 실제 Weight 데이터와 bank/주소가 해당 Primitive에 연결됨을 확인한다.
3. 5개 column의 동시 공급, 저장 용량, 주소 범위, 초기값의 동일성을 검증한다.
4. LUT/MUX는 주소·제어 등 필요한 부분에 허용하되 Weight 본체가 대규모 논리 선택망으로 대체되지 않아야 한다.
5. Read latency 또는 pipeline 변경 시 Valid·주소·Scheduler·group cycle을 함께 재검증한다.
   REQ-SYS-016/017에 영향을 주면 별도 SPEC 변경 승인을 선행한다.
6. Primitive 하나를 추가하는 것만으로 통과하지 않는다. 데이터 저장·공급 경로 전체의 증거가 필요하다.

PPA-MEMORY-MAPPING-001은 BRAM=0을 자동 탐지하는 1차 Gate이며, 위 전체 합격 판정의 대체물이 아니다.
이 요구사항은 사용자 요청을 명문화한 승인 대기 보완안이다. 기존 승인 SPEC을 몰래 변경하거나 RTL을 수정하지 않는다.

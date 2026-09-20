# SPEC 보완안 — 사용자 승인 대기

**미승인입니다. 기존 SPEC·RTL을 변경하거나 실행하도록 허가한 문서가 아닙니다.**

원본 증거와 기계 판정 조건은 같은 폴더의 `requirements.yaml`에 보존합니다.
초안 해시: `f458a87bdd69274c92f961a57226b293d5073db4dfa931d1e2689904bee4dd58`

| 탐지 ID | 구체적인 수정/검증 방향 | 상태 |
|---|---|---|
| REGRESSION-TOTAL-ON-CHIP-POWER-W | 평균 전력 회귀: 개발자가 전력/에너지 우선순위와 두 상한을 결정. 자동 면제 금지. | 승인 대기 |
| PPA-DSP-001 | 25개 PE 각각의 DSP MAC 매핑과 병렬 동작 검증. 총 DSP 개수만으로 성공 판정하지 않음. | 승인 대기 |
| PPA-WEIGHT-001 | Weight 자원 집중 완화: 메모리 접근과 큰 선택 회로를 줄이며 5-lane 공급 보존. | 승인 대기 |
| PPA-TIMING-001 | 목표 클록을 유지하고 Post-Route Setup/Hold/Pulse 조건 충족. | 승인 대기 |
| PPA-POWER-001 | 같은 입력의 SAIF 매칭률과 환경 확인. 전력 추정치를 실측으로 표현하지 않음. | 승인 대기 |
| IMPL-DRC-001 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| PPA-MEMORY-MAPPING-001 | Weight를 물리 BRAM으로 매핑. 뱅크·용량·초기화·동기 읽기 정합성 검증. | 승인 대기 |
| PPA-ADDRESS-001 | 주소 폭·산술·decode와 메모리 읽기 지연을 함께 검토. | 승인 대기 |
| PPA-MUX-001 | 임계 경로 선택 회로 깊이 축소 및 RAM 추론 확인. | 승인 대기 |
| PPA-PIPELINE-001 | 연산 단계 분할 및 데이터·valid·스케줄러 지연 정렬. | 승인 대기 |
| PPA-ROUTE-DELAY-001 | 배치·부하 분산으로 배선 지연 개선, 추가 자원 비용 비교. | 승인 대기 |
| PPA-FANOUT-001 | 고부하 주소·제어 신호 분산/복제 검토. 원인 가설을 추가 검증. | 승인 대기 |
| DRC-NSTD-1 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-UCIO-1 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-CHECK-3 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-DPIP-1 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-DPOP-1 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-DPOP-2 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-RBOR-1 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-REQP-1840 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| DRC-ZPS7-1 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | 승인 대기 |
| PPA-CONSTRAINT-001 | 실제 외부 인터페이스 지연 조건 확정. 임의 핀/제약으로 경고 숨김 금지. | 승인 대기 |
| EVIDENCE-PROVENANCE-001 | 같은 소스·입력·도구의 해시 연결. 과거 출처 추측 금지. | 승인 대기 |
| EVIDENCE-COVERAGE-001 | 누락 보고서·계측 수집. UNKNOWN을 PASS로 처리하지 않음. | 승인 대기 |

## 승인 시 확인할 조건

정답 기준을 완화하지 않습니다. 현재 수치 목표 제안은 `../../ppa_summary/spec_change_proposal.md`에 있으며 아직 실행 정책에 반영하지 않습니다.

### REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W

- 연결 탐지: REGRESSION-TOTAL-ON-CHIP-POWER-W
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-REGRESSION-TOTAL-ON-CHIP-POWER-W", "op": "eq", "value": true}]`

- 전력/에너지 개발자 선택(미정 값은 null): `{"priority": null, "max_average_power_w": null, "max_energy_per_workload_uj": null, "rationale": null}`

### REQ-LOOP-PPA-DSP-001

- 연결 탐지: PPA-DSP-001
- 정확한 판정 조건: `[{"metric": "utilization.dsp", "op": "ge", "value": 25}, {"metric": "verification.peak_active_pe_count", "op": "ge", "value": 25}, {"metric": "review.REQ-LOOP-PPA-DSP-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-WEIGHT-001

- 연결 탐지: PPA-WEIGHT-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-WEIGHT-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-TIMING-001

- 연결 탐지: PPA-TIMING-001
- 정확한 판정 조건: `[{"metric": "timing.wns_ns", "op": "ge", "value": 0}, {"metric": "timing.tns_ns", "op": "ge", "value": 0}, {"metric": "review.REQ-LOOP-PPA-TIMING-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-POWER-001

- 연결 탐지: PPA-POWER-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-POWER-001", "op": "eq", "value": true}]`

### REQ-LOOP-IMPL-DRC-001

- 연결 탐지: IMPL-DRC-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-IMPL-DRC-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-MEMORY-MAPPING-001

- 연결 탐지: PPA-MEMORY-MAPPING-001
- 정확한 판정 조건: `[{"metric": "ram.weight_block_count", "op": "gt", "value": 0}, {"metric": "review.REQ-LOOP-PPA-MEMORY-MAPPING-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-ADDRESS-001

- 연결 탐지: PPA-ADDRESS-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-ADDRESS-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-MUX-001

- 연결 탐지: PPA-MUX-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-MUX-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-PIPELINE-001

- 연결 탐지: PPA-PIPELINE-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-PIPELINE-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-ROUTE-DELAY-001

- 연결 탐지: PPA-ROUTE-DELAY-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-ROUTE-DELAY-001", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-FANOUT-001

- 연결 탐지: PPA-FANOUT-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-FANOUT-001", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-NSTD-1

- 연결 탐지: DRC-NSTD-1
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-NSTD-1", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-UCIO-1

- 연결 탐지: DRC-UCIO-1
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-UCIO-1", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-CHECK-3

- 연결 탐지: DRC-CHECK-3
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-CHECK-3", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-DPIP-1

- 연결 탐지: DRC-DPIP-1
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-DPIP-1", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-DPOP-1

- 연결 탐지: DRC-DPOP-1
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-DPOP-1", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-DPOP-2

- 연결 탐지: DRC-DPOP-2
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-DPOP-2", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-RBOR-1

- 연결 탐지: DRC-RBOR-1
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-RBOR-1", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-REQP-1840

- 연결 탐지: DRC-REQP-1840
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-REQP-1840", "op": "eq", "value": true}]`

### REQ-LOOP-DRC-ZPS7-1

- 연결 탐지: DRC-ZPS7-1
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-DRC-ZPS7-1", "op": "eq", "value": true}]`

### REQ-LOOP-PPA-CONSTRAINT-001

- 연결 탐지: PPA-CONSTRAINT-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-PPA-CONSTRAINT-001", "op": "eq", "value": true}]`

### REQ-LOOP-EVIDENCE-PROVENANCE-001

- 연결 탐지: EVIDENCE-PROVENANCE-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-EVIDENCE-PROVENANCE-001", "op": "eq", "value": true}]`

### REQ-LOOP-EVIDENCE-COVERAGE-001

- 연결 탐지: EVIDENCE-COVERAGE-001
- 정확한 판정 조건: `[{"metric": "review.REQ-LOOP-EVIDENCE-COVERAGE-001", "op": "eq", "value": true}]`

# optimized_accelerator analysis_004 탐지 결과

원본 증거에서 자동 생성한 검토 표입니다. 관측과 원인 가설을 구분하며 승인 전 수정하지 않습니다.

| 탐지 ID | 심각도 | 검토/수정 방향 | 근거 파일 |
|---|---|---|---|
| PPA-DSP-001 | 높음 | 25개 PE 각각의 DSP MAC 매핑과 병렬 동작 검증. 총 DSP 개수만으로 성공 판정하지 않음. | utilization_hierarchical.rpt |
| PPA-WEIGHT-001 | 높음 | Weight 자원 집중 완화: 메모리 접근과 큰 선택 회로를 줄이며 5-lane 공급 보존. | utilization_hierarchical.rpt |
| PPA-TIMING-001 | 심각 | 목표 클록을 유지하고 Post-Route Setup/Hold/Pulse 조건 충족. | timing_summary.rpt |
| PPA-POWER-001 | 중간 | 같은 입력의 SAIF 매칭률과 환경 확인. 전력 추정치를 실측으로 표현하지 않음. | power.rpt |
| IMPL-DRC-001 | 심각 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| PPA-MEMORY-MAPPING-001 | 높음 | Weight를 물리 BRAM으로 매핑. 뱅크·용량·초기화·동기 읽기 정합성 검증. | utilization_hierarchical.rpt |
| PPA-ADDRESS-001 | 높음 | 주소 폭·산술·decode와 메모리 읽기 지연을 함께 검토. | findings.yaml 참조 |
| PPA-MUX-001 | 높음 | 임계 경로 선택 회로 깊이 축소 및 RAM 추론 확인. | findings.yaml 참조 |
| PPA-PIPELINE-001 | 높음 | 연산 단계 분할 및 데이터·valid·스케줄러 지연 정렬. | findings.yaml 참조 |
| PPA-ROUTE-DELAY-001 | 높음 | 배치·부하 분산으로 배선 지연 개선, 추가 자원 비용 비교. | findings.yaml 참조 |
| PPA-FANOUT-001 | 높음 | 고부하 주소·제어 신호 분산/복제 검토. 원인 가설을 추가 검증. | findings.yaml 참조 |
| DRC-NSTD-1 | 심각 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-UCIO-1 | 심각 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-CHECK-3 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-DPIP-1 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-DPOP-1 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-DPOP-2 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-RBOR-1 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-REQP-1840 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| DRC-ZPS7-1 | 중간 | DRC 원본 규칙과 보드·클록·reset 계약을 검토하고 수정 범위 승인. | drc.rpt |
| PPA-CONSTRAINT-001 | 높음 | 실제 외부 인터페이스 지연 조건 확정. 임의 핀/제약으로 경고 숨김 금지. | findings.yaml 참조 |
| EVIDENCE-PROVENANCE-001 | 중간 | 같은 소스·입력·도구의 해시 연결. 과거 출처 추측 금지. | run_manifest.yaml |
| EVIDENCE-COVERAGE-001 | 중간 | 누락 보고서·계측 수집. UNKNOWN을 PASS로 처리하지 않음. | findings.yaml 참조 |

정확한 수치·원본 줄 번호·상태는 같은 폴더의 findings.yaml에 보존합니다.
연결: SPEC 요구 ID → 실패 증거 → 수정 내용 → 재검증 결과. 사용자 승인 대기.

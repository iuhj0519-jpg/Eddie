# Architecture Optimization Specification Set

이 디렉터리는 검증된 Systolic Prototype의 외부 기능을 유지하면서 Buffer 구조와 Batch Scheduling을 최적화하기 위한 규범적 초안을 관리한다.

## Files

| 파일 | 역할 |
|---|---|
| `ARCHITECTURE_OPTIMIZATION_SPECIFICATION.md` | Unified Buffer, AXI Latency Hiding, Scheduler, 용량 산정 및 PPA 요구사항 |

## Current Status

- 문서 상태: `approved`
- RAG Source Manifest 포함 여부: 포함
- Optimization Generation 허용 여부: 활성
- 구현 시작 조건: Approval Gate 전체 통과

Unified Buffer의 고정 Depth나 주소 분할은 지정하지 않는다. Agent는 Data Lifetime, Port Conflict와 목표 FPGA Memory Packing을 근거로 용량과 Mapping을 선택하고, 통합으로 발생할 수 있는 Capacity, Port, MUX, Fmax와 Power 불이익을 후보 비교로 최소화해야 한다.

## Approval Procedure

1. `ARCHITECTURE_OPTIMIZATION_SPECIFICATION.md`의 용량 산정 규칙, AXI Backpressure, Buffer Port 우선순위와 성능식을 검토한다.
2. 미결 항목이 없고 사용자가 내용을 승인하면 문서의 `상태`를 `approved`로 바꾸고 버전을 확정한다.
3. 이 README와 상위 `specifications/README.md`의 상태도 `approved`로 바꾼다.
4. `source_manifest.yaml`에 승인된 Optimization SPEC Markdown을 Source Group으로 추가한다.
5. `phase_access_policy.yaml`의 `optimization_generation`을 활성화하고 다음만 허용한다.
   - 승인된 Reference Model 및 Systolic Controller Reference
   - 승인된 Systolic Accelerator SPEC과 Architecture Optimization SPEC
   - 검증 완료된 `workspace/systolic_prototype/` RTL·TB·Memory 연결 자료
6. `historical_baselines/**`와 `workspace/optimized_accelerator/**`는 계속 차단한다.
7. 승인 Source 전체의 SHA-256 Inventory와 Source Manifest Count를 다시 만든 뒤 Manifest Validation을 통과시킨다.
8. Optimization 전용 Chunking/Ingestion과 Retrieval Smoke Test를 수행한다.
9. Generation Query별 Chunk ID·Source Hash·Requirement Coverage를 고정한 새 Evidence Freeze를 만든다.
10. 새 Git Tag와 격리 Worktree를 만든 뒤에만 `workspace/optimized_accelerator/` 코드 생성을 시작한다.

## Approval Checklist

- [x] Unified Buffer의 Data Lifetime 기반 용량 산정 규칙 승인
- [x] Agent의 Bank Depth·주소식·BRAM Mapping 사전 보고 의무 승인
- [x] 동적 `axis_in_data_ready` Backpressure 승인
- [x] Compute와 다음 Batch Prefetch Overlap 승인
- [x] Activation Write와 Prefetch 충돌 시 우선순위 승인
- [x] Layer 3 결과를 Unified Buffer에 저장하지 않는 경로 승인
- [x] AXI-Lite `0x08`, `intr`, Fixed-Point 계약 유지 승인
- [x] PPA 불이익 최소화와 평가 기준 승인

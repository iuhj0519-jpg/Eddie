# PPA SPEC Change Proposal

Status: `pending_human_approval`

## Proposed REQ-PPA-DSP-001

5×5 Systolic Array는 25개 PE의 동시 유효 MAC 수행 능력을 보존해야 한다. FPGA 합성에서는 각 PE의 곱셈을 DSP48로 Mapping하는 것을 우선 목표로 하며, DSP48 개수와 Simulation 기반 PE Utilization을 함께 검증한다.

## Proposed REQ-PPA-WEIGHT-001

Weight Memory는 LUT와 다단 MUX 사용을 최소화하고 FPGA Block RAM 추론을 우선해야 한다. Memory Read Latency가 추가되면 Controller와 Data Alignment를 조정하되 외부 Interface, 결과 정확도와 승인된 Protocol을 보존해야 한다.

## Approval Effect

승인 시에만 정식 SPEC 버전을 증가시키고 Manifest와 SHA-256을 갱신한 후 RAG Index를 재생성한다. 이후 격리 Worktree에서 RTL을 수정하고 Compile, Simulation, Synthesis와 Regression을 수행한다.

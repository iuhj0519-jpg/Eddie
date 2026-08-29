# Systolic Controller Reference

이 디렉터리는 `zyNet` Reference Model에 이식할 Systolic Controller의 원본 RTL을 보존한다. 이 코드는 외부 사례가 아니라 프로젝트가 직접 제공한 승인 설계 원천이며, Systolic Prototype 생성 시 Reference Model RTL과 함께 근거로 사용한다.

## Integration Intent

프로젝트의 핵심은 새로운 Systolic Controller를 자유롭게 발명하는 것이 아니라, 이 Reference Controller의 계산 구조를 FC-MLP `zyNet`의 AXI, Buffer, SRAM, Fixed-Point Interface에 동기화하여 이식하는 것이다.

보존 대상은 다음과 같다.

- `IDLE`, `RUN`, `DONE_STATE` FSM
- `i_start`, `o_busy`, `o_done` Handshake 의미
- `array_clr = (state == IDLE) && i_start`
- RUN 상태의 Array Enable
- `k = cnt - row_index`, `k = cnt - column_index` Skewing
- 행 방향 A 전달, 열 방향 B 전달
- PE 내부 Output-Stationary Accumulation
- Controller → 2D Array → Systolic Cell → MAC PE 계층

## Files

| File | Role | Integration Status |
|---|---|---|
| `rtl/systolic_controller_ref.sv` | FSM, Input Latch, Skewing, 2D Array 제어 | Normative Core Reference |
| `rtl/systolic_array_2d_ref.sv` | Parameterized 2D Array 연결 | Normative Core Reference |
| `rtl/pe_systolic_cell_ref.sv` | A/B Register 전달과 MAC PE 연결 | Normative Core Reference |
| `rtl/mac_pe_ref.sv` | Multiply/Accumulate와 Clear/Enable | Normative Core Reference |

4개 RTL은 사용자가 제공한 원본을 변형 없이 보존한다. 생성 Agent는 이 원본과 승인 SPEC을 함께 검색하여 `zyNet` 이식에 필요한 Interface와 Fixed-Point 구현을 판단해야 한다. 이 디렉터리의 원본 파일을 직접 수정하거나 생성 결과로 덮어써서는 안 된다.

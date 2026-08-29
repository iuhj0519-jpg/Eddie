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
| `rtl/pe_chain_1d_ref.sv` | 1D PE 전달 구조의 선행 단계 | Supporting Reference; Controller 직접 계층에는 미사용 |

## Required Target Adaptations

Reference RTL의 구조적 동작과 목표 시스템의 Interface가 다른 부분은 Adapter 또는 명시적 Parameter 변경으로 처리한다.

- 원본 unsigned 연산은 목표 Fixed-Point 계약에 맞춰 signed Q1.7×Q4.4로 변경
- `ACC_W`는 Layer별 기본 계산식 대신 26-bit Q15.11로 고정
- Active-Low `rst_n`과 `zyNet` 내부 Reset 극성 동기화
- Compile-Time `K_DIM`을 Layer별 K=784/30/20 동작에 맞게 연결
- 전체 Matrix Latch Interface와 Input Buffer/Global Buffer/Weight SRAM의 1-Cycle Read Interface 동기화
- 원본 `CALC_CYCLES` Counter의 Inclusive 종료 의미를 보존하여 최종 797/43/33 Clock 계약 유지

Adapter는 외부 AXI Protocol이나 Reference Controller의 FSM/Skew 의미를 바꾸기 위한 것이 아니다. 변경된 Port, Latency와 Cycle 계산은 SPEC과 구현 보고서에 추적되어야 한다.

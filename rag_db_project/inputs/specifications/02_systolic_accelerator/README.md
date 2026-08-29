# Systolic Accelerator Specification Set

이 폴더는 legacy FC-MLP의 neuron별 MAC 구조를 대체할 5×5 output-stationary systolic accelerator의 목표 구조와 제어 계약을 정의한다.

이 프로젝트는 Systolic Array를 새로 자유 설계하는 프로젝트가 아니다. `inputs/systolic_controller/rtl/`에 보존된 Systolic Controller Reference 계층을 `zyNet` Reference Model의 AXI, Buffer, SRAM과 Fixed-Point Interface에 동기화하여 이식하는 프로젝트다.

- `SYSTOLIC_ACCELERATOR_SPECIFICATION.md`: array, PE, OS dataflow, controller FSM, memory feed 및 cycle 요구사항

Agent는 이 폴더의 승인된 SPEC과 단계별로 허용된 RAG DB 입력만 사용해 새 prototype을 생성해야 한다.

현재 상태는 `approved`다. 이 폴더의 SPEC은 Systolic Accelerator 생성 단계의 규범적 RAG 입력이다.

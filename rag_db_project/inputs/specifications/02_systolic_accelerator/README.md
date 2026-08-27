# Systolic Accelerator Specification Set

이 폴더는 legacy FC-MLP의 neuron별 MAC 구조를 대체할 5×5 output-stationary systolic accelerator의 목표 구조와 제어 계약을 정의한다.

- `SYSTOLIC_ACCELERATOR_SPECIFICATION.md`: array, PE, OS dataflow, controller FSM, memory feed 및 cycle 요구사항

기존 `systolic_project`의 완성 코드는 생성 입력이 아니라 `historical_baselines`의 비교 근거다. 이 SPEC은 historical 코드를 복사하라는 지시가 아니라, 새 prototype이 만족해야 할 요구사항이다.

# Legacy FC-MLP To Systolic Accelerator RAG Project

## RAG-Only 생성 정책

이 프로젝트는 외부 Web 검색, 외부 자료와 외부 LLM/API를 코드 생성 근거에서 완전히 배제하고, 승인된 RAG DB만으로 설계·구현·검증하는 조건에서 RAG 성능을 최대한 끌어올리는 것을 목표로 한다. 승인 DB에 근거가 없으면 Agent는 외부 지식으로 보완하지 않고 `unknown` 또는 Requirement mismatch로 보고한다.

이 프로젝트는 MNIST handwritten digit inference를 수행하는 legacy FC-MLP RTL에 5×5 output-stationary systolic array 기반의 TPU-style 연산 구조를 적용하고, 그 과정을 RAG 기반 AI Agent로 재현·최적화·검증하는 것을 목표로 한다.

완성된 RTL을 단순히 검색하는 프로젝트가 아니다. 승인된 reference model과 단계별 specification을 근거로 다음 산출물을 순서대로 생성하고 검증한다.

```text
Legacy FC-MLP reference model
        +
Systolic accelerator specification
        ↓
Generated systolic prototype
        +
Architecture optimization specification
        ↓
Generated optimized accelerator
        +
Verification specification
        ↓
Compile, simulation, regression and comparison
```

## 핵심 목표

1. 784→30→20→10 FC-MLP의 기능과 99/1 baseline을 보존한다.
2. neuron별 병렬 MAC 구조를 5×5 systolic array 기반 연산 구조로 대체한다.
3. 요구사항, RTL symbol, test 및 실행 결과를 추적 가능하게 연결한다.
4. full-context, RAG, RAG+Agent 방식의 코드 생성·검증 성능을 같은 조건에서 비교한다.
5. 근거가 부족하거나 입력 문서가 충돌하면 추측하지 않고 `unknown` 또는 mismatch를 보고한다.

## 디렉터리

| 경로 | 역할 |
|---|---|
| `inputs/reference_model/` | legacy FC-MLP RTL, weight/bias, sigmoid LUT, test vector와 재현 스크립트 |
| `inputs/systolic_controller/` | `zyNet`에 이식할 Controller, 2D Array, Systolic Cell과 MAC PE Reference RTL |
| `inputs/specifications/` | 단계별 승인 요구사항과 목표 아키텍처 SPEC |
| `workspace/systolic_prototype/` | reference model과 systolic SPEC으로 새로 생성할 prototype |
| `workspace/optimized_accelerator/` | prototype과 optimization SPEC으로 생성할 최적화 RTL |
| `historical_baselines/` | 기존에 사람이 개발한 비교용 결과; 생성 단계 검색에서 제외 |
| `verification/` | 현재 legacy TB와 향후 계층형 검증 환경 |
| `rag/` | 수집, chunking, hybrid retrieval, Agent 및 평가 구현 |
| `manifests/` | source, 접근 정책, baseline 및 index 버전 |
| `experiments/` | prototype 생성, 최적화, 검증 및 비교 실험 기록 |
| `artifacts/` | 실행 summary와 artifact 위치·hash 기록 |

## 현재 기준

- Reference DUT top: `zyNet`
- Reference network: 784→30→20→10
- Reference testbench: `top_sim.v` 단일 testbench
- Reference baseline: 100 samples, 99 PASS / 1 FAIL, Accuracy 99.000000%
- Systolic target: 5×5 array, output-stationary dataflow
- Systolic controller: `IDLE`, `RUN`, `DONE_STATE`

## 정본과 데이터 누출 방지

- 승인된 specification은 설계 의도의 정본이다.
- 현재 구현 사실은 Git commit으로 식별한 RTL 원문에서 확인한다.
- vector DB는 검색용 파생 데이터이며 정본이 아니다.
- `historical_baselines/`는 평가용 결과이므로 prototype 및 optimization 생성 단계의 RAG 검색에서 제외한다.
- 생성된 결과는 `workspace/`에만 저장한다.
- compile 또는 simulation을 수행하지 않은 코드는 verified로 표시하지 않는다.

## 생성 독립성과 명명 정책

- Reference Model에 이미 선언된 external interface, 변수 및 parameter 이름은 호환성을 위해 그대로 유지한다.
- Reference Model에 존재하는 module의 기능을 계승하면 해당 module 이름을 그대로 유지하고, Input Buffer, Global Buffer, Weight SRAM, Bias SRAM, Activation Unit, DNN Scheduler처럼 새로 추가된 기능 블록에만 새 이름을 사용한다.
- 승인된 SPEC이 이름까지 요구한 signal만 생성 코드의 고정 interface로 사용한다.
- 내부 module, state, register 및 helper signal 이름은 `historical_baselines/`에서 복사하거나 그 이름을 정답처럼 사용하지 않는다.
- Historical Baseline에만 존재하는 구현 세부사항은 SPEC 요구사항으로 승격하지 않는다.
- RAG 생성 결과는 승인된 기능과 interface를 만족하되, Historical Baseline과 독립적으로 설계되어야 한다.
- 비교 실험에서는 기능 정확도와 cycle뿐 아니라 module 분해, RTL 구조 및 코드 유사도도 함께 평가한다.

## 진행 단계

Reference Model, 변경되지 않은 Systolic Controller Reference RTL 4개와 Systolic Accelerator SPEC version 1.1을 포함한 246개 입력 파일은 `rag-input-baseline-v1.1`과 SHA-256 Inventory로 동결한다.

`prototype_generation` 접근 정책에 따라 Markdown과 두 Reference RTL 계층의 23개 원천을 164개 Chunk로 나눠 `prototype_generation_v2` Hybrid Index에 Ingestion했다. SQLite FTS5 BM25와 384차원 deterministic feature-hash Dense Index를 사용하며, Historical Baseline과 Workspace를 포함한 금지 경로 Chunk는 0개다. Systolic Prototype은 변경되지 않은 4개 Controller Reference와 SPEC을 근거로 SRAM Streaming Adapter를 사용해 생성했으며, ModelSim 100-Sample Regression에서 99 PASS/1 FAIL, Accuracy 99.0%를 확인했다.

Architecture Optimization SPEC version 1.0은 승인되었다. Input Buffer와 Global Buffer를 Unified Buffer로 통합하고, 현재 Batch의 Compute와 다음 Batch의 AXI-Stream Prefetch를 겹쳐 첫 Batch 이외의 입력 Latency를 숨기는 계약을 정의한다.

기존 Manifest 계층을 유지하면서 승인 Source와 단계별 Access Policy를 확장한다. Optimization Generation은 검증된 `run_002` Systolic Prototype과 승인 SPEC만 사용하며 외부 Web, 외부 LLM/API와 Historical Baseline은 차단한다.

## Prototype Generation Run 역할

`experiments/prototype_generation/`의 Run은 생성 당시 Source와 Index Hash를 포함하는 불변 감사 기록이다. 뒤 Run이 앞 Run의 생성 기준을 대체하더라도 이전 Run의 Chunk Count와 Index Hash를 삭제하거나 재작성하지 않는다.

| Run | 역할 | 후속 생성 기준 |
|---|---|---|
| `run_001` | Generation Query의 의미, RAG 접근 정책, Protocol Preservation과 최초 Evidence Freeze가 형성된 실험 기록 | 사용하지 않음 |
| `run_002` | Systolic Controller Reference RTL까지 포함한 Source, Chunking/Ingestion, Retrieval Evidence와 최종 Systolic Prototype 검증 기록 | 현재 기준 |

`run_001`의 Source/Index 정보는 현재 RAG DB를 설명하기 위한 값이 아니라 당시 Query 결과를 재현하기 위한 값이다. Optimization Generation은 `run_002`가 고정한 검증 완료 Systolic Prototype과 새로 승인할 Optimization SPEC만 사용한다.

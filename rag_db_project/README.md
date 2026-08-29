# Legacy FC-MLP To Systolic Accelerator RAG Project

## 외부 LLM API 최후 수단 정책

일반적인 프로젝트 운영에서는 외부 LLM API를 원천 차단하지 않는다. 승인된 RAG DB에서 필요한 근거를 찾지 못한 경우에만 다음 절차를 적용한다.

1. Agent는 근거가 없는 설계 결정을 추측하지 않고 `unknown`으로 보고한다.
2. 부족한 정보와 영향을 받는 Requirement를 사용자에게 제시하고 외부 조사 승인을 받는다.
3. 승인된 경우에만 외부 LLM API 또는 외부 자료를 최후의 수단으로 사용한다.
4. 외부에서 얻은 내용은 바로 코드 근거로 사용하지 않는다. 사용자가 검토한 뒤 SPEC에 반영하고 Source Manifest와 RAG Index를 다시 생성한다.
5. 새 SPEC의 Requirement와 Retrieval Evidence가 고정된 뒤에만 코드 생성을 재개한다.

그림의 `신뢰도 90%`는 LLM의 주관적 자기평가가 아니라 Requirement Coverage, 인용 가능한 근거, Source Hash, 금지 경로 누출 검사로 판정한다. `systolic_prototype_run_001`은 비교 실험의 독립성을 위해 이 최후 수단까지 비활성화한 예외 Run이며, 외부 Web 검색과 외부 LLM/API를 사용하지 않는다.

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
- 승인된 SPEC이 이름까지 요구한 signal만 생성 코드의 고정 interface로 사용한다.
- 내부 module, state, register 및 helper signal 이름은 `historical_baselines/`에서 복사하거나 그 이름을 정답처럼 사용하지 않는다.
- Historical Baseline에만 존재하는 구현 세부사항은 SPEC 요구사항으로 승격하지 않는다.
- RAG 생성 결과는 승인된 기능과 interface를 만족하되, Historical Baseline과 독립적으로 설계되어야 한다.
- 비교 실험에서는 기능 정확도와 cycle뿐 아니라 module 분해, RTL 구조 및 코드 유사도도 함께 평가한다.

## 진행 단계

Reference Model과 Systolic Accelerator SPEC은 version 1.0으로 승인됐으며, 241개 입력 파일은 `rag-input-baseline-v1.0` tag와 SHA-256 inventory로 동결됐다.

`prototype_generation` 접근 정책에 따라 Markdown과 Reference RTL 18개 원천을 143개 chunk로 나눠 로컬 Hybrid Index에 ingestion했다. SQLite FTS5 BM25와 384차원 deterministic feature-hash dense index를 사용하며, Historical Baseline과 workspace를 포함한 금지 경로 chunk는 0개다. Retrieval smoke test까지 통과했으므로 다음 단계는 `workspace/systolic_prototype/`에 독립적인 RTL 초안을 생성하는 것이다.

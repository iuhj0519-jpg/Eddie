# Unified Buffer and AXI Latency Hiding Architecture Optimization Specification

- 문서 ID: OPT-SPEC-001
- 버전: 1.0
- 상태: approved
- 선행 조건: 승인된 Reference Model SPEC, Systolic Accelerator SPEC 및 검증 완료된 Systolic Prototype
- 적용 범위: Unified Buffer, Input Loader, DNN Scheduler, AXI-Stream Input Scheduling 및 PPA 구현 규칙

## 1. 목적

본 문서는 기존 Input Buffer와 Global Buffer의 기능을 하나의 Unified Buffer로 통합하고, 현재 Batch의 Compute 시간에 다음 Batch의 AXI-Stream Input을 Prefetch하여 Batch 사이의 입력 Latency를 숨기는 최적화 아키텍처를 정의한다.

최적화의 우선순위는 다음과 같다.

1. 분리된 Buffer를 5-bank Unified Buffer로 통합하여 FPGA Memory Inference와 Packing 가능성을 높인다.
2. 첫 Batch를 제외한 AXI Load를 Compute와 겹쳐 End-to-End Cycle을 줄인다.
3. 외부 결과 Protocol, 수치 정확도와 5×5 Output-Stationary Systolic Controller의 연산 의미를 유지한다.
4. Memory 용량과 주소 배치는 고정하지 않고 Data Lifetime, Port Conflict와 목표 FPGA의 Memory Primitive를 근거로 산정한다.
5. 추가 최적화는 정확도와 Protocol을 훼손하지 않는 범위에서 PPA Report로 판단한다.

Unified Buffer 통합이 BRAM Block 또는 Area 감소를 보장하지는 않는다. 실제 이득은 선택한 용량, Port 구조, FPGA Memory Packing과 합성 결과로 판정한다.

## 2. Normative Evidence Boundary

본 SPEC의 구현은 승인된 RAG Source와 검증된 Systolic Prototype만 근거로 사용한다. 승인되지 않은 비교용 구현이나 승인 Source 밖의 설계 사례를 구현 근거로 사용하지 않는다. 근거가 없거나 서로 충돌하는 결정은 임의로 채우지 않고 `unknown`으로 보고한 뒤 SPEC 승인을 다시 받아야 한다.

본 문서의 기능·Interface·Timing Requirement가 규범적이다. Agent가 명시되지 않은 구조를 추가하려면 구현 전에 승인된 근거, Cycle과 Interface 영향을 보고해야 한다.

## 3. Optimized Top Architecture

```text
AXI-Stream Input
       |
       v
+---------------------------+
| Input Loader              |
| Batch Counter/Prefetch    |
+---------------------------+
       |
       v
+---------------------------------------------+
| Unified Buffer: 5 Banks                     |
| - Current Batch Operand Storage             |
| - Layer 1/2 Intermediate Activation Storage |
| - Next Batch Prefetch Storage               |
+---------------------------------------------+
       | current Layer source
       v
+----------------------+      +--------------------+
| Systolic Controller  | <--- | Weight SRAM       |
| 5x5 Systolic Array   |      +--------------------+
+----------------------+      +--------------------+
       | partial sums          | Bias SRAM/SigROM  |
       v                       +--------------------+
+----------------------+
| Activation Unit      |
+----------------------+
       | Layer 1/2: Unified Buffer
       | Layer 3: MaxFinder path
       v
MaxFinder -> axi_lite_wrapper -> 0x08 Results / intr

DNN Scheduler controls compute ownership and layer/group sequencing.
Input Loader independently controls next-Batch prefetch ownership.
```

Reference Model에서 계승된 `zyNet`, `axi_lite_wrapper`, `maxFinder` Module 이름과 외부 Port 이름은 유지한다. 새 기능 Block의 이름은 기능을 명확히 나타내는 이름을 사용하며, Parameter는 `UPPER_SNAKE_CASE`, Signal/Register/Counter는 full-name lowercase `snake_case`를 사용한다.

## 4. Unified Buffer Functional Capacity

Unified Buffer는 8-bit Q1.7 Data를 저장하고 5개 image lane에 필요한 병렬 접근을 지원해야 한다. 물리 깊이, 전체 용량, 주소 분할, Ping-Pong 영역 수와 Physical Address Encoding은 Agent가 구현 전에 결정한다.

### 4.1 Required Live Data

용량 산정에는 최소한 다음 Data Lifetime을 포함해야 한다.

| Data Set | 최대 논리 항목 수 | Lifetime |
|---|---:|---|
| Current Batch Layer 1 Input | `5 × 784` | 해당 Feature가 Layer 1에서 마지막으로 소비될 때까지 |
| Layer 1 Activation | `5 × 30` | Layer 2에서 소비될 때까지 |
| Layer 2 Activation | `5 × 20` | Layer 3에서 소비될 때까지 |
| Next Batch Prefetch | 최대 `5 × 784` | 다음 Batch의 Layer 1 소비 완료까지 |

Layer 3 Activation은 기본 Dataflow에서 Unified Buffer에 저장하지 않고 MaxFinder 경로로 전달한다.

### 4.2 Capacity Selection Rule

Agent는 단순히 위 항목을 모두 더해 고정 용량으로 사용해서는 안 된다. 다음 절차로 필요한 용량과 주소를 산정해야 한다.

1. Batch와 Layer별로 동시에 살아 있는 Data Set을 기록한 Lifetime Table을 만든다.
2. 이미 마지막 소비가 끝난 Storage는 다음 Batch Prefetch 또는 다음 Layer 결과에 재사용한다.
3. Read/Write가 같은 Cycle에 필요한 Data는 Port Conflict가 없는 물리 위치에 배치한다.
4. 후보 Depth를 목표 FPGA Memory Primitive의 Width/Depth 조합에 Mapping한다.
5. 후보별 Memory Bit, BRAM Block, Logic MUX, Port Stall과 Timing을 비교한다.
6. 선택한 총 용량, Bank별 Depth, 주소식, Ownership 전환 조건과 선택 근거를 Generation Evidence에 기록한다.

선택된 용량은 다음 조건을 모두 만족하는 최소의 구현 가능 용량이어야 한다.

- 현재 Layer Operand를 손실 없이 유지한다.
- Layer 1/2 Intermediate Activation을 다음 Layer가 소비할 때까지 유지한다.
- Compute와 겹쳐 수신한 다음 Batch Data를 덮어쓰지 않는다.
- 이미 소비가 끝난 위치는 재사용할 수 있다.
- 동일 주소 또는 허용 Port 수를 넘는 접근은 Scheduling이나 Backpressure로 방지한다.

### 4.3 Ping-Pong Semantics

Ping-Pong Buffering은 특정 주소 범위나 고정된 두 Physical Array를 의미하지 않는다. 다음 두 역할이 충돌 없이 교대하면 된다.

- Compute Ownership: 현재 Batch 또는 현재 Layer가 읽는 Data
- Fill Ownership: 다음 Layer 결과 또는 다음 Batch Prefetch가 쓰는 Data

역할 교대는 Valid와 Ownership Metadata로 제어한다. 동등한 기능을 만족한다면 두 논리 영역, Circular Buffer, Lifetime 기반 Address Reuse 또는 다른 BRAM-Friendly Mapping을 사용할 수 있다.

## 5. AXI-Stream Input and Batch Prefetch

외부 Signal 이름과 Width, `axis_in_data_valid && axis_in_data_ready`에서만 Transfer가 성립한다는 AXI-Stream 규칙은 유지한다. Input Order는 Batch별 Image-Major이다.

```text
Batch b:
  image 5b+0 feature 0..783
  image 5b+1 feature 0..783
  image 5b+2 feature 0..783
  image 5b+3 feature 0..783
  image 5b+4 feature 0..783
```

### 5.1 Ready Behavior

다음 Batch를 저장할 공간 또는 쓰기 Port가 없는데 Transfer를 승인하면 아직 계산하지 않은 Data가 덮어써질 수 있다. 따라서 다음 계약을 적용한다.

- Initial Batch 또는 Next Batch를 저장할 안전한 위치가 있으면 `axis_in_data_ready=1`이다.
- 5×784 Transfer가 완료되어 다음 Batch Storage가 가득 차면 Ownership이 전환될 때까지 `axis_in_data_ready=0`이다.
- Buffer Port가 Activation Write에 사용되어 Prefetch Write를 받을 수 없는 Cycle에는 `axis_in_data_ready=0`으로 Backpressure한다.
- `axis_in_data_valid=1`이고 `axis_in_data_ready=0`인 동안 Sender는 Data와 Valid를 유지해야 한다.
- Stall은 Data Loss, 중복 Count 또는 Image/Feature 순서 변경을 일으켜서는 안 된다.

### 5.2 Prefetch Metadata

Input Loader는 다음 정보를 동등한 의미로 관리해야 한다.

- Compute Storage Ownership
- Prefetch Storage Ownership
- Prefetch Valid/Complete
- Image Index `0:4`
- Feature Index `0:783`

전체 Input Matrix를 별도 Controller Register Array로 복제해서는 안 된다. Transfer된 Data는 Unified Buffer의 Agent가 선택한 Prefetch 위치에 직접 기록한다.

5×784 Transfer가 모두 완료된 뒤에만 해당 Batch를 Prefetch Complete로 표시한다. DNN Scheduler는 현재 Batch의 Result Protocol이 끝났고 Prefetch Complete가 참일 때만 다음 Batch Compute Ownership을 부여한다. Prefetch가 늦으면 정확성을 우선하여 대기한다.

## 6. AXI Latency Hiding Schedule

목표 Timeline은 다음과 같다.

```text
Time ->
Batch 0: [AXI Load][---------- Compute ----------]
Batch 1:            [AXI Load][---------- Compute ----------]
Batch 2:                       [AXI Load][---------- Compute ----------]
```

Batch 0은 빈 Buffer를 채워야 하므로 AXI Load Latency가 노출된다. Batch 1 이후의 Load는 이전 Batch Compute와 겹친다.

한 Batch의 AXI Transfer Cycle을 `L`, Compute 중 Prefetch 가능 Cycle을 `C_OVERLAP`이라고 할 때, Prefetch가 완전히 숨겨지는 필요조건은 다음과 같다.

```text
L <= C_OVERLAP
```

연속 Valid이고 Cycle당 1개 8-bit Feature를 전송하면 `L = 5 × 784 = 3,920` Transfer Cycle이다. `C_OVERLAP`은 Activation Write 충돌이나 다른 Port 사용으로 Backpressure된 Cycle을 제외한 실제 Prefetch 가능 구간이다.

Prefetch가 완료되는 Steady State의 Batch 간 Compute 시작 간격은 입력과 계산을 직렬화한 `L + C`가 아니라 대략 `max(L, C)`가 된다. 전체 20-Batch Latency는 최초 Load와 마지막 Drain을 별도로 포함해 측정한다.

다음 경우에는 AXI Latency가 완전히 숨겨지지 않을 수 있다.

- Upstream `axis_in_data_valid` Stall
- Unified Buffer Port Conflict로 인한 Ready Backpressure
- `L > C_OVERLAP`
- 이전 Batch의 AXI-Lite Result Read 지연

이 경우 구현은 Data를 덮어쓰지 말고 Scheduler를 대기시켜야 하며, 노출된 Stall Cycle과 원인을 기록해야 한다.

## 7. Unified Buffer Port and Collision Rules

FPGA BRAM 추론을 위해 Read는 Synchronous 1-Cycle Latency를 기본으로 한다. Memory Array 전체를 Reset하지 않고 Ownership, Valid, Address Counter와 같은 Metadata만 Reset한다.

Port 우선순위는 다음과 같다.

1. Current Layer Operand Read
2. Activation Result Write
3. Next Batch AXI Prefetch Write

Compute Read와 Activation Write가 동시에 필요하면 목표 Memory Primitive의 Port 수 안에서 충돌 없이 처리한다. 추가 Prefetch Access가 허용 Port 수를 넘으면 Prefetch만 Stall하고 `axis_in_data_ready=0`으로 만든다. Compute 결과나 Activation Write를 버려서는 안 된다.

Agent는 구현 전에 다음 접근 조합의 충돌 여부를 표로 작성해야 한다.

- Layer 1 Operand Read, Layer 1 Activation Write와 Next Batch Prefetch
- Layer 2 Operand Read, Layer 2 Activation Write와 Next Batch Prefetch
- Layer 3 Operand Read와 Next Batch Prefetch
- 동일 Bank의 Activation Write와 AXI Prefetch Write
- Ownership 전환 경계의 마지막 Read/Write와 다음 Batch 첫 Read

Read-During-Write 동작이 FPGA Device 설정에 의존하면 동일 주소 충돌을 Scheduling으로 금지해야 한다. Simulation Model과 Synthesis Inference의 의미가 달라서는 안 된다.

## 8. DNN Scheduler and Input Loader

DNN Scheduler는 Layer/Group/Tile/Activation/MaxFinder/Result 순서를 관리한다. Input Loader는 AXI Transfer와 Prefetch Storage를 독립적으로 관리한다. 하나의 FSM에 모든 상태를 직렬화하여 Prefetch가 Compute를 기다리게 해서는 안 된다.

DNN Scheduler는 다음 조건을 보장해야 한다.

- Batch 0은 Initial Load Complete 뒤 Compute를 시작한다.
- Batch N Compute 중 Batch N+1 Prefetch를 허용한다.
- 현재 Layer Operand와 Activation Destination의 Ownership을 명시적으로 선택한다.
- Layer 1/2는 Unified Buffer에 Intermediate Activation을 저장한다.
- Layer 3 Activation은 Unified Buffer에 저장하지 않고 MaxFinder로 전달한다.
- 현재 Batch 결과가 준비되면 Batch당 1-Cycle `intr`를 발생시킨다.
- AXI-Lite byte address `0x08`에서 class 5개를 image 순서로 읽는 계약을 유지한다.
- 다섯 번째 Result Read Handshake가 완료되기 전에는 결과를 덮어쓰지 않는다.
- 다음 Batch가 Prefetch Complete여도 Result Protocol이 끝나지 않았으면 Compute 전환을 기다린다.

## 9. Preserved Compute And Numeric Contracts

다음 항목은 Optimization으로 변경하지 않는다.

- 5×5 Output-Stationary Systolic Array
- `IDLE`, `RUN`, `DONE_STATE` Controller 의미와 1-Cycle Start/Done 계약
- SRAM Streaming Adapter와 Matrix Register 복제 금지
- Layer 1/2/3의 6/4/2 Group
- Group별 797/43/33 Target Cycle
- Q1.7 × Q4.4 → Q15.11, Bias Q5.3, Sigmoid Input Q5.5, Activation Output Q1.7
- Q5.5 LUT Address Saturation과 `sigContent.mif`
- 100개 Image, 20개 Batch, Batch당 image 5개
- Classification, Tie Rule, `0x08` Result와 `intr` 의미

Buffer의 Synchronous Read 또는 새로운 Arbitration 때문에 Controller Cycle 변경이 불가피하면 구현 전에 변경 이유와 새 Cycle 식을 보고하고 SPEC 승인을 받아야 한다.

## 10. Additional PPA Requirements

### 10.1 BRAM-Friendly RTL

- Unified Buffer는 5-bank Synchronous Memory Template으로 작성한다.
- Memory Data Array에 비동기 Read나 전체 Reset Loop를 사용하지 않는다.
- Bank별 Read/Write Enable을 사용하여 불필요한 Toggle을 줄인다.
- Device 종속 Primitive를 고정하기 전에 Portable Inference RTL을 우선한다.
- 합성 Report에서 MLAB/LUT RAM 또는 BRAM 중 무엇으로 추론됐는지 확인한다.
- 최소 논리 Bit 수뿐 아니라 실제 소비되는 Memory Block 수를 기준으로 후보를 선택한다.

### 10.2 Control and Counter Width

- Counter와 Address Width는 선택된 용량에 필요한 최소 Width를 Parameter/Localparam에서 계산한다.
- 큰 Data MUX보다 Ownership 기반 Address Selection을 우선한다.
- 반복 Decode는 공통 Control Signal로 묶되, Critical Fan-Out이 커지면 합성 결과로 조정한다.

### 10.3 Power

- 임의의 Fabric Clock Gating을 만들지 않고 Clock Enable을 사용한다.
- 사용하지 않는 Bank, Systolic PE Update, SRAM Read와 SigROM Lookup은 Enable로 정지한다.
- Valid가 없는 Data 변경이 Datapath Toggle을 유발하지 않게 한다.

### 10.4 Unified Buffer Disadvantage Minimization

Unified Buffer 통합으로 발생할 수 있는 Memory Capacity 증가, Port Competition, Address MUX 증가, Critical Path 악화와 동시 Access Power 증가를 최소화해야 한다. Agent는 하나의 Mapping을 즉시 채택하지 않고 최소 두 개 이상의 구현 후보를 비교해야 한다.

- Data Lifetime 기반 Storage Reuse로 동시에 필요한 Live Data만 보존한다.
- Compute Read와 Activation Write를 우선하고 Prefetch는 Backpressure로 안전하게 지연한다.
- 가능한 후보마다 Memory Bit와 실제 BRAM Block 수를 모두 계산한다.
- 큰 Crossbar보다 Bank-Local Address와 Ownership Decode를 우선한다.
- Prefetch가 Compute Critical Path에 조합논리로 연결되지 않도록 Ready와 Ownership 경로를 분리한다.
- 추가 Memory와 동시 Access가 만드는 Dynamic Power를 Bank Enable과 Clock Enable로 억제한다.
- 후보 선택 기준은 기능 충족 후 Total Cycle, BRAM Block, Logic, Fmax, Power 순으로 기록한다.

### 10.5 Optional Exploration

- SigROM 공유는 Area를 줄일 수 있지만 5-Lane 처리량을 낮출 수 있으므로 고정하지 않는다.
- 추가 Pipeline은 Fmax를 높일 수 있지만 Cycle과 Handshake를 바꾸므로 사전 보고와 승인이 필요하다.

## 11. PPA Measurement And Acceptance

최적화 효과는 동일한 FPGA Family, Synthesis Option과 Timing Constraint의 Report로 판단한다.

### 11.1 Theoretical Performance Bound

승인된 Group Cycle을 기준으로 한 Batch의 Systolic Controller 계산량은 다음과 같다.

```text
C_GROUP = 6 × 797 + 4 × 43 + 2 × 33
        = 5,020 cycles per batch
L_INPUT = 5 × 784
        = 3,920 transfer cycles per batch
```

`C_OVERLAP`이 `L_INPUT` 이상이고 Source Stall과 Port Stall이 충분히 작으면 Batch 1~19의 Input Load를 이전 Batch Compute에 모두 숨길 수 있다. Controller Group Cycle과 Input Transfer만 포함한 단순 이론 비교는 다음과 같다.

```text
Serialized 20 batches = 20 × (3,920 + 5,020) = 178,800 cycles
Overlapped 20 batches = 3,920 + 20 × 5,020   = 104,320 cycles
Maximum hidden input  = 19 × 3,920           = 74,480 cycles
```

이 단순 경계에서는 약 41.7% Cycle 감소와 약 1.71× Total Throughput 향상이 가능하다. Steady-State Batch 시작 간격만 비교하면 `8,940`에서 `5,020` Cycle로 약 43.8% 감소한다.

이 값에는 Activation, MaxFinder, AXI-Lite Result Read, Scheduler 전환, Source Stall과 Memory Port Stall이 포함되지 않는다. 따라서 구현 목표와 검증 기준으로만 사용하며 최종 성능은 Simulation 측정값으로 보고한다.

필수 비교 항목은 다음과 같다.

- Functional Regression: 100 Samples, 99 PASS / 1 FAIL, Accuracy 99.0%
- Total Cycle과 Batch별 Cycle
- 최초 Batch Load Cycle
- Steady-State Batch 간 간격
- AXI Ready Low Cycle, Source Valid Stall Cycle, Prefetch Wait Cycle
- Unified Buffer 선택 용량과 Data Lifetime Table
- ALM/Logic Element, Register, Memory Bit, BRAM Block 수
- Fmax와 Worst Slack
- 가능하면 Dynamic/Static Power Estimate

최적화 성공 조건은 기능·수치·Protocol Regression을 통과하고, 다음 두 핵심 목표 중 측정 가능한 Gain을 보이는 것이다.

1. 첫 Batch 이후 AXI Load가 Compute에 대부분 또는 전부 숨겨져 Total Cycle이 감소한다.
2. Unified Buffer가 목표 FPGA에서 더 안정적인 BRAM Inference 또는 유리한 Memory Block Packing을 보인다.

논리 Memory Capacity 증가는 허용된 Trade-Off이지만, BRAM Block 수와 Area가 모두 악화되고 Performance Gain도 없으면 구조를 재검토해야 한다.

## 12. Requirements

- REQ-OPT-001: Input Buffer와 Global Buffer의 기능을 하나의 5-bank Unified Buffer로 통합해야 한다.
- REQ-OPT-002: Unified Buffer 용량과 주소는 Current Operand, Layer 1/2 Intermediate Activation과 Next Batch Prefetch의 Data Lifetime 분석으로 결정해야 한다.
- REQ-OPT-003: Agent는 구현 전에 선택한 총 용량, Bank별 Depth, 주소식, Ownership과 BRAM Mapping 근거를 보고해야 한다.
- REQ-OPT-004: 마지막 소비가 끝난 Storage는 안전하게 재사용하여 불필요한 Capacity 증가를 줄여야 한다.
- REQ-OPT-005: Layer 3 Activation은 기본 Dataflow에서 Unified Buffer에 저장하지 않고 MaxFinder 경로로 전달해야 한다.
- REQ-OPT-006: Compute Ownership과 Fill Ownership은 동일 Live Data를 덮어쓰지 않도록 Ping-Pong 방식 또는 동등한 방식으로 교대해야 한다.
- REQ-OPT-007: Batch 0은 Initial AXI Load 완료 후 Compute를 시작해야 한다.
- REQ-OPT-008: Batch N Compute 중 Batch N+1의 Image-Major 5×784 Input을 Unified Buffer에 Prefetch해야 한다.
- REQ-OPT-009: 안전한 Storage 또는 Memory Port가 없으면 `axis_in_data_ready=0`으로 Backpressure해야 한다.
- REQ-OPT-010: AXI Transfer는 오직 `axis_in_data_valid && axis_in_data_ready`에서 Count해야 한다.
- REQ-OPT-011: Prefetch Complete와 Current Result Protocol 완료 전에는 다음 Batch Compute Ownership을 부여해서는 안 된다.
- REQ-OPT-012: Input Loader와 DNN Scheduler는 AXI Prefetch와 Compute가 병렬 진행될 수 있게 제어를 분리해야 한다.
- REQ-OPT-013: 전체 Input Matrix를 별도 Controller Register Array로 복제해서는 안 된다.
- REQ-OPT-014: Unified Buffer는 1-Cycle Synchronous Read와 Bank별 Enable을 사용하는 BRAM-Friendly RTL이어야 한다.
- REQ-OPT-015: Memory Data Array 전체를 Reset하지 않고 Valid와 Ownership Metadata만 Reset해야 한다.
- REQ-OPT-016: Port 충돌 시 Compute Read, Activation Write, AXI Prefetch Write 순으로 우선하고 Prefetch를 Stall해야 한다.
- REQ-OPT-017: Image-Major Order, Fixed-Point, Systolic Controller, MaxFinder와 AXI-Lite `0x08` Result 계약을 유지해야 한다.
- REQ-OPT-018: `intr`는 Batch 결과가 준비될 때 Batch당 정확히 한 번, 1 cycle assertion해야 한다.
- REQ-OPT-019: `zyNet`, `axi_lite_wrapper`, `maxFinder`의 계승 Module 이름과 외부 Port 이름을 유지해야 한다.
- REQ-OPT-020: Parameter는 `UPPER_SNAKE_CASE`, 새 Signal/Register/Counter는 full-name lowercase `snake_case`를 사용해야 한다.
- REQ-OPT-021: Counter와 Address는 선택한 Mapping에 필요한 최소 Width를 사용해야 한다.
- REQ-OPT-022: Inactive Memory와 Datapath는 Clock Enable 또는 Bank Enable로 Toggle을 억제해야 한다.
- REQ-OPT-023: Agent는 Unified Buffer 후보를 최소 두 개 비교하고 Memory Capacity, Port Competition, Address MUX, Fmax와 Power 불이익을 최소화한 구조를 선택해야 한다.
- REQ-OPT-024: `L > C_OVERLAP` 또는 Input Stall이면 Data를 덮어쓰지 않고 다음 Compute를 대기하며 Stall 원인을 기록해야 한다.
- REQ-OPT-025: 동일 조건의 합성·시뮬레이션에서 기능, Cycle, BRAM, Logic, Register, Fmax와 가능한 Power를 보고해야 한다.

## 13. Verification Items

- Agent가 작성한 Data Lifetime Table과 선택 용량의 충분성 검토
- Bank별 Address Mapping과 Ownership Collision 검증
- 3,920개 Transfer에서만 Prefetch Complete가 되는지 확인
- Prefetch Full에서 `axis_in_data_ready=0` 및 Data 안정성 확인
- Random `axis_in_data_valid` Stall과 Ready Backpressure 조합
- Layer 1/2 Read/Write와 Prefetch의 Port Collision Assertion
- Ownership 전환 전후 마지막/첫 접근 경계 Assertion
- Batch 0 Load 노출과 Batch 1~19 Load/Compute Overlap 측정
- Prefetch 미완료 시 안전한 Scheduler Wait
- AXI-Lite Result Read 지연 중 결과 보존
- Layer 3의 Unified Buffer Write 부재와 MaxFinder 전달
- 797/43/33 Controller Cycle 또는 승인된 변경 Cycle
- Q5.5 Saturation과 100-Sample 99% Regression
- 20개 Batch의 `intr` 1-Cycle Pulse
- Memory Array Reset Loop 부재와 Synchronous BRAM Inference
- 선택 용량 후보별 Synthesis Resource, Fmax와 Power Report 수집

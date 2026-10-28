# TCAD Project Final Goal and Optimization Criteria

## 1. Purpose of This Document

이 문서는 `README_TCAD_MOSFET_PROJECT_Github_구조정리본.md`를 기반으로 수행하는 TCAD 프로젝트의 **최종 목표, 최적화 논리, 정량 성과 산출 방식, 자기소개서/포트폴리오용 KPI 작성 기준**을 Agent가 일관되게 이해하고 적용할 수 있도록 정리한 운영 문서이다.

이 문서는 구현 상세를 대체하지 않는다.

- 구현 절차와 Phase 순서: 메인 README를 따른다.
- 본 문서의 역할: 프로젝트가 최종적으로 **어떤 수치를 산출해야 하며, 그 수치를 어떤 기준으로 해석·보고할지** 정의한다.

---

# 2. Project Positioning

이 프로젝트는 단순 논문 재현 프로젝트가 아니다.

프로젝트의 성격은 다음과 같다.

```text
Open-source TCAD / DEVSIM 분석
        ↓
선행 논문의 구조·설계 아이디어 분석
        ↓
자체 baseline device 구축
        ↓
Gate stack / doping / spacer / scaling 효과 분리
        ↓
논문 아이디어를 차용한 자체 설계 확장
        ↓
제한된 다변수 최적화
        ↓
Pareto trade-off 분석
        ↓
수치적으로 검증된 최종 candidate 도출
```

선행 논문은 다음 용도로 사용한다.

- HKMG 설계 개념 참고
- LDD 구조 참고
- multi-spacer 개념 참고
- 28 nm planar NMOS 설계 맥락 참고
- 문헌 수치와 qualitative trend 비교

그러나 다음을 주장하지 않는다.

- 논문 구조를 완전히 재현했다.
- 논문의 공정 recipe를 재현했다.
- 논문 성능값에 calibration했다.
- 제조 공정 수준의 process TCAD를 수행했다.

핵심 결과는 **동일 모델·동일 추출법·통제된 조건에서 자체 baseline 대비 얻은 개선과 trade-off**이다.

---

# 3. Final Optimization Objective

최종 최적화의 목적은 하나의 지표만 극단적으로 개선하는 것이 아니다.

다음 성능 지표를 동시에 고려한다.

```text
Ion       → maximize
Ioff      → minimize
SS        → minimize
DIBL      → minimize
Vth       → target range 유지
Ion/Ioff  → maximize
```

가능한 경우 추가적으로 다음을 확인한다.

```text
Peak Electric Field → minimize
EOT                 → feasible range
Solver Stability    → maintain
Mesh Independence   → maintain
```

따라서 "최적"은 단일 scalar score가 아니라 **feasible Pareto candidate** 중에서 선택한다.

---

# 4. Baseline Definition

최종 개선율의 기준은 논문 수치가 아니라 **프로젝트 자체 baseline**이다.

핵심 baseline은 README에서 정의한 28 nm 기준 소자 `B28`이다.

```text
Long-channel validation
        ↓
100 nm numerical baseline
        ↓
Gate-length scaling
        ↓
28 nm model review
        ↓
B28 fixed baseline
```

`B28`은 다음을 통과한 상태여야 한다.

- mesh convergence
- solver convergence
- extraction consistency
- numerical unit checks
- model assumption review
- 28 nm bias sweep stability

최적화 이후 모든 주요 개선율은 기본적으로 `B28` 대비 계산한다.

요소별 실험에서는 각 실험의 통제군을 별도로 사용한다.

예:

```text
High-k effect
→ SiO2 gate-stack control 대비

Spacer effect
→ S0 SiO2 spacer 대비

Halo extension
→ no-halo control 대비
```

---

# 5. Optimization Variables

최적화는 한 번에 모든 변수를 조절하지 않는다.

먼저 OFAT 또는 제한된 sweep으로 각 변수의 영향을 이해한 뒤, 영향도가 큰 2–3개 변수를 조합한다.

## 5.1 Gate Stack Variables

```text
t_SiO2
t_IL
t_HfO2
EOT
dielectric material
effective gate work function (Phi_eff)
```

주요 실험 흐름:

```text
SiO2 thickness scaling
        ↓
High-k / EOT comparison
        ↓
Metal gate / work-function engineering
        ↓
HKMG integration
```

## 5.2 Doping Variables

```text
Channel doping
LDD concentration
LDD depth
LDD lateral spread
LDD length
Halo-like doping [optional extension]
```

Halo는 논문 재현 요소가 아니라 **자체 확장 설계**로 취급한다.

## 5.3 Spacer Variables

```text
SiO2 spacer
SiON spacer
SiO2 / SiON
SiON / SiO2
SiO2 / SiON / SiO2
total spacer width
internal layer ratio
```

필요 시 문헌의 SiO2 / Si3N4 계열과 비교한다.

---

# 6. Step-by-Step Optimization Flow

최종 최적화는 다음 순서로 진행한다.

## Step 1 — Establish B28

고정할 항목:

- Lg = 28 nm
- extraction definition
- bias condition
- reference width
- model coefficient set
- contact assumptions
- mesh policy

출력:

```text
Vth
SS
DIBL
Ion
Ioff
Ion/Ioff
```

이 값이 최종 개선율 계산의 기준이 된다.

## Step 2 — Gate Stack Optimization

순서:

```text
SiO2 thickness
        ↓
HfO2 / IL thickness
        ↓
Matched-EOT comparison
        ↓
Phi_eff sweep
        ↓
HKMG candidate
```

목표:

- SS 개선
- DIBL 개선
- Vth target 유지
- Ion 감소 최소화
- Ioff 감소

## Step 3 — Doping Optimization

순서:

```text
Channel doping
        ↓
LDD profile
        ↓
Optional halo-like profile
```

평가:

- Vth
- SS
- DIBL
- Ion
- Ioff
- peak electric field
- series-resistance trade-off

## Step 4 — Spacer Optimization

비교:

```text
S0: SiO2
S1: SiON
S2: SiO2 / SiON
S3: SiON / SiO2
S4: SiO2 / SiON / SiO2
```

평가:

- DIBL
- SS
- Ion/Ioff
- barrier potential
- gate-edge electric field
- drain-side electric field

## Step 5 — Reduced Multi-Variable DOE

README 원칙에 따라 한 번에 최대 2–3개 핵심 변수를 결합한다.

예:

```text
DOE-A:
t_IL × t_HfO2

DOE-B:
selected gate stack × Phi_eff

DOE-C:
selected spacer × LDD length
```

필요할 때만 다음을 추가한다.

```text
channel doping
halo-like profile
spacer composition
```

## Step 6 — Pareto Candidate Selection

각 candidate에 대해 동일한 extraction library를 사용한다.

예시 테이블:

| Candidate | SS | DIBL | Ion | Ioff | Ion/Ioff |
|---|---:|---:|---:|---:|---:|
| B28 | ... | ... | ... | ... | ... |
| C1 | ... | ... | ... | ... | ... |
| C2 | ... | ... | ... | ... | ... |
| C3 | ... | ... | ... | ... | ... |

단일 최고값이 아니라 trade-off를 판단한다.

## Step 7 — Fine-Mesh Revalidation

최종 후보는 반드시 다시 계산한다.

검증:

```text
Fine mesh
Smaller bias step
Convergence check
Current conservation
Extraction repeatability
```

중간 mesh에서 좋아 보였던 결과가 fine mesh에서 유지되는지 확인한다.

---

# 7. Final KPI Calculation

최종 자기소개서 및 포트폴리오에서 사용하는 수치는 다음 방식으로 계산한다.

## 7.1 감소가 좋은 지표

예: DIBL, SS, Ioff

```text
Improvement (%) =
(Baseline - Optimized) / Baseline × 100
```

예시:

```text
B28 DIBL       = 91.4 mV/V
Optimized DIBL = 58.7 mV/V
```

```text
DIBL improvement
= (91.4 - 58.7) / 91.4 × 100
= 35.8%
```

자기소개서 표현:

> DIBL을 35.8% 개선했습니다.

## 7.2 증가가 좋은 지표

예: Ion, Ion/Ioff

```text
Improvement (%) =
(Optimized - Baseline) / Baseline × 100
```

또는 비율 자체가 더 직관적인 경우:

```text
Ion/Ioff = 1.8× improvement
```

## 7.3 유지 조건이 중요한 지표

최적화 결과는 다음 형식이 가장 좋다.

```text
[A 지표]를 X% 개선하면서
[B 지표]를 Y 이하 / Z 이상 / Δ% 이내 변화로 유지
```

예시:

> DIBL을 31% 감소시키면서 Ion 감소를 3% 이내로 유지했습니다.

또는:

> Ioff를 43% 줄이면서 Ion을 400 µA/µm 이상 유지했습니다.

또는:

> SS를 15% 개선하면서 DIBL을 70 mV/V 이하로 유지했습니다.

---

# 8. Preferred Final Resume KPI Style

가능하다면 다음 구조를 우선한다.

## Preferred Type A — Trade-off Controlled Optimization

> **DIBL을 X% 개선하면서 Ion 감소를 Y% 이내로 제한하는 EOT·work-function·LDD 조건을 도출했습니다.**

이 유형은 공정설계 직무에서 가장 강한 신호를 준다.

이유:

- 단일 지표 최적화가 아님
- trade-off 관리 능력을 보여줌
- 변수–성능 관계를 정량적으로 해석함
- 실제 engineering decision을 보여줌

## Preferred Type B — Leakage / Drive Balance

> **Ioff를 X% 감소시키면서 Ion을 Y 이상 유지하는 설계 조건을 도출했습니다.**

## Preferred Type C — Electrostatic Improvement

> **SS를 X% 개선하고 DIBL을 Y mV/V 이하로 낮추는 gate-stack 조건을 도출했습니다.**

---

# 9. Required Final Result Table

프로젝트 종료 시 다음 표를 반드시 생성한다.

| Metric | B28 Baseline | Optimized | Change |
|---|---:|---:|---:|
| Vth | actual | actual | Δ |
| SS | actual | actual | x% ↓ |
| DIBL | actual | actual | x% ↓ |
| Ion | actual | actual | x% ↑/↓ |
| Ioff | actual | actual | x% ↓ |
| Ion/Ioff | actual | actual | x× or x% ↑ |
| EOT | actual | actual | Δ |
| Peak E-field | actual | actual | x% ↓ |

그리고 최종 설계 변수도 함께 기록한다.

```text
Optimized Device Configuration

Lg          =
t_IL        =
t_HfO2      =
EOT         =
Phi_eff     =
NA          =
LDD length  =
LDD profile =
Spacer      =
Halo        = optional
```

---

# 10. Important Rule: Do Not Predefine Success Numbers

실험 전에 다음과 같은 목표를 임의로 정하지 않는다.

```text
"DIBL 30% 이상 개선해야 한다"
"SS 15% 이상 개선해야 한다"
```

실제 결과가 그보다 작아도 프로젝트 실패가 아니다.

예:

```text
DIBL 22% 개선
Ion 2.3% 감소
Ioff 18% 감소
```

이라면 다음처럼 충분히 의미 있는 결과가 된다.

> DIBL을 22% 개선하면서 Ion 감소를 2.3%로 제한하고 Ioff를 18% 줄이는 조건을 도출했습니다.

핵심은 **trade-off를 정량적으로 해석하고 합리적인 candidate를 선택했다는 것**이다.

---

# 11. Numerical Result Integrity

최종 KPI는 다음 조건을 만족한 결과만 사용한다.

- 동일 extraction version
- 동일 bias definition
- 동일 width normalization
- solver convergence
- mesh convergence
- fine-mesh revalidation
- failed point 제외
- NaN / Inf 제외
- 동일 model coefficient set

최적 candidate의 결과가 numerical uncertainty보다 충분히 큰 차이를 보이는지 확인한다.

예:

```text
Observed DIBL improvement = 3 mV/V
Mesh sensitivity          = 5 mV/V
```

이면 "개선"이라고 주장하지 않는다.

---

# 12. Literature-Derived vs Original Contribution

Agent는 프로젝트 결과를 다음 두 범주로 구분해야 한다.

## Literature-Derived

- HKMG 개념
- LDD 개념
- multi-spacer 개념
- 28 nm planar NMOS 맥락
- 논문의 구조적 아이디어

## Original Project Extension

- DEVSIM 기반 자체 baseline
- 동일 extraction pipeline
- SiO2 → High-k → work-function 효과 분리
- SiON spacer 적용
- spacer layer ordering study
- halo-like profile extension
- reduced multi-variable DOE
- Pareto analysis
- B28 대비 정량 개선율

자기소개서에서는 다음처럼 표현한다.

> 오픈소스 TCAD와 선행 논문을 분석한 뒤 HKMG·LDD·multi-spacer 설계 개념을 차용하고, 이를 DEVSIM 기반 자체 28 nm baseline에 적용·확장해 변수별 trade-off와 최적 조건을 분석했습니다.

"논문 구조를 그대로 재현했다"라고 표현하지 않는다.

---

# 13. Final Portfolio Narrative

최종 프로젝트 스토리는 다음 순서로 정리한다.

```text
기초 물리 검증
        ↓
DEVSIM baseline 구축
        ↓
28 nm scaling / SCE 분석
        ↓
Gate-stack engineering
        ↓
Doping engineering
        ↓
Spacer engineering
        ↓
Multi-variable DOE
        ↓
Pareto candidate selection
        ↓
Fine-mesh revalidation
        ↓
정량 KPI 도출
```

이 프로젝트의 핵심 역량은:

> **공정/소자 변수를 개별 파라미터로 보는 것이 아니라, 소자 특성과의 상관관계 및 trade-off 속에서 해석하고 최적 조건을 도출하는 능력**

으로 정리한다.

---

# 14. Final Completion Criteria

다음 항목이 모두 충족되어야 최종 최적화 완료로 간주한다.

- [ ] B28 baseline 수치 확정
- [ ] Gate-stack 주요 변수 sweep 완료
- [ ] Channel/LDD 분석 완료
- [ ] Spacer 대조실험 완료
- [ ] 선택한 2–3개 변수의 multi-variable DOE 완료
- [ ] Pareto candidate 선정
- [ ] Fine mesh 재검증
- [ ] 최종 KPI table 생성
- [ ] B28 대비 개선율 계산
- [ ] numerical uncertainty와 효과 크기 비교
- [ ] limitation 기록
- [ ] 자기소개서용 1–2개 핵심 정량 성과 선정

---

# 15. Agent Instruction

이 프로젝트를 지원하는 Agent는 다음 원칙을 따른다.

1. 메인 README를 master execution plan으로 사용한다.
2. 본 문서를 final-goal / KPI 기준 문서로 사용한다.
3. 실제 simulation 결과가 나오기 전에는 개선 수치를 임의 생성하지 않는다.
4. 각 Phase에서 얻은 결과를 최종 KPI와 연결 가능하도록 저장한다.
5. 모든 주요 후보는 동일 extraction library로 평가한다.
6. Baseline과 candidate의 비교 조건이 다르면 개선율을 계산하지 않는다.
7. 논문 수치와 자체 baseline 개선율을 혼동하지 않는다.
8. 결과가 예상과 달라도 숨기지 않고 trade-off로 해석한다.
9. 자기소개서용 결과는 fine-mesh 검증 완료 결과만 사용한다.
10. 최종 문장은 정량 결과 + 유지 조건 + 조절 변수까지 포함하는 형식을 우선한다.

Preferred final sentence template:

```text
[변수군]을 조절해 [A 지표]를 [X%] 개선하면서
[B 지표]를 [Y 기준]으로 유지하는 조건을 도출했습니다.
```

Example structure only:

```text
EOT·effective work function·LDD 조건을 조절해
DIBL을 X% 개선하면서 Ion 감소를 Y% 이내로 유지하는
28 nm planar NMOS 설계 조건을 도출했습니다.
```

`X`, `Y`는 반드시 실제 검증된 simulation 결과로 대체한다.

DEVSIM은 각 설계 후보의 semiconductor PDE를 계산하는 Device TCAD solver이며, Python은 parameter sweep, 결과 추출, DOE/Pareto 비교 및 최적 후보 선택을 수행하는 orchestration·analysis layer로 사용한다. 따라서 본 프로젝트의 ‘최적화’는 DEVSIM 내부의 자동 optimizer가 아니라, DEVSIM 결과를 기반으로 Python에서 수행하는 설계 탐색과 trade-off 분석을 의미한다.
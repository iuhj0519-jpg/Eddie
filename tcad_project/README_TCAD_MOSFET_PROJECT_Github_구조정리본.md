# TCAD Planar NMOS: HKMG and Multi-Spacer Optimization

최종 방향 정립: 2026-09-20. 이 문서는 프로젝트의 기준 계획서이다.
개발환경 구축 절차는 [DEVSIM_SETUP.md](docs/DEVSIM_SETUP.md)를 따른다.
현재는 프로젝트 구조 준비 단계이다. 소자 구현·DEVSIM 설치 성공·성능 개선은 아직 입증되지 않았다.

## 1. 목표와 범위

> DEVSIM을 이용하여 28 nm planar NMOS의 문헌 기반 HKMG 구조를 근사하고,
> EOT·effective gate work function·LDD·spacer가 SS, DIBL 및 Ion/Ioff에 미치는
> 개별 효과와 상호작용을 검증한다. 문헌 비교와 자체 대조실험의 개선율을 구분하고,
> 수치 수렴과 물리 모델의 한계를 함께 보고한다.

선정 논문은 최적화 개념과 구조 설계의 출발점이다. 논문의 수치·공정·추출 조건을
정확히 재현하거나 성능값에 맞추는 calibration은 필수 목표가 아니다.
핵심 결과는 **동일 모델·동일 추출법·통제된 조건에서 자체 baseline 대비 얻은 개선과 trade-off**이다.

핵심 범위:

- 1D capacitor/PN/MOSCAP과 2D planar NMOS의 물리·수치 검증
- long channel 검증에서 100 nm, 28 nm로 이어지는 scaling/SCE 분석
- SiO2 thickness, HfO2/SiO2 또는 HfO2/SiON stack의 층별 두께 탐색
- effective work-function을 통한 Vth 및 Ion/Ioff 제어
- 분석적 channel/LDD 도핑 profile
- 단일 SiO2 spacer 대비 SiON 단일·다층 spacer의 정전기 효과
- 작은 설계 공간에서의 Pareto 분석과 재현 가능한 Python workflow

선택 확장: La2O3 advanced stack, explicit poly-Si depletion, halo, 통계 변동,
quantum correction, 3D FinFET. 선택 과제는 핵심 프로젝트 완료를 지연시키지 않는다.

본 프로젝트는 device TCAD이다. 층 두께·재료·도핑 profile에 관한 설계 후보를 제시하며,
증착 시간·온도·가스 유량·implant/anneal 등의 제조 공정 레시피 자체를 최적화했다고 주장하지 않는다.

## 2. 문헌의 역할과 비교 원칙

개념 출처: [Xiao et al., arXiv:2409.15015v3](https://arxiv.org/abs/2409.15015v3).

논문의 Poly-Si/TiN/La2O3/HfO2/SiON/Si 구조에서 HKMG·LDD·multi-spacer 개념을 가져온다.
논문은 SiO2/Si3N4 multi-spacer를 사용한다. 본 프로젝트의 **SiON spacer는 독립적인 응용 설계**이다.
Gate 아래의 SiON interfacial layer와 gate 옆의 SiON spacer는 별도 영역·변수로 관리한다.

문헌의 SS=69.8 mV/dec, DIBL=30.5 mV/V는 참고값이며 PASS 기준이 아니다.
30.2% SS 개선은 참고문헌 [1]의 100 mV/dec, 약 89% DIBL 개선은 [14]의
279 mV/V를 기준으로 한다. 두 비교 대상은 다르며, 동일 조건의 자체 대조실험이 아니다.
[1] [Lee et al., DOI](https://doi.org/10.1109/ISNE.2014.6839328),
[14] [Kumar et al., DOI](https://doi.org/10.1109/ICOSEC49089.2020.9215330).
원 참고문헌의 소자·바이어스·추출 조건이 확인되지 않은 수치는 정량 우열 판정에 사용하지 않는다.

- 문헌 비교: 구조, 온도, 바이어스, 폭, 추출법, 사용 모델과 미공개 정보를 표에 명시한다.
- 자체 비교: 비교군 ID와 바뀐 변수, 고정 변수, baseline 값을 함께 저장한다.
- 모델 계수를 특정 후보의 성능을 높이기 위해 재보정하지 않는다.
- 향후 충분한 실측 데이터가 확보되면 독립 calibration/hold-out validation을 선택적으로 수행한다.
- 검증되지 않은 모델 결과는 정량적인 실제 제조 소자 예측으로 표현하지 않는다.

## 3. 물리 모델과 Poly-Si에서 HKMG로의 전환

### 3.1 Poly-Si/metal gate의 물리적 배경

고농도 poly-Si 도핑은 전도성을 높이고 gate Fermi level을 조정한다.
진공 준위 기준 일함수는 Phi = E_vac - E_F이므로 n+ 도핑은 일반적으로 일함수를
낮추는 방향, p+ 도핑은 높이는 방향이다. 모든 금속을 대표하는 하나의 일함수는 없다.

Poly-Si는 SiO2와의 공정·열적 호환성과 self-aligned 공정에 유리했지만,
유한한 poly depletion, dopant penetration 등의 한계가 있다.
High-k와의 조합에서는 계면 반응·Fermi-level pinning도 고려해야 한다.
HKMG는 이런 제약을 줄이고 적절한 effective work function을 확보하기 위한 접근이다.
단순히 SiO2 계면을 비슷하게 만들기 위해 일함수를 높인다고 설명하지 않는다.

기본 구현은 **effective work function을 명시한 이상적 전극**이다.
SiO2 baseline도 동일한 전극 모델을 사용하므로, 이를 실제 doped-poly 모델이라고 부르지 않는다.
TiN 이름이나 형상 추가 자체를 metal-gate 성능 개선의 증거로 사용하지 않는다.

선택 확장에서 poly-Si를 반도체 영역으로 풀고 doping sweep을 수행한다.
먼저 MOSCAP에서 poly depletion에 따른 capacitance 및 전압 분배를 검증한 뒤 NMOS에 적용한다.
같은 effective work function에서 poly/ideal-metal을 비교해야 depletion 효과를 구분할 수 있다.

배경 자료:
[Auburn TCAD 강의](https://www.eng.auburn.edu/~niuguof/elec6710dev/html/fundamental.html),
[Stanford MOS scaling 강의](https://web.stanford.edu/class/ee311/NOTES/PWong_BeyondMOS.pdf).

### 3.2 구현 전에 작성할 model specification

- Poisson + electron/hole continuity + drift-diffusion; 이산화와 Jacobian 생성 방식 기록
- 온도 기본값 300 K; nm 입력을 cm 내부 단위로 변환, doping cm^-3, mobility cm^2/(V s)
- 전류 원시 단위와 2D out-of-plane width 환산을 검증하여 A/um으로 출력
- long channel 학습: constant mobility와 비축퇴 통계부터 시작
- 28 nm 설계 비교 전: doping/field-dependent mobility, SRH,
  고농도 영역의 carrier statistics와 band-gap narrowing 필요성 검토·검증
- 모든 모델은 implemented / verified / omitted 상태와 파라미터 출처를 명시
- Gate boundary에 effective work function을 반영하는 식과 부호를 MOSCAP에서 검증
- S/D/body contact, 절연 경계, dielectric interface에서 potential 및 displacement 조건 명시
- 이상적인 기본 계면은 Qf=0, Dit=0; 이후 문헌 범위에 근거한 민감도 분석
- Gate tunneling, BTBT, impact ionization, self-heating, quantum confinement은 기본값에
  자동 포함되었다고 가정하지 않음; 누락된 누설 메커니즘을 명시
- Silicide는 기본적으로 ideal contact 가정 또는 명시적 series/contact resistance로 근사

28 nm의 DD 결과는 모델 가정하의 경향 분석이다. 메시 수렴이 모델 타당성을 보장하지 않는다.
고농도·극박막 영역에서 물리 모델이 부족하면 해당 결과를 탐색 결과로 표시한다.

## 4. 실행 순서와 단계별 산출물

기존 Phase 4의 문헌 수치 보정 의무를 없애고, 모델 구축 의존성에 맞춰 단계를 재번호화했다.

| Phase | 내용 | 핵심 산출물 |
|---|---|---|
| 0 | WSL2/Python/DEVSIM 환경 | import + 실제 capacitor solve, 버전 기록 |
| 1 | 물리 검증 및 model specification | capacitor/PN/MOSCAP 오차, 경계조건 |
| 2 | 공통 extraction library + 장채널 NMOS | 추출법 v1, 단위 테스트, I-V |
| 3 | 문헌 개념 정리 + 100 nm baseline | 입력값 출처·가정·누락 목록, 수렴 |
| 4A | SiO2 thickness scaling | Cox, SS/DIBL, 전계 |
| 4B | High-k/IL 층별 두께 + EOT | thickness DOE, matched-EOT 대조 |
| 4C | Effective work-function Vth 제어 | Vfb/Vth shift, Ion/Ioff |
| 4D | 단순화한 HKMG 통합 | 검증된 stack builder와 baseline |
| 5 | Channel/LDD profile | 접합 깊이·측방 길이·전계·저항 trade-off |
| 6 | Scaling/SCE + 28 nm 기준 소자 고정 | 100→28 nm, 전위 장벽, 기준 config |
| 7 | SiO2/SiON multi-spacer | 재료·층 순서·폭 대조실험 |
| 8 | 제한된 다변수 최적화 | feasible Pareto 후보와 fine-mesh 재검증 |
| 9 | 문헌 맥락 비교·문서화 | 자체 개선율, 한계, 재현 명령 |
| Optional | La2O3/poly depletion/halo/통계/quantum/FinFET | 독립 후속 보고서 |

모든 단계: 질문 → 가설 → 모델/가정 → 계산 → 수렴/추출 → 검증 → 해석 → 한계 → 기록.
필요한 부분 모델은 먼저 MOSCAP/long channel에서 검증한다.
초기 stack 탐색 후 28 nm에서도 대표점과 최종 후보를 다시 계산한다.
100 nm에서의 최적값이 28 nm에서도 최적이라고 가정하지 않는다.

## 5. Phase 1–3: 검증·baseline·추출법

### 5.1 기본 물리 검증

- 1D capacitor: C/A = epsilon/t, 선형 potential, 일정 electric field 검증
- 다층 capacitor: (C/A)^-1 = sum(t_i/epsilon_i), 각 층 전압 강하,
  계면 자유전하가 없을 때 displacement 연속성 검증
- PN: 비축퇴·급격 접합·평형에서 Vbi=(kBT/q) ln(NA ND/ni^2)
  및 depletion approximation 비교; 역바이어스에서는 Vbi+VR 사용
- Depletion edge 판정법을 명시하고 해석해의 근사 오차와 수치 오차를 구분
- MOSCAP: 처음에는 quasi-static C=dQg/dVg; Vfb, surface potential, Cox 검증
- High-frequency C-V는 별도 AC 모델·주파수·minority-carrier 응답 조건을 정의한 선택 실험

정상적인 log10 전류 기준 SS 근사:
SS = ln(10) (kBT/q) [1 + Cdep/Cox] (이상적 계면, 동일 면적 기준).
선정 논문 v3 식 (1)의 ln(10) 분모 표기를 구현에 복사하지 않는다.

### 5.2 long channel과 baseline

- 장채널 검증용 Lg=1 um를 초기 예시로 사용하고 square-law 근사의 적용 조건 확인
- 수치 개발용: Lg=100 nm, tox=5 nm, NA=1e16–1e17 cm^-3, NSD=1e19 cm^-3
- 위 값은 교육용 시작값이며 제조 공정값이나 보정된 최적값이 아님
- Body depth, S/D length, junction depth, LDD geometry, gate overlap도 config에 포함
- 계산 영역 크기를 늘려 body/contact 경계가 결과를 좌우하지 않는지 확인

### 5.3 프로젝트 공통 추출 규약

논문 재현 전용 모드는 만들지 않는다. 모든 설계 비교에 하나의 project extraction version을 사용한다.
아래는 개발 시작값이며 Phase 2 pilot에서 동작 구간·노이즈를 확인한 뒤 **설계 DOE 전에 고정**한다.

| 항목 | 프로젝트 기본 정의 |
|---|---|
| 온도·폭 | 300 K, 전류 A/um; 기준 구조 폭 1 um 환산 |
| VDD | 1.0 V |
| Body bias | VBS=0 V |
| Id-Vg | VDS=0.05 V, 1.0 V; 초기 VGS=-0.3~1.2 V |
| Vth | Id/W=1e-7 A/um constant current, log-current 보간, L 보정 없음 |
| SS | VDS=0.05 V; Id/W=1e-10~1e-8 A/um에서 log10(Id/W) 대 Vg 회귀 |
| DIBL | [Vth(0.05)-Vth(1.0)]/0.95, mV/V로 변환 |
| Ion | VGS=VDS=VDD |
| Ioff | VGS=0, VDS=VDD |
| gm, gds | 각각 고정 VDS, 고정 VGS의 수치 미분; bias step 민감도 확인 |

SS는 최소 10점 및 2 decades 확보를 기본으로 하되 강반전·누설 바닥 혼입 여부와
회귀 잔차를 확인한다. 창을 충족하지 못하면 invalid로 표시하고 임의의 다른 창으로 바꾸지 않는다.
바이어스 범위 밖의 Vth를 외삽하지 않는다. 일관된 규칙으로 재계산하거나 추출 불가를 기록한다.
규약 변경 시 version을 올리고 영향을 받는 비교군을 모두 다시 추출한다.

Width-normalized constant current도 길이에 따른 추출 의존성이 있으므로,
SCE 해석은 barrier potential 및 선택적인 다른 Vth 추출법 cross-check와 함께 수행한다.
도구 전류 부호 규약을 검증한 뒤 일관되게 처리하고, 0/NaN/실패값을 임의 floor로 바꾸지 않는다.

함수: extract_vth, extract_ss, extract_dibl, extract_ion, extract_ioff, extract_gm, extract_gds.
알려진 기울기의 synthetic I-V, 단위 환산, 비단조 곡선, 범위 미달, solver 실패 처리 테스트 포함.
I-V만으로 추정한 mobility는 apparent metric으로 명시; full BSIM 추출은 범위 밖이다.

## 6. Phase 4: Gate-stack engineering

### 6.1 SiO2 두께

예시 tox=5, 4, 3, 2, 1.5 nm. 초기 단계에서는 doping·work function·geometry를 고정한다.
Cox, Vth, SS, DIBL, Ion/Ioff, oxide electric field, surface potential을 비교한다.
Gate-tunneling 모델이 없으면 얇아질수록 좋아지는 경계해가 나올 수 있다.
이를 실제 최적 산화막 두께나 leakage/reliability의 입증으로 해석하지 않는다.

### 6.2 High-k stack의 두께 탐색과 EOT

기본 stack (gate에서 channel 방향): ideal electrode / HfO2 / IL / Si.
IL은 SiO2 또는 SiON. Al2O3는 선택적인 재료 비교이다.

**설계 입력은 층별 실제 두께**, EOT는 계산·비교를 위한 파생값이다.

EOT = sum_i[t_i * 3.9/k_i]
Cox/A = epsilon0 * 3.9/EOT

재료 유전율, 온도, 조성, 두께와 증착/열처리 조건을 문헌에서 조사하여
references/materials/materials.csv에 source URL/DOI, 값, 단위, 범위, 가정/측정 여부를 기록한다.
SiON의 k를 보편적인 상수로 취급하지 않는다.
재료 k와 물리 두께와 EOT를 모두 독립 변수로 지정하지 않는다.

학습용 pilot 예시: t_IL=0.5, 0.8, 1.0, 1.2 nm; t_HfO2=2, 3, 4, 5 nm.
이 범위는 검증된 공정 window가 아니다. 문헌의 구현 가능 범위와 모델 타당성으로
DOE 전에 수정·고정하고, 배제 이유를 기록한다.
공정 자료가 부족하면 "가정한 두께 범위 내 electrostatic optimum"으로 결과를 제한한다.

실험은 두 종류로 분리한다.

1. Thickness DOE: 층 두께를 바꾸고 EOT·Cox·SS/DIBL·Ion/Ioff·각 층 전계를 산출한다.
2. Matched-EOT 대조: 같은 EOT에서 SiO2와 stack을 비교해 재료/물리 두께/fringing 효과를 조사한다.

Matched EOT는 최적화의 제한 조건이 아니라 원인 분리용 실험이다.
같은 EOT의 1D ideal capacitance는 유사해야 하며, high-k가 항상 SS/DIBL을 개선할 필요는 없다.
2D short-channel에서는 fringing 및 spacer coupling으로 차이가 날 수 있다.

층별 최소 두께, 허용 전계의 문헌 근거, 유효 모델 범위를 명시한다.
검증된 gate-leakage 모델이 없으면 Ig와 수명은 최적화 목적에 넣지 않는다.
제조 feasibility와 장기 신뢰성은 별도 검증 과제로 남긴다.

### 6.3 Effective work-function Vth 제어

재료·두께·도핑을 고정하고 Phi_eff를 sweep한다.
Pilot 예시 4.2–4.8 eV; 실제 TiN 공정에서 전 범위가 구현된다는 뜻이 아니다.
문헌 기반 effective 값의 범위를 사용하거나 이상적 sensitivity sweep임을 표시한다.

목표: Vfb/Vth shift 및 고정 VDD에서 Ion/Ioff trade-off.
이상적인 조건에서 Phi_eff 변화는 주로 곡선을 수평 이동시키므로,
SS/DIBL 개선을 반드시 요구하지 않는다. 관측 변화는 동일 추출 창과 carrier 상태를 확인한다.
TiN 두께 변화가 Phi_eff를 자동으로 바꾸는 모델이라고 가정하지 않는다.

### 6.4 통합 비교군

| ID | Gate dielectric | 전극 |
|---|---|---|
| G0 | SiO2 | 고정 Phi_eff의 ideal electrode |
| G1 | HfO2/SiO2 IL | G0와 같은 Phi_eff |
| G2 | HfO2/SiON IL | G0와 같은 Phi_eff |
| G3 | 선택된 stack | Phi_eff sweep |

두께 DOE, matched-EOT, 고정 stack의 Phi_eff sweep 결과를 구분한다.
G3의 Vth가 바뀐 경우 Ion/Ioff 개선을 전부 electrostatic control 향상으로 설명하지 않는다.
필요하면 별도의 matched-Vth 비교를 추가하되 Phi_eff 조정량을 명시한다.

### 6.5 Optional advanced stack

Poly-Si/TiN/La2O3/HfO2/SiON/Si를 문헌 기반 확장으로 다룬다.
La2O3의 유전 두께와 dipole-induced shift는 별개이다.
명시적 layer, 유효 work-function shift, charge/dipole boundary 중 구현을 기록하고
동일 효과를 중복 계상하지 않는다. 단일 fixed charge는 dipole과 일반적으로 동일하지 않다.
계면 화학, 원자적 결합, 실제 증착 공정 재현은 주장하지 않는다.

## 7. Phase 5–6: Doping, scaling, 28 nm 기준 고정

Channel/LDD는 analytical profile로 구현한다.
Peak/plateau concentration, 깊이, lateral spread, junction criterion, LDD 길이를 기록한다.
Implant dose를 균일 농도로 직접 대체하지 않는다.

- NA sweep: Vth, depletion width, SS/DIBL, mobility trade-off
- LDD: abrupt S/D와 비교해 전계, series-resistance 영향, Ion/Ioff 분석
- 먼저 baseline에 필요한 nominal profile을 고정한 뒤 한 변수씩 변화
- Halo는 선택 확장; implant process simulation이라고 부르지 않음

Gate-length 예시: 100, 80, 60, 50, 40, 30, **28 nm**.
20 nm는 모델 타당성 검토 후 선택한다.
Lg만 바꾸는 scaling 실험과 stack/LDD까지 함께 바꾸는 재설계는 구분한다.
길이에 따른 junction/gate 상대 좌표 생성 규칙을 고정한다.

SS/DIBL/Vth/Ion/Ioff 및 source-channel conduction-band barrier를 비교한다.
VDS 증가에 따른 장벽 변화와 공간 potential/electric field를 함께 제시한다.
28 nm에서 수치 및 model review를 완료한 config를 **B28**로 고정한다.

## 8. Phase 7: SiO2 대비 SiON Multi-Spacer

핵심 질문: 같은 외곽 형상과 도핑에서 spacer의 SiON 도입·배치가
drain/gate fringing과 channel barrier에 어떤 영향을 주는가?

표의 순서는 **gate sidewall에서 S/D 쪽으로** 읽는다.
처음에는 source/drain에 대칭으로 적용한다.

| ID | Spacer 구성 | 목적 |
|---|---|---|
| S0 | SiO2 단일층 | 교재형 baseline |
| S1 | SiON 단일층 | 조성/k 변화의 대조군 |
| S2 | SiO2 / SiON | gate 인접 저-k, 바깥 SiON |
| S3 | SiON / SiO2 | 층 순서 반전 |
| S4 | SiO2 / SiON / SiO2 | 3층 spacer |
| S5 (선택) | SiO2 / Si3N4 / SiO2 | 논문의 nitride 계열과 비교 |

첫 실험은 전체 폭·높이·외곽 형상·gate overlap·접합 위치·도핑을 동일하게 유지한다.
Pilot 전체 폭 10 nm에서 S2/S3=5+5 nm, S4=2.5+5+2.5 nm처럼 시작할 수 있다.
폭·비율은 교육용 제안이며 문헌 및 메시 분해능으로 타당성을 확인한다.
이후 전체 폭 예시 5/10/15 nm 및 내부 층 비율을 별도 sweep한다.
재료의 lateral 폭 합은 항상 total width와 일치해야 한다.

SiON 조성에 따른 k 범위를 출처와 함께 입력한다.
기본 실험에서는 dielectric permittivity만 반영하고,
stress, trap passivation, 식각 선택비, diffusion barrier 개선은 계산한 것으로 주장하지 않는다.
다층화가 반드시 우수하다고 가정하지 않는다.

측정: Vth, SS, DIBL, Ion/Ioff, 장벽 위치·높이, gate-edge/drain 전계.
가능하면 AC Cgd/Cgs를 추가해 leakage 개선과 capacitance 증가의 trade-off를 확인한다.
AC 검증 이전에는 switching-speed 개선을 주장하지 않는다.

후속 coupling 실험에서만 LDD 길이/접합 위치를 함께 바꾼다.
이는 spacer가 implant mask 역할을 하는 공정에서 착안한 **기하·도핑 공동설계**이며,
spacer의 순수 dielectric 효과와 별도 표에 보고한다.
이상적인 날카로운 모서리의 peak E가 mesh-dependent이면 고정 거리의 값 또는
명시한 영역 평균을 사용하고 해당 정의를 유지한다.

## 9. Phase 8: 최적화와 제한 조건

처음에는 B28을 기준으로 최대 2–3개 변수만 결합한다.

1. t_IL × t_HfO2: stack thickness DOE
2. 선택된 stack에서 Phi_eff: Vth/Ion/Ioff 조정
3. 선택된 spacer 구조에서 폭 또는 층 비율 × LDD 길이
4. 필요할 때만 재료 조성 또는 도핑을 추가

독립 sweep 결과를 바탕으로 작은 factorial DOE를 사용하고 상호작용을 분석한다.
온도, 바이어스, 모델 계수, 추출법, contact, 기준 폭을 고정한다.
전체 대조군과 모델 coefficient set ID를 기록한다.

목표: Ion 최대화, Ioff/SS/DIBL 최소화의 feasible Pareto set.
개발용 제약 예시: Vth=0.2–0.5 V, Ioff/W<=1e-8 A/um,
SS<=100 mV/dec, DIBL<=100 mV/V.
이는 산업 표준·논문 재현 기준이 아닌 초기 설계 목표이다.
Pilot 후 이유를 기록해 DOE 전에 고정하며, 결과를 통과시키려고 사후 완화하지 않는다.

두께/전계/geometry/model-validity 제약과 solver 실패를 함께 적용한다.
모든 후보가 infeasible이면 이를 결과로 보고하고 원인을 분석한다.
실패점을 낮은 Ioff나 유리한 목적값으로 처리하지 않는다.

개선율은 지표별 own baseline을 분모로 계산한다.
전체 통합 개선은 B28 대비, 요소별 효과는 해당 실험의 통제 대조군 대비로 표기한다.
해당 baseline 수치·조건을 함께 제공한다.
동점 수준의 차이는 mesh·bias-step 오차보다 충분히 큰지 확인한다.

계산 예산은 대표 I-V sweep의 실제 시간·메모리를 측정한 후 정한다.
선별은 검증된 중간 mesh, 최종 후보는 fine mesh와 작은 bias step으로 재계산한다.

## 10. Numerical Quality Gate

| 항목 | 초기 기준 |
|---|---|
| 1D/다층 capacitor | 해석 C 오차 <1%, displacement/charge balance |
| PN (적용 가능한 해석 조건) | Vbi <2%, depletion width <5% |
| MOSCAP | Cox <3%, Vfb/표면전위/계면 조건 검증 |
| Mesh 3단계 | medium–fine Ion <2%, Vth <5 mV, SS <2% |
| 28 nm 핵심 지표 | DIBL 차이 <5 mV/V, log10(Ioff/W) 차이 <0.1 decade |
| Bias-step | 절반 step 재계산에서 지표의 안정성 확인 |
| Solver | 필수 bias 전체 수렴, residual/update/iteration 기록, NaN/Inf 없음 |
| 전류 보존 | 모든 terminal을 포함한 sum(I)=0 검사; 상대·절대 허용오차 기록 |
| 추출 | 공통 규약, 합성곡선·실패처리·단위 테스트 통과 |
| 최종 후보 | fine mesh, 영역 크기·수치 오차와 효과 크기 비교 |

전류 보존은 near-zero에서 상대오차만 사용하지 않는다.
예: |sum I| <= I_abs_tol + 1e-4 * sum|I|. I_abs_tol은 width-normalized solver
noise floor를 측정해 고정하고, Ioff를 구분할 수 있을 만큼 작은지 확인한다.
전하 보존은 semiconductor 공간전하·계면전하·gate/contact charge와 경계 flux를 함께 고려한다.

숫자는 프로젝트 quality gate이며 보편적인 산업 기준이 아니다.
Coarse→medium→fine 추세를 보며 fine mesh를 절대 정답으로 부르지 않는다.
각 새로운 stack/spacer의 얇은 층·계면·접합·gate edge를 재검증한다.

## 11. 재현성·폴더·문서 관리

아래 폴더 구조를 사용한다. Git은 빈 폴더를 저장하지 않으므로 미구현 폴더에는
`.gitkeep`만 둔다. 시뮬레이션 파일은 해당 Phase에서 구현하며, 폴더 존재가 구현 완료를 뜻하지 않는다.

폴더는 **코드 기능(`src/`)**, **검증(`validation/`)**, **실험(`experiments/`)**, **데이터(`data/`)**,
**문헌·공식 구현 참고(`references/`)**를 분리한다. Phase 4의 gate-stack engineering은 하나의
실험군으로 묶고, 내부에서 SiO2 → High-k/EOT → Metal Gate → HKMG → Advanced Stack 순으로
세분화한다. 선택 확장인 halo, variability, FinFET, quantum은 핵심 프로젝트와 분리된 폴더로 유지한다.

```text
TCAD_Project/
├── README.md
├── README_TCAD_MOSFET_PROJECT_Github_구조정리본.md
├── CHANGELOG.md
├── requirements.in
├── .gitignore
│
├── src/
│   ├── device/
│   │   ├── capacitor.py
│   │   ├── pn_junction.py
│   │   ├── moscap.py
│   │   ├── nmos_planar.py
│   │   └── finfet.py                  # 선택 확장
│   │
│   ├── physics/
│   │   ├── materials.py
│   │   ├── mobility.py
│   │   ├── doping.py
│   │   └── srh.py                     # bulk 생성·재결합식 및 연속방정식 source/Jacobian
│   │
│   ├── solver/
│   │   ├── dc_solver.py
│   │   └── convergence.py
│   │
│   ├── extraction/
│   │   ├── capacitance.py             # Q–V 데이터의 기울기·국소 dQ/dV 추출
│   │   ├── iv_metrics.py
│   │   ├── compact_params.py
│   │   └── statistics.py
│   │
│   └── utils/
│
├── configs/
│   ├── phase1/                        # capacitor/PN 등 기초 검증 설정
│   ├── baseline/
│   ├── gate_stack/
│   ├── doping/
│   ├── spacer/
│   └── optimization/
│
├── validation/
│   ├── analytic/
│   │   ├── capacitor/
│   │   ├── pn_junction/
│   │   └── moscap/
│   │
│   ├── literature/
│   │   └── calibration_reference/
│   │
│   └── regression/
│
├── experiments/
│   ├── 01_baseline/
│   ├── 02_gate_length/
│   │
│   ├── 03_gate_stack/
│   │   ├── 01_sio2_scaling/
│   │   ├── 02_high_k_eot/
│   │   ├── 03_metal_gate/
│   │   ├── 04_hkmg/
│   │   └── 05_advanced_stack/         # 선택 확장
│   │
│   ├── 04_channel_doping/
│   ├── 05_ldd/
│   ├── 06_spacer/
│   ├── 07_optimization/
│   │
│   ├── 08_halo/                       # 선택 확장
│   ├── 09_variability/                # 선택 확장
│   ├── 10_finfet/                     # 선택 확장
│   └── 11_quantum/                    # 선택 확장
│
├── tests/
│   ├── unit/
│   │   └── phase1/
│   └── regression/
│       └── phase1/
│
├── data/
│   ├── raw/
│   │   └── phase1/                    # 주제/run_NNN/ (필요 시 pilot/extension)
│   └── processed/
│
├── figures/
├── notebooks/
│
├── references/
│   ├── papers/
│   ├── materials/
│   └── devsim/
│
└── docs/
    ├── DEVSIM_SETUP.md
    ├── GIT_WORKFLOW.md
    ├── methodology.md
    ├── extraction_methodology.md
    ├── experiment_log.md
    └── limitations.md
```

### 11.1 Phase–폴더 대응

| README 실행 단계 | 주요 실험 폴더 |
|---|---|
| Phase 1–3: 검증·baseline·추출 | `validation/`, `experiments/01_baseline/` |
| Phase 4A: SiO2 thickness | `experiments/03_gate_stack/01_sio2_scaling/` |
| Phase 4B: High-k / EOT | `experiments/03_gate_stack/02_high_k_eot/` |
| Phase 4C: work function | `experiments/03_gate_stack/03_metal_gate/` |
| Phase 4D: HKMG | `experiments/03_gate_stack/04_hkmg/` |
| Optional advanced stack | `experiments/03_gate_stack/05_advanced_stack/` |
| Phase 5: channel/LDD | `experiments/04_channel_doping/`, `experiments/05_ldd/` |
| Phase 6: scaling/SCE | `experiments/02_gate_length/` |
| Phase 7: spacer | `experiments/06_spacer/` |
| Phase 8: optimization | `experiments/07_optimization/` |
| Optional extensions | `experiments/08_halo/`, `09_variability/`, `10_finfet/`, `11_quantum/` |

이 구조에서 `src/`는 여러 실험에서 재사용되는 구현 코드만 보관한다. 개별 sweep 조건,
실험별 실행 스크립트, 결과 요약은 해당 `experiments/` 폴더에 둔다. 동일한 물리 모델이나
추출 코드를 실험 폴더마다 복제하지 않는다.

experiment 번호는 폴더 식별자이며 Phase 실행 순서는 4절을 따른다.
`03_gate_stack/` 내부 번호는 Phase 4A–4D와 선택 확장 4E에 대응한다.
`08_halo`, `09_variability`, `10_finfet`, `11_quantum`은 선택 확장 폴더이다.

실험별 저장: config, run ID, timestamp, Git commit/dirty status, model/extraction version,
Python/DEVSIM/Gmsh/dependency 버전, mesh 요약, convergence.csv, metrics.csv, raw I-V.
난수 실험에는 seed와 분포/상관길이를 추가한다.

작은 baseline I-V, 모든 config·추출 코드·출처·핵심 표는 Git에 보관한다.
미구현 실험 폴더는 `.gitkeep`만 둔다. 구현이 시작되면 상세 가이드·조건·해석·실험 기록은
Phase 내 소자별 단일 문서(예: PHASE1_SIO2_CAPACITOR.md, PHASE1_PN_JUNCTION.md)를 기준으로 관리하고,
같은 소자의 실행 가이드·각 sweep·결과를 별도 문서로 나누지 않는다. 실험 폴더의 README 또는 run script에는
실행 방법과 해당 문서의 경로·링크만 안내하여 상세 기록의 중복 관리를 피한다.
위 트리는 구현 예정 파일도 포함하는 배치 기준이다. 새 공통 모듈을 구현하면 이 구성도에도 반영하며,
파일의 물리량 이름이 아니라 실제 책임으로 위치를 결정한다.

- `src/device/`: 구조·접촉·mesh와 물리 모델의 결합. PN은 SRH 활성 여부와 관계없이 `pn_junction.py` 하나를 사용한다.
- `src/physics/`: 지배방정식에 들어가는 물리 법칙과 계수·source/Jacobian. `srh.py`는 생성·재결합률을 계산하고 연속방정식에 결합하므로 여기에 둔다.
- `src/extraction/`: 계산된 데이터에서 지표를 추출. 현재 `capacitance.py`의 `extract_qv()`는 입력 Q–V 배열의 회귀 기울기·국소 dQ/dV·잔차를 구하므로 여기에 유지한다. 소자의 유전율이나 Poisson 방정식을 정의하는 모듈이 아니다.
- `validation/analytic/<device>/`: 실행 조건 조합·검증 판정·CSV/PNG/VTK 출력. SRH의 실행·전류 보존 판정은 `validation/analytic/pn_junction/run_srh.py`가 담당한다.

대형 raw mesh/field는 제외할 수 있지만 생성 명령·checksum·보관 위치를 기록한다.
문헌 PDF 배포 권한을 확인하고, 권한이 불명확하면 링크·서지정보만 공개한다.
직접 의존성과 설치된 환경 snapshot을 구분한다. 같은 이름의 계획서를 중복 편집하지 않는다.

## 12. 완료 조건과 후속 연구

다음을 모두 충족하면 핵심 프로젝트 완료:

- [ ] 환경에서 import와 실제 solver smoke test 성공
- [ ] 기초 물리, extraction, mesh/solver 검증 완료
- [ ] 자체 28 nm B28 및 비교 규약 고정
- [ ] High-k stack의 층별 두께 탐색과 matched-EOT 비교
- [ ] Effective work-function에 따른 Vth/Ion/Ioff 분석
- [ ] Channel/LDD 영향 및 scaling/SCE 공간 증거
- [ ] SiO2 대비 SiON 단일/다층 spacer 대조와 층 순서 비교
- [ ] 적어도 한 개의 작은 다변수 DOE와 trade-off/feasibility 분석
- [ ] 개선 여부와 무관하게 결과·수치 오차·모델 한계 보고
- [ ] 주요 실험의 재실행 명령과 입력·환경 기록 제공

문헌 수치 일치, 실측 calibration, FinFET, full process recipe는 완료 조건이 아니다.
Quantum/통계/advanced stack의 선택 여부와 이유를 최종 보고서에 명시한다.

통계 확장: 연속 도핑 perturbation을 atomistic RDF라고 부르지 않는다.
표본 수를 늘리며 통계량과 신뢰구간 수렴을 확인한다.
FinFET 확장: 3D 구현·Weff·EOT·온도·바이어스·Vth/contact/model 비교 조건을 정의한다.
Density-gradient는 MOSCAP에서 먼저 검증하고 classical DD와 비교한다.

## 13. 누설·터널링·후속 신뢰성 검증 및 ParaView 운영 방침

이 절은 후속 구현·검증 방침이며, 모델 구현 완료를 의미하지 않는다.
4절의 Phase 순서와 11절의 Git 구조를 유지하고, 필요한 모델을 단순 소자에서 검증한 뒤 재사용한다.
모델 상태·파라미터 기록은 3.2절, 수치 검증 기준은 10절을 따른다.
아래에서는 누설·신뢰성 모델의 도입 조건과 시각화 운영에 특화된 절차를 정한다.

### 13.1 단계별 물리 모델 도입

| 단계 | 우선 검증 | 후속 도입 조건 |
|---|---|---|
| Capacitor | 단층·다층 정전기, C/Q/V/E, 계면 조건 | 현 단계에서 누설·절연파괴를 필수로 추가하지 않음 |
| PN | 평형 전위·공핍층, 순방향 I–V, 역방향 전류 | SRH 생성·재결합 검증 후, 고전계 역바이어스가 대상일 때 avalanche·BTBT 검토 |
| MOSCAP | 축적·공핍·반전, C–V, 층별 전압·전계 | Gate tunneling 및 필요 시 계면·산화막 트랩을 독립적으로 검증 |
| Phase 2 장채널 MOSFET | I–V, 전류 보존, Vth·SS·Ion/Ioff 추출 | 3.2절의 constant mobility·비축퇴 통계 baseline부터 시작하고 SRH·추가 이동도·누설 모델은 개별 검증 후 통합 |
| 후속 gate-stack 최적화 | 두께·EOT·성능·전계 trade-off | 검증된 gate leakage와 문헌 기반 제한 조건을 갖춘 경우 Ig까지 평가 |
| 후속 신뢰성 연구 | 시간·온도·스트레스에 따른 열화 | 목적별 TDDB·BTI·HCI 모델 및 대응 데이터 확보 후 별도 검증 |

PN의 접합 항복과 gate 산화막의 절연파괴는 다른 현상이다.
산화막이 없는 기본 PN에 gate 절연파괴 모델을 추가하지 않는다.
SRH, avalanche, BTBT, tunneling을 한꺼번에 켜지 않고 모델별 효과와 수치 수렴을 분리해 검증한다.

### 13.2 터널링·누설 모델의 검증 절차

1. 기존 정전기·수송 baseline과 추출 규약을 먼저 고정한다.
2. 재료·물리 두께·전압·온도 범위에 맞는 모델을 선택한다.
3. 장벽 높이, 밴드 정렬, 터널링 유효질량, 필요한 트랩 파라미터 등의 출처·단위·가정을 기록한다.
4. 단층 MOSCAP의 단순 조건에서 검증한 뒤 SiO2/HfO2 다층으로 확장한다.
5. 10절의 수치 검증 기준을 적용하고, 누설의 전압·물리 두께 의존성을 해당 모델의 해석 근사 또는 기준 데이터와 비교한다.
6. 검증된 물리 구현을 MOSFET에 재사용하고, 모델 활성화 전후의 변화와 유효 범위를 기록한다.

재료 이름이나 상대 유전율만으로 터널링 전류가 결정되지 않는다.
다층 장벽은 층별 물리 두께와 물성을 사용하며, EOT 하나로 단순 대체하지 않는다.
사후 계산한 누설 추정과 연속방정식·접촉 전류에 자기일관적으로 결합한 모델을 구분한다.
공식 구현 사례가 있어도 현재 프로젝트에 자동 적용되거나 검증된 것으로 간주하지 않는다.

MOSFET에서는 정의된 OFF 조건의 drain 전류 Ioff, gate 전류 Ig,
접합 누설 및 필요 시 BTBT/GIDL 기여를 구분한다.
독립적으로 분리 추출할 수 없는 성분을 임의로 나누거나 중복 합산하지 않는다.
비교 조건과 실패 처리 원칙은 2·5.3·9·10절을 따른다.

### 13.3 최적 두께와 신뢰성 주장의 범위

전계 제한 조건 확인, 항복 전압 계산, 장기 수명 예측은 서로 다른 검증이다.
최대 전계가 기준 이하이거나 DC solve가 수렴했다는 사실만으로 절연파괴·수명을 검증했다고 하지 않는다.
TDDB 등에는 시간·온도·스트레스 의존성 및 통계·면적 효과에 맞는 모델과 검증 데이터가 필요하다.

최적 두께·Ig·신뢰성 주장의 범위는 6.1·6.2절을 따른다.
충분한 스트레스 데이터와 모델 검증을 확보한 경우에만 장기 신뢰성 연구를 별도로 수행한다.
이는 12절의 핵심 완료 조건에 수명 예측을 일괄 의무화하는 것이 아니며,
결과·한계의 최종 보고 기준도 12절을 따른다.

### 13.4 소자별 Python·ParaView 분석 역할

고정 도핑 device TCAD에서 bias에 따라 주로 변하는 것은 전자·정공 농도,
공간전하, 전위, 전계이며 도핑 원자 분포 자체가 이동하는 것은 아니다.
NetDoping과 n/p를 구분하고, 공간전하는 이온화 도핑을 포함한
rho=q(p-n+ND_plus-NA_minus)로 정의한다.

| 소자 | Python 정량 그래프 | ParaView 활용 |
|---|---|---|
| 1D PN | 위치별 n/p/rho/전위/전계, I–V, 공핍층 검증 | 도핑·공핍 영역과 전하 분포의 대응 확인, 출력 체계 검증 |
| 1D MOSCAP | C–V, 표면전위, 깊이별 carrier 분포 | 축적·공핍·반전 및 재료 영역 확인 |
| 2D MOSFET | I–V, Vth·SS·DIBL·Ion/Ioff 등 | 채널 형성, 전위 장벽, drain/gate 전계, 전류 경로 |

PN·MOSCAP은 Python 중심에 ParaView를 보조로 사용하고, 2D MOSFET은 두 도구를 함께 사용한다.
1D 선 mesh의 표시·필드 읽기를 먼저 확인하며, 시각화 목적으로 2D 분포를 계산한 것처럼 표현하지 않는다.
농도는 필요 시 로그 스케일을 사용하되 부호가 있는 NetDoping·rho에는 무분별하게 로그를 적용하지 않는다.

### 13.5 기존 Git 구조 안의 출력 코드 배치

별도 paraview/ 같은 최상위 또는 도구 전용 폴더를 추가하지 않는다.
11절에 정의된 소자별 validation/analytic 하위 경로를 사용하며 아래 파일명은 후속 구현 배치안이다.

```text
validation/analytic/
├── capacitor/
│   ├── run_capacitor.py
│   ├── run_voltage.py
│   └── run_thickness.py
├── pn_junction/
│   ├── run_pn_junction.py
│   └── export_vtm.py
└── moscap/
    ├── run_moscap.py
    └── export_vtm.py
```

소자·물리 모델의 배치와 재사용 원칙은 11절을 따른다. 출력 코드의 추가 역할은 다음과 같다.

- run_*.py: 실험 실행·검증·CSV·Python PNG 출력.
- export_vtm.py: 같은 계산 상태의 ParaView 출력만 담당하며 별도 solver를 복제하지 않는다.
- src/utils/: 여러 exporter의 공통 처리가 필요할 경우 기존 위치에 공통 함수 배치.
- MOSFET 실험별 실행·export 호출: 11절의 해당 실험 경로 사용. 별도의 도구 전용 실험 트리를 만들지 않는다.
- data/raw/phase*/주제/run_*/: 계산 결과와 VTK 파일을 같은 실험 단위로 보관.
- tests/unit/phase*/ 및 tests/regression/phase*/: 출력 형식·단위 검사와 실제 solve/export 재현 검증 구분.

실험 주제는 하나의 주제 폴더로 관리하며, 상세 기록의 기준 문서와 링크 운영은 11절을 따른다.
PNG 생성기와 VTM exporter가 서로 다른 bias를 다시 계산하지 않고 동일한 수렴 상태를 공유한다.

### 13.6 VTM 출력·보존·검증 규칙

DEVSIM의 write_devices(type="vtk")를 기본 후보로 사용한다.
실제 1D/2D mesh와 필요한 필드의 출력 가능 여부는 해당 소자의 최초 smoke test에서 확인한다.
VTM은 영역별 VTU를 참조하므로 VTM만 복사하거나 Git에 추가하지 않는다.
생성되는 관련 파일과 상대 경로를 함께 보존하고 Windows/WSL 이동 후 다시 읽기를 확인한다.

1. 수렴 완료 후 device 삭제 전에 출력하거나, 복원 가능한 mesh·state를 저장한 뒤 출력한다.
2. 좌표·농도·전계·전류의 단위를 명시한다. 2D 전류의 폭 환산과 전류 밀도를 구분한다.
3. CSV·PNG·VTK의 run ID, bias, mesh 및 물리 모델 조건을 일치시킨다.
4. 전체 sweep의 정량 결과는 보존하되 VTK는 평형·대표 순방향/역방향·OFF/ON 등 명시한 대표점부터 출력한다.
5. 실패 상태는 정상 결과와 구분한다. bias 순서를 물리적인 과도 시간으로 오인하지 않게 표시한다.
6. 내보내기 과정의 edge-to-node 보간과 계면 양쪽 값을 확인한다.
   peak E·전류 보존·계면 jump의 판정은 보간된 그림이 아니라 원시 수치값으로 수행한다.
7. Git 추적·대형 결과 보관은 11절을 따른다. VTK를 선택적으로 추적할 때도
   VTM이 참조하는 VTU가 누락되지 않았는지 확인한다.

PN의 다음 실행 순서는 평형 해석 검증 → Python 그래프 → 동일 상태의 VTM 읽기 검증 →
순·역방향 sweep 및 SRH 검증으로 한다. 고전계 항복과 추가 누설 모델은 그 이후에 판단한다.

참고:

- [DEVSIM VTK/ParaView 출력 및 보간 설명](https://devsim.net/visualization.html)
- [DEVSIM avalanche 모델 구현 사례](https://devsim.com/avalanche-modeling/)
- [NIST: gate oxide 신뢰성의 물리 모델·통계·평가](https://www.nist.gov/publications/ultra-thin-gate-oxide-reliability-physical-models-statistics-and-characterization)

## 14. 지금 시작할 일

처음 시작하는 경우 [개발환경 구축 가이드](docs/DEVSIM_SETUP.md)의 Phase 0 이후
1D capacitor와 다층 capacitor를 검증한다.
Capacitor 검증을 마친 현재의 후속 단계는 13.6절의 PN 검증·시각화이며,
이후 MOSCAP 검증을 거쳐 Phase 2 장채널 MOSFET으로 진행한다.
환경 및 기초 검증이 완료되기 전까지 28 nm 최적화 결과를 생산 단계로 진행하지 않는다.

## 15. 공식 GitHub 구현 참고 자료

| 자료 | 링크 | 사용 범위 |
|---|---|---|
| DEVSIM 본체 | [devsim/devsim](https://github.com/devsim/devsim) | 설치, capacitor/diode, meshing, contact, Poisson/DD |
| 공식 조직 | [devsim](https://github.com/devsim) | 관련 공식 프로젝트 탐색 |
| 문서 | [devsim_documentation](https://github.com/devsim/devsim_documentation) | API, equation/node/edge model, solver; [온라인 매뉴얼](https://devsim.net/) |
| 양자보정 | [devsim_density_gradient](https://github.com/devsim/devsim_density_gradient) | Classical MOSCAP 검증 이후 선택 확장 |
| 3D 예제 | [devsim_3dmos](https://github.com/devsim/devsim_3dmos) | 후속 3D 구현 참고; 완성된 FinFET 템플릿으로 가정하지 않음 |

API·구현은 공식 문서와 예제를 우선하고, 물리 타당성은 교재 해석식 및 원 논문으로 검증한다.
코드를 가져올 때 governing equations, units, boundary conditions, material parameters,
mesh, solver settings, 적용 가능한 device regime을 확인한다.
저장소 URL, 사용 commit/tag, 참조 파일, 라이선스/저작권 표시를 references/에 기록한다.
GitHub 예제의 다운로드와 실행용 DEVSIM pip 패키지 설치는 별도 작업이다.

## 16. Project_Git 브랜치 운영

프로젝트 저장소는 [iuhj0519-jpg/Eddie](https://github.com/iuhj0519-jpg/Eddie)이다.
통합 대상인 Project_Git 브랜치를 기준으로 전용 tcad 브랜치를 만들고,
기존 프로젝트와 경로 충돌을 피하기 위해 TCAD_Project/ 하위에 이 구조를 구성한다.
실제 저장소의 기존 규칙이나 배치가 다르면 먼저 확인하여 그 규칙에 맞춘다.

- 개발·검증·중간 commit은 tcad 브랜치에서 수행한다.
- 분기 기준과 최종 통합 대상은 Project_Git이다. 저장소 기본 브랜치 main과 구분한다.
- 기존 파일과 다른 작업자의 변경을 보존하고 force push를 하지 않는다.
- 완료 후 Project_Git 대상 diff/테스트/문서를 확인하고 PR 또는 merge로 통합한다.
- 현재 준비 작업에서 완료 후의 merge까지 미리 수행하지 않는다.
- venv, 대형 raw 결과, 임시 파일과 제3자 논문 PDF는 초기 commit에서 제외한다.

[Git 운영 절차](docs/GIT_WORKFLOW.md)를 따른다.

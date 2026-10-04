# TCAD HKMG / SiON Multi-Spacer Project

DEVSIM을 이용해 planar NMOS의 gate stack, effective work function, LDD 및
SiO2/SiON multi-spacer를 자체 대조실험으로 비교·최적화한다.

- [기준 프로젝트 계획서](<README_TCAD_MOSFET_PROJECT_Github 주소 반영본.md>)
- [개발환경 구축 가이드](docs/DEVSIM_SETUP.md)
- [Project_Git / tcad 브랜치 운영](docs/GIT_WORKFLOW.md)

저장소는 [iuhj0519-jpg/Eddie](https://github.com/iuhj0519-jpg/Eddie)이다.
tcad 브랜치는 tcad_project/만 추적한다. 완료 후 해당 폴더만 Project_Git에 통합한다.
다른 프로젝트의 삭제가 전파되지 않도록 tcad를 Project_Git에 직접 merge하지 않는다.
구체적인 통합 절차는 위 Git 운영 문서를 따른다.
2026-10-03 기준 WSL에서 DEVSIM 예제 실행과 cap2, diode, MOSFET, bias sweep, mobility 모델의 경향성 확인을 완료했다.
자체 소자의 정량 검증·특성 추출·최적화는 아직 완료하지 않았다.
완료 범위와 한계는 [오픈소스 분석 기록](docs/opensource_analysis.md)을 참고한다.
이전 README_TCAD_MOSFET_PROJECT.md 및 README_TCAD_MOSFET_PROJECT_수정본.md는 이력용 초안이다.

## 폴더별 역할

오픈소스 예제 탐색 이후, 아래 구조로 자체 실험과 검증 코드를 구현한다.

| 폴더 | 기능 |
|---|---|
| configs/ | 소자 치수, 도핑, 재료, 바이어스, solver 설정과 sweep 조건 |
| data/raw/ | 원시 I-V, mesh, solver 로그 등 재생성 가능한 출력; 기본 Git 제외 |
| data/processed/ | SS, DIBL, Vth, Ion/Ioff 등 추출·정리한 결과 |
| docs/ | 설치·Git 운영, 모델 방법론, 추출법, 실험 기록과 한계 |
| experiments/ | 단계별 실행 스크립트와 실험 구성; 14_spacer는 SiO2/SiON 비교 |
| figures/ | 보고서용 I-V 곡선, 전위·전계 분포, 비교 그래프 |
| notebooks/ | 탐색적 분석·시각화; 재사용할 로직은 src로 분리 |
| references/ | 논문·교재·오픈소스 출처, 사용 버전과 라이선스 기록 |
| src/device/ | 소자 구조, mesh, 영역·접촉·도핑 정의 |
| src/physics/ | 재료 파라미터, 물리 방정식과 수송·재결합 모델 |
| src/solver/ | 해석 초기화, 바이어스 sweep, 수렴 제어 |
| src/extraction/ | Vth, SS, DIBL, Ion/Ioff 추출 함수 |
| src/utils/ | 단위 변환, 설정·파일 입출력 등 공통 기능 |
| tests/ | 코드와 추출 함수의 자동 테스트 |
| validation/analytic/ | 해석식 대비 물리·수치 검증 |
| validation/literature/ | 문헌 결과와 조건·모델 차이를 명시한 비교 |
| validation/regression/ | 코드 변경 후 기준 결과가 유지되는지 확인 |

빈 폴더는 .gitkeep으로 추적한다. 실험 번호는 식별자이며 실제 진행 순서는 상세 계획서의 단계 표를 따른다.

## 다음 단계와 정량 최적화 실험

다음 단계는 **Phase 1: 기본 물리 검증과 model specification**이다. 예제 실행 성공을
자체 소자의 검증 완료로 간주하지 않는다. 기존 capacitor·PN 결과를 재사용해 해석식 대비
오차 검사를 자동화하고, MOSCAP 검증을 추가한다. 단위·접촉/계면 조건·통계·이동도 모델,
mesh와 solver 설정을 docs/methodology.md에 명시한다. 특히 2D 전류의 폭 정규화를 확인하기 전에는
기존 raw API 전류를 A 또는 A/um로 단정하지 않는다.

1. **Phase 1:** capacitor·PN·MOSCAP의 정량 검증과 수치 허용오차 기록.
2. **Phase 2:** 1 um long-channel NMOS와 공통 추출 코드 구현; Vth, SS, Ion/Ioff, DIBL의 추출 규약을 pilot 후 고정.
3. **Phase 3–7:** 100 nm baseline에서 gate stack·산화막 두께·effective work function·도핑을 대조실험하고, gate length scaling 후 28 nm 기준 소자와 SiO2/SiON spacer 비교.
4. **Phase 8:** 소수 변수 DOE, 제한 조건 및 Pareto 비교로 후보 선정; 더 미세한 mesh와 bias 간격에서 개선 재검증.
5. **Phase 9:** 원시 데이터·설정·추출 코드·비교표·재현 명령을 연결해 결과 보고.

Gate Length, 산화막 두께, channel/LDD doping 등의 **소자 설계 파라미터**를 변화시키고,
동일 온도·바이어스·물리 모델·추출법에서 I-V 및 지표를 비교한다. 변수별 영향 확인 후 조합 실험으로
trade-off를 평가한다. 이는 공정 레시피 자체를 계산하는 공정 TCAD와 구분한다.

최종 산출물은 baseline/candidate별 설정과 run ID, Vth[V], SS[mV/dec], Ion/Ioff 및 폭 정규화 전류,
DIBL[mV/V], 수치 오차, 제약 충족 여부와 개선율을 포함한 비교표다.
최대화 지표 개선율은 100*(후보-기준)/기준, 최소화 지표는 100*(기준-후보)/기준으로 계산한다
(양의 기준값에 적용; 기준이 0이거나 부호가 달라지면 절대 변화량과 별도 정의 사용).
목표 지표 A와 제약 지표 B의 한계 Y는 DOE 전에 정하고, 개선율 X는 실제 결과에서 계산한다.
자기소개서의 '[A 지표]를 [X%] 개선하면서 [B 지표]를 [Y 이하]로 유지'는 **향후 입증할 목표**이며
아직 달성한 결과가 아니다. 제약을 만족하는 후보가 없거나 수치 오차보다 개선폭이 작으면 그대로 보고한다.
구체적인 초기 추출 조건·제약·품질 기준은 기준 프로젝트 계획서의 5, 9, 10절을 따른다.

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
현재는 폴더 구조·문서 준비 단계이며 소자 구현이나 DEVSIM 설치 성공을 의미하지 않는다.
이전 README_TCAD_MOSFET_PROJECT.md 및 README_TCAD_MOSFET_PROJECT_수정본.md는 이력용 초안이다.

## 폴더별 역할

현재는 구조와 문서를 준비한 단계이며, 아래는 구현 시 사용할 역할이다.

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

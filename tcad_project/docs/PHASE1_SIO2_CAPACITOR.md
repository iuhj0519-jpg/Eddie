# Phase 1: 실행 가이드와 SiO2 capacitor 실험

작성일: 2026-10-03. 통합 갱신일: 2026-10-04.

## 문서 운영 원칙과 진행 상태

Phase별 문서는 하나만 유지한다. 앞부분에 Git·코드·테스트 진행 가이드를 두고,
뒷부분에 각 실험의 모델·실행 명령·결과·한계를 순서대로 추가한다.
Phase 1의 다층 capacitor·PN·MOSCAP도 이 문서에 이어 기록하며 별도 실험 가이드로 분리하지 않는다.
다음 Phase도 해당 Phase의 단일 문서 안에서 같은 구성을 따른다.
기존 PHASE1_EXECUTION.md의 가이드는 이 파일로 통합했다.

단층 SiO2 코드와 초기 테스트는 실행했다. 앞부분의 전체 Phase 1 구조와 CLI 중
아직 구현되지 않은 항목은 계획이며, 실제 단층 실행 방법은 뒷부분을 따른다.
solver_info 저장 코드는 Windows/WSL에 동기화했고, 사용자 실행 sio2_my_run_001에서 12개 검사 PASS를 확인했다.
2026-10-04 푸시 전 unittest 3개 메서드와 내부 subcase를 재실행해 OK를 확인했다. Phase 1 전체가 완료된 것은 아니다.
Git 게시 대상은 코드·config·문서이며 data/raw와 임시 run.log는 제외한다.

## A. 실험 진행 가이드

### A.0. 직접 진행하는 첫 실습 순서

이번 실습은 Phase 1 전체가 아니라 **단층 SiO2 검증**이다. 기존 실행 기록(B.7)은 참고값이며
자신의 실행 결과를 B.9에 별도로 기록한다. 아래 명령은 WSL bash에서 프로젝트 루트를 기준으로 실행한다.

**1단계 — 작업 위치와 입력 확인**

```bash
cd /home/iuhj0/projects/Project_Git/tcad_project
pwd
git branch --show-current
.venv/bin/python --version
cat configs/phase1/capacitor.json
```

10 nm, epsilon_r=3.9, 0→1 V인지 확인한다. 이 단계에서는 입력을 변경하지 않는다.
DEVSIM에서는 material='SiO2'라는 이름만으로 유전율이 정해지는 것이 아니라
config의 값으로 등록한 eps가 방정식에 사용된다는 점을 확인한다.

**2단계 — 계산 전에 예상값 작성**

두께를 cm로 변환하고 C/A=epsilon/t, E=-(Vright-Vleft)/t를 계산한다.
예상값은 C/A=3.453133246992e-7 F/cm², E=-1e6 V/cm이다.
왼쪽 전극 전하는 음수, 오른쪽은 양수이고 두 전하 합은 0이어야 한다.
이번 모델은 전류 I-V가 아니라 정전기 전하·전위 검증이다.

**3단계 — 구현을 함수별로 읽기**

코드는 다음 링크 또는 WSL의 같은 상대 경로에서 연다.

- [입력 config](../configs/phase1/capacitor.json)
- [소자·해석식·검사 코드](../src/device/sio2_capacitor.py)
- [실행·그래프 저장 코드](../validation/analytic/run_capacitor.py)
- [테스트 코드](../tests/test_sio2_capacitor.py)

| 읽을 순서 | 코드 | 해석하면서 답할 질문 |
|---|---|---|
| 1 | validate | 음수 두께, NaN, 0 V 전압차를 왜 거부하는가? |
| 2 | reference | nm→cm 변환 위치와 C/A의 단위는 무엇인가? |
| 3 | simulate의 mesh/region/contact | 10 intervals일 때 왜 node는 11개인가? |
| 4 | Potential, ElectricField, Displacement 모델 | 왜 Potential@n0와 @n1 미분 모델이 필요한가? |
| 5 | equation/contact_equation | 내부 전하 없는 방정식과 양단 전위 조건은 어디에 등록되는가? |
| 6 | solve와 solver_info | Newton 업데이트 수렴과 해석식 오차 PASS는 어떻게 다른가? |
| 7 | assess | Qright/dV에서 부호를 유지하는 이유는 무엇인가? |
| 8 | runner main | 실패 상태, 기존 경로 보호, 그래프 저장은 어떻게 처리되는가? |

**4단계 — 테스트부터 실행**

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_sio2_capacitor.py' -v
```

3개 테스트 메서드와 그 안의 subcase가 실행된다. 마지막 `OK`와 종료코드 0을 확인한다.
solver 테스트는 실제 DEVSIM을 호출한다. 입력 오류 검사는 기대한 ValueError를 확인하며,
결과 전하를 의도적으로 20% 변경한 검사는 검증기가 잘못된 결과를 FAIL로 판정하는지 확인한다.
여기서 실패하면 본 실행으로 넘어가지 말고 최초 traceback과 해당 subcase를 기록한다.

**5단계 — 자신의 run 생성 및 solver 로그 보존**

아래 블록은 새 출력 이름을 매번 만든다. Bash 배열로 solver의 종료코드를 tee와 구분한다.

```bash
mkdir -p data/raw/phase1
cap_run=$(mktemp -d data/raw/phase1/sio2_manual_XXXXXX)
.venv/bin/python -m validation.analytic.run_capacitor \
  --config configs/phase1/capacitor.json \
  --output "$cap_run/results" 2>&1 | tee "$cap_run/solver.log"
cap_status=${PIPESTATUS[0]}
echo "solver exit code: $cap_status"
echo "run directory: $cap_run"
```

runner는 존재하지 않는 results 폴더를 생성한다. 로그는 그 옆에 저장하므로 경로 충돌이 없다.
위 명령에서 나온 실제 run directory를 기록하고 이후 명령도 같은 터미널에서 실행한다.
종료코드가 0이 아니면 PASS라고 기록하지 않는다. config 검증처럼 출력 생성 전 실패한 경우
metadata가 없을 수 있으므로 solver.log도 함께 확인한다.

**6단계 — 수치와 그래프 대조**

```bash
cat "$cap_run/results/validation.csv"
cat "$cap_run/results/metadata.json"
code "$cap_run/results/capacitor.png"
```

code 명령이 없으면 VS Code 탐색기에서 출력 경로를 연다. VTM은 이번 실행에서 생성하지 않는다.
10/20/40 intervals의 4개 검사, 총 12개 CSV 행을 확인한다. 모두 True이고 metadata가 PASS인지 확인한다.
mesh JSON의 solver_info에서는 각 mesh의 수렴과 반복 정보를 확인한다.
전위 그래프가 직선이고 전계는 음의 상수인지, C/A가 해석값과 일치하는지 각각 기록한다.
겹친 그래프만으로 검증을 대체하지 않는다.

**7단계 — 한 변수만 바꾸어 확인**

기준 실행을 보존한 뒤 config를 다른 이름으로 복사해 VS Code에서 한 항목만 편집한다.
새 config는 매번 --config로 지정하고 새 output을 사용한다. 아래 값은 예상 경향이지 새 실행 결과가 아니다.

| 추가 실험 | 변경 | 예상 |
|---|---|---|
| 두께 | 10→20 nm, 전압 유지 | C/A와 전계 절댓값 모두 1/2 |
| 전압 | right_V 1→0.5, 두께 유지 | C/A 일정, 전계·전하 절댓값 1/2 |
| 극성 | left_V=1, right_V=0 | C/A 양수 유지, 전계·전하 부호 반전 |
| 전위 기준 | left_V=2, right_V=3 | 전위만 +2 V, 전계·전하·C/A 유지 |

처음에는 기준 실행과 두께 변경만 진행해도 된다. 바꾼 config·결과·해석은 B.9에 이어 기록한다.
복잡한 물리 모델이나 다음 소자를 동시에 추가하지 않는다.

**8단계 — 기록 후 커밋 검토**

B.9에 입력·실제값·오차·판정·원인을 적고 B.8의 명령으로 파일을 선별한다.
이번 실습 성공은 단층 검증 완료이며 Phase 1 전체 완료가 아니다.

### A.1. 기준 작업 공간과 현재 상태

- Git 루트: `/home/iuhj0/projects/Project_Git`
- 프로젝트: `/home/iuhj0/projects/Project_Git/tcad_project`
- 개발 브랜치: `tcad`
- 최종 통합 대상: `Project_Git` 브랜치. 직접 merge 금지; `docs/GIT_WORKFLOW.md`의 경로 한정 통합을 따른다.
- Windows `TCAD_Project`는 별도 자료 사본이며 Git 저장소가 아니다. 실험·커밋 기준은 WSL이다.
- src/tests/validation에는 현재 대부분 .gitkeep만 있다. 이제 재사용 가능한 자체 코드를 작성한다.
- 자체 코드도 DEVSIM solver를 사용한다. 오픈소스 예제를 그대로 실행하는 단계에서 프로젝트의 입력·검증·재현 체계를 소유하는 단계로 바뀐다.

PowerShell에서 WSL에 들어간 뒤 실제 프로젝트를 연다.

```powershell
wsl -d Ubuntu
```

```bash
cd /home/iuhj0/projects/Project_Git/tcad_project
pwd
git rev-parse --show-toplevel
git branch --show-current
git status --short
code .
```

`code` 명령이 없다면 VS Code의 WSL 연결 기능으로 같은 Linux 경로를 연다.
터미널만 WSL로 전환한 Windows 폴더 창과 구분한다. 이후 이 문서의 bash 명령은 WSL 프로젝트 폴더 기준이다.
**하위 폴더에서 git init을 실행하거나 clone을 중복 생성하지 않는다.**

### A.2. Git 준비: 현재 변경부터 보존

확인 시 README 두 개의 수정, 분석 문서와 run.log의 미추적 상태가 있었다.
작업 내용이 바뀔 수 있으므로 항상 다시 확인한다. dirty 상태에서 pull/switch/reset하지 않는다.

1. 기존 분석 종료 문서를 검토한다. `git diff`는 미추적 파일 본문을 보여 주지 않으므로 새 문서는 직접 열어 확인한다.
2. 문서만 명시적으로 stage하고 cached diff를 검토한다. run.log와 tmp 출력은 포함하지 않는다.
3. 사용자가 검토 후 문서 종료 커밋을 만든다.

```bash
git diff -- README.md 'README_TCAD_MOSFET_PROJECT_Github 주소 반영본.md'
git add -- docs/opensource_analysis.md docs/PHASE1_SIO2_CAPACITOR.md
git add -- README.md 'README_TCAD_MOSFET_PROJECT_Github 주소 반영본.md'
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "docs(tcad): conclude example analysis and plan phase 1"
```

commit은 위 검토가 끝난 뒤 실행한다. 다른 작업의 staged 변경이 있으면 먼저 소유자와 구분한다.
run.log는 삭제하지 않고 보존하되 stage하지 않는다. 새 실행 로그는 Git 제외인 data/raw 아래에 저장한다.
원격 확인/동기화는 작업 내용을 보존한 뒤 `git fetch origin`, `git status -sb`로 시작한다.
behind 상태이고 충돌할 로컬 변경이 없을 때만 `git pull --ff-only origin tcad`를 사용한다.
이번 단계는 tcad에서 계속 개발하며 불필요한 분기·force push·Project_Git 직접 병합을 하지 않는다.

### A.3. 첫 코드 작성 전 모델 명세

docs/methodology.md에 다음을 작성하고 config와 일치시킨다.

| 항목 | Phase 1에서 고정·검사할 내용 |
|---|---|
| 단위 | 내부 cm, V, cm^-3, F/cm 등; nm→cm 변환은 한 곳에서 수행 |
| 전류·전하 | API 출력의 차원/단면적/폭 의미; 1D 면적과 2D 폭 정규화를 분리 |
| 온도·물성 | 온도, epsilon, ni 등의 값·출처·버전 |
| 방정식 | 유전체 Poisson, 반도체 Poisson/DD, 통계·재결합 선택 |
| 경계조건 | 접촉 bias, work function 기준, 계면전하 유무, 전위 연속성 |
| 수치 조건 | mesh, 영역 크기, bias step, 절대·상대 허용오차, 최대 반복 |
| 검증 조건 | 해석식이 유효한 조건, 공핍 경계 판정법, 비교 오차 정의 |

처음부터 고농도·고전계의 복잡한 모델을 추가하지 않는다. 해석식과 비교 가능한 단순 조건에서
Poisson/접촉/계면의 정확도를 먼저 확인하고 PN의 DD로 확장한다.
모델 계수를 결과에 맞춰 임의 조절하지 않는다. 예제 코드 재사용 시 출처·라이선스·변경 내용을 남긴다.

### A.4. 구현할 코드 구조와 책임

아래는 **전체 Phase 1 제안 구조**다. 한 번에 모두 만들지 않고 capacitor부터 수직으로 완성한다.
현재 단층 구현 파일명과 실제 명령은 B절을 우선한다.

| 제안 파일 | 역할 | 먼저 작성할 테스트 |
|---|---|---|
| configs/phase1/*.json | 구조·물성·bias·mesh·허용오차 | 필수값, 양의 두께/유전율, 단위 검증 |
| src/utils/units.py | 단위 변환·정규화 | nm→cm, 잘못된 값 거부 |
| src/utils/run_io.py | run ID·입력 복사·metadata·CSV | 출력 충돌 거부, UTF-8, 실패 상태 보존 |
| src/device/capacitor.py | 단층/다층 1D mesh·영역·계면 | 영역 수·길이·접촉·계면 |
| src/physics/electrostatics.py | 유전율·전위 모델·경계식 | 경계 전위·전속 부호 |
| src/solver/dc.py | solve wrapper와 실패 전달 | 예외를 성공/0으로 바꾸지 않음 |
| validation/analytic/reference.py | 독립적인 해석식 | 단층 극한, 같은 유전율의 다층 극한 |
| validation/analytic/run_capacitor.py | 단층/다층 실행·비교·판정 | 해석값 대비 오차 |
| src/device/pn.py, run_pn.py | PN 구조 및 평형/DD 검증 | Vbi·공핍 폭·전류 보존 |
| src/device/moscap.py, run_moscap.py | MOSCAP 구조 및 Q-V/C-V | Cox·Vfb·표면전위·전하 보존 |
| tests/ | solver 없는 단위 테스트와 solver 통합 테스트 분리 | 수집된 테스트 수와 실패 메시지 |

표의 run_pn.py/run_moscap.py는 validation/analytic/ 아래에 둔다.
모듈 실행을 위해 필요한 __init__.py와 테스트 설정을 추가한다. DEVSIM 전역 상태가
테스트 간 누적되지 않도록 장치 정리 fixture 또는 독립 프로세스 실행을 설계한다.
solver 계산값을 그대로 정답으로 쓰지 않고 해석식 구현과 수치 모델 구현을 분리한다.

### A.5. 실험 구현·실행 순서

#### A.5.1 단층 capacitor

입력: 두께, 유전율, 양단 전압, mesh 간격.
출력: 위치별 Potential/E/D, 접촉 전하, C/A.
비교: C/A=epsilon/t, 선형 전위, 일정 전계. 접촉 전하 부호 규약을 먼저 확인한다.
전압차 0으로 Q/V를 나누지 않고 유한 전압차 또는 전하 미분으로 C를 구한다.
자동 판정: 정전용량 오차 <1%; 경계전위·전속·전하 균형 허용오차도 별도로 명시.

#### A.5.2 다층 capacitor

비교: (C/A)^-1=sum(t_i/epsilon_i), 각 층 전압 강하, 자유 계면전하가 없을 때 D 연속성.
동일 유전율 극한, 층 두께 변경, 유전율 변경→복원 테스트를 포함한다.
정전용량 오차 <1%. 변경 후 반드시 다시 solve한 결과끼리 비교한다.

#### A.5.3 PN 접합

비축퇴 급격 접합의 평형 조건부터 구현한다. Vbi와 공핍 근사 적용 조건을 config/보고서에 명시한다.
Vbi 오차 <2%, 공핍 폭 오차 <5%를 초기 기준으로 사용한다.
도핑 불연속의 위치와 공핍 경계 추출법을 고정하고, 근사 자체의 오차와 mesh 오차를 분리한다.
이후 작은 bias부터 DD sweep을 구현하고 전자+정공을 합한 모든 단자 전류 보존을 검사한다.
Shockley 식과의 정확한 일치를 모든 조건의 통과 기준으로 강제하지 않는다.

#### A.5.4 MOSCAP

단순 gate/oxide/semiconductor에서 시작하고 고정 계면전하 유무와 work-function 기준을 명시한다.
Gate sweep의 Qg·표면전위·carrier 분포를 저장한다. 준정적 C=dQg/dVg를 계산하고
정규화한 Cox 오차 <3%, Vfb와 work-function 부호, 축적·공핍·반전의 일관성을 검사한다.
Vfb/표면전위의 수치 허용오차는 기준해·정의와 함께 실행 전에 정한다.
미분의 bias 간격과 경계점 차분법을 기록한다. 준정적 C-V를 고주파 C-V로 이름 붙이지 않는다.

#### A.5.5 Mesh·step 민감도

각 소자의 coarse/medium/fine에서 C, Vbi, 공핍 폭, 표면전위 등을 비교한다.
Gate/bias step을 절반으로 줄여 특히 Q 미분의 안정성을 확인한다.
Phase 2용 Ion/Vth/SS 수렴 기준을 Phase 1 소자에 무리하게 적용하지 않는다.
fine도 절대 정답이 아니다. 기준 미달이면 허용오차를 사후 완화하기 전에 단위·경계·영역·mesh를 점검한다.

### A.6. 테스트 명령과 출력 계약

현재 바로 실행 가능한 것은 환경·경로 확인이다. 아래 CLI는 **위 코드와 의존성을 구현한 뒤** 사용할 제안이다.
pytest 등 필요한 도구는 개발 의존성 파일에 선언하고 실제 설치 버전을 기록한다.

```bash
.venv/bin/python -m pytest tests/unit -q
.venv/bin/python -m pytest tests/integration -q
.venv/bin/python -m validation.analytic.run_capacitor --config configs/phase1/capacitor.json
.venv/bin/python -m validation.analytic.run_pn --config configs/phase1/pn.json
.venv/bin/python -m validation.analytic.run_moscap --config configs/phase1/moscap.json
```

CLI는 실패하면 nonzero exit code를 반환하도록 구현한다. `no tests ran` 또는 import만 성공한 상태를
물리 검증 PASS로 기록하지 않는다. 예제의 큰 absolute_error를 의미 검토 없이 복사하지 않는다.

각 실행은 data/raw/phase1/<run_id>/에 다음을 남긴다.

- config.json: 기본값까지 펼친 실제 입력 및 단위.
- metadata.json: UTC 시간, Git commit/dirty 상태, Python/DEVSIM/의존성 버전, 실행 명령, 입력 해시.
- solver.log 및 convergence.csv: bias, 수렴 여부, 반복·오차 정보, 실패 이유.
- profiles.csv 및 terminal.csv: 단위가 명시된 원시 필드·단자값.
- validation.csv: 검사명, 예상값, 계산값, 절대/상대오차, 허용오차, PASS/FAIL.

수치 실패·추출 불가 값은 NaN과 상태로 남기고 0으로 채우지 않는다. 0 근처 보존 검사는
|sum I| <= atol + rtol*sum|I| 형태로 수행하며 atol은 단위와 측정한 수치 잡음 바닥에 맞춰 사전 고정한다.
정전용량·전위·전류에 같은 atol을 재사용하지 않는다. 정식 비교표/대표 그래프는
data/processed/phase1/와 figures/phase1/에 선별해 저장하고 run ID로 원시 결과와 연결한다.

### A.7. Git 커밋 단위와 검증 주기

| 순서 | 커밋 범위 예시 | 커밋 전 검사 |
|---|---|---|
| 1 | docs: 모델 명세·출력 계약 | 단위·출처·가정 검토 |
| 2 | feat: 단위/config/run IO + test | solver 없는 단위 테스트 |
| 3 | feat/test: 단층·다층 capacitor | 물리 검사, mesh 비교 |
| 4 | feat/test: PN | Vbi·공핍 폭·보존 검사 |
| 5 | feat/test: MOSCAP | Cox·표면전위·step 검사 |
| 6 | docs/test: Phase 1 요약·회귀 기준 | 전체 재실행 및 추적성 |

코드·테스트·관련 config를 같은 커밋에 포함한다. 아래 add 경로는 실제 구현된 파일에 맞게 좁힌다.

```bash
git status --short
git diff --check
git diff -- src tests validation configs docs
git add -- src/utils/units.py tests/unit/test_units.py
git diff --cached --check
git diff --cached
git commit -m "feat(tcad): add tested unit conversions"
```

생성물을 무조건 `git add .` 하지 않는다. 작은 기준 CSV와 대표 그림은 검토 후 선택적으로 추적한다.
raw/venv/tmp/PDF 제외 규칙을 확인한다. ignored raw는 경로·해시만으로 복구되지 않으므로
재현 명령 또는 별도 보관 위치도 남긴다. API 토큰·개인 경로 등 불필요한 정보는 배포 로그에서 제외한다.
검토된 커밋은 `git push origin tcad`로 게시한다. 이는 사용자가 실행할 후속 단계이며 이번 작업에서 실행하지 않았다.

### A.8. Phase 1 종료와 다음 단계

- [ ] 모델·단위·경계조건 문서와 실제 config 일치
- [ ] capacitor·PN·MOSCAP 자동 판정과 실패 테스트 구현
- [ ] 필수 bias 수렴 및 원시 출력의 NaN/Inf 검사
- [ ] mesh·bias-step 민감도와 해석식 적용 한계 기록
- [ ] clean 환경에서 재현 가능한 명령·의존성 제공
- [ ] 검증 요약과 run ID·코드 버전 연결, 검토된 commit 완료

전부 충족한 뒤 Phase 2의 1 um long-channel NMOS 및 공통 특성 추출로 진행한다.
Phase 1 자체에는 성능 최적화 개선율을 요구하지 않는다. 먼저 수치 결과를 신뢰할 기반을 만든다.

## B. 단층 SiO2 capacitor 실험

### B.1. 범위와 구현 파일

2026-10-04 첫 자체 검증 코드. 이상적인 평판 전극 사이의 **전하가 없는 단층 유전체**를 1D로 푼다.
MOSCAP이 아니며 Si bulk·도핑·carrier·이동도·누설·터널링을 포함하지 않는다.
단층 검증 이후 다층 유전체, PN, MOSCAP 순으로 확장한다.

| 파일 | 역할 |
|---|---|
| configs/phase1/capacitor.json | 두께·유전율·전압·mesh·검증 허용오차 |
| src/device/sio2_capacitor.py | 입력 검사, 독립 해석식, DEVSIM 구조/방정식, 결과 판정 |
| validation/analytic/run_capacitor.py | 3단계 mesh 실행, JSON/CSV/PNG 저장, 실행 metadata |
| tests/test_sio2_capacitor.py | 입력 오류·해석값·전압 반전·offset·두께 변화·판정 실패 테스트 |

첫 단층 예제를 따라가기 쉽게 모델 코드는 한 모듈에 모았다. 다층 확장 시 공통 물리/solver/IO를 분리한다.
API 연결 방식은 설치된 DEVSIM 2.11의 testing/cap2.py를 참고했으며 원본 예제 전체 복사 실행과 구분한다.
추가 패키지 설치 없이 기존 requirements.in의 DEVSIM·matplotlib와 표준 unittest를 사용한다.

### B.2. 모델과 기대값

- x=0: 0 V, x=t: 1 V의 Dirichlet 경계조건.
- t=10 nm=1e-6 cm, epsilon_r=3.9, epsilon_0=8.8541878128e-14 F/cm.
- epsilon_r는 이번 이상적 SiO2 검증의 고정 가정이며 측정 데이터에 맞춘 보정값이 아니다.
- 전위 방정식: d/dx(epsilon*d(phi)/dx)=0. 내부 전하와 내부 계면은 없다.
- phi(x)=Vleft+(Vright-Vleft)*x/t.
- E=-d(phi)/dx=-1e6 V/cm, D=epsilon*E=-3.453133246992e-7 C/cm².
- C/A=epsilon/t=3.453133246992e-7 F/cm² = 약 3.45313 fF/um².
- 오른쪽 전극 Q/A=+3.453133246992e-7 C/cm², 왼쪽은 반대 부호.

이 1D 평면 모델의 API 접촉 전하는 단위 단면적에 대응하므로 C/cm²로 해석한다.
실제 총 C[F]는 (C/A)*A[cm²]이다. 이 규약을 기존 2D MOSFET 전류 정규화에 그대로 적용하지 않는다.
코드는 오른쪽의 부호 있는 접촉 전하를 전압차로 나누어 C/A를 구한다. abs로 부호 오류를 숨기지 않는다.
edge 전계는 n0→n1 방향이다. endpoint 좌표로 +x 방향을 확인한 뒤 해석 전계와 비교한다.

### B.3. 실행 위치와 Git 확인

VS Code도 WSL 프로젝트를 열어야 한다. Windows 자료 사본에서 Python을 실행하지 않는다.

```bash
cd /home/iuhj0/projects/Project_Git/tcad_project
git rev-parse --show-toplevel
git branch --show-current
git status --short
```

Git 루트는 상위 Project_Git, 개발 브랜치는 tcad다. 새 git init은 하지 않는다.
기존 문서 변경과 run.log는 보존하고 이번 파일과 구분한다.

### B.4. 테스트 → 실제 검증 실행

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_sio2_capacitor.py' -v
.venv/bin/python -m validation.analytic.run_capacitor --config configs/phase1/capacitor.json --output data/raw/phase1/sio2_my_run_001
```

첫 명령은 3개 테스트 메서드를 실행하며 여러 입력/solver subcase를 포함한다.
두 번째는 10/20/40 intervals를 계산한다. 기존 output 경로가 있으면 덮어쓰지 않고 중단한다.
재실행은 sio2_my_run_002처럼 새로운 이름을 사용한다. zero-voltage Q/dV는 지원하지 않고 명시적으로 거부한다.
실패 판정은 종료코드 1, 예외 발생은 ERROR 기록 후 nonzero 종료다. 실패값을 0으로 채우지 않는다.

### B.5. 출력과 판정

| 출력 | 확인 항목 |
|---|---|
| config.json | 실제 입력과 사전 설정 허용오차 |
| metadata.json | PASS/FAIL/ERROR, 버전, Git commit/dirty, 소스·config 해시 |
| mesh_10/20/40.json | node 좌표/전위, edge 전계/전속, 양단 전하, solver_info |
| validation.csv | 실제 node 수, C/A, 각 오차·허용오차·판정 |
| capacitor.png | 3개 mesh의 전위/전계 및 해석선 |
| error.txt | 실행 도중 예외가 난 경우 traceback |

허용오차는 C/A 상대오차 <1%, 전위 최대오차 <1e-9 V, 전계 상대오차 <1e-8,
양단 전하 합의 절댓값 <1e-14 C/cm²다. 이들은 이번 선형 문제의 설정이지 모든 소자의 보편적 기준이 아니다.
solve 업데이트 기준은 absolute_error=1e-12, relative_error=1e-10, 최대 30회다.
solver_info의 수렴 여부를 별도로 검사하며 업데이트 기준과 해석식 오차 기준을 구분한다.
metadata의 dirty 상태에서는 commit hash만으로 재현할 수 없으므로 실제 소스와 config도 함께 보관해야 한다.

### B.6. 그래프 읽기

VS Code에서 output의 capacitor.png를 연다. Agg 모드이므로 팝업 창이 뜨지 않는 것이 정상이다.
왼쪽 전위는 0→1 V 직선이며, 오른쪽 +x 전계는 -1e6 V/cm의 일정한 값이어야 한다.
세 mesh와 해석선이 겹치는 것이 예상 결과다. 이 문제는 선형 해가 이산화로 정확히 표현되므로
mesh를 줄일 때 오차가 단조 감소하지 않고 반올림 수준에서 흔들릴 수 있다.
그래프만 보고 PASS를 판단하지 않고 validation.csv도 확인한다.
이번 구현은 PNG/JSON/CSV 출력이며 ParaView VTM을 생성하지 않는다.

### B.7. 최초 검증 기록과 한계

초기 실행 data/raw/phase1/sio2_first_20261004에서 11/21/41 node 모두 4개 검사 PASS였다.
C/A 상대오차 최대 약 2.0e-15, 전위 오차 최대 약 1.11e-16 V,
전계 상대오차 최대 약 2.56e-15, 전하 합 최대 약 6.88e-22 C/cm²였다.
최초 실행 이후 solver_info 저장을 추가했고 Windows/WSL 코드를 동기화했다.
사용자 실행 sio2_my_run_001(2026-10-04 16:55 KST)의 metadata는 PASS이며 3개 mesh의 12개 검사가 모두 True다.
해당 실행의 오차는 위 초기 실행과 같은 값이며 mesh JSON에 solver_info가 저장된 것을 확인했다.
2026-10-04 게시 전 unittest도 3개 테스트 메서드와 내부 subcase 모두 OK였다.
현재 결과는 단층 정전기 구현의 검증이며 Phase 1 전체 완료, SiO2 누설/신뢰성 또는 실제 공정 정확도를 뜻하지 않는다.

### B.8. 검토 후 Git 커밋

아래는 후속 변경을 검토한 후 사용하는 커밋 절차다. 이미 게시된 파일은 변경이 있을 때만 stage한다.

```bash
git diff --check
git add -- configs/phase1/capacitor.json src/device/sio2_capacitor.py
git add -- validation/analytic/run_capacitor.py tests/test_sio2_capacitor.py
git add -- docs/PHASE1_SIO2_CAPACITOR.md
git diff --cached --stat
git diff --cached
git commit -m "feat(tcad): validate single-layer SiO2 capacitor"
```

다른 staged 변경이 있으면 함께 커밋하지 않도록 먼저 구분한다. data/raw는 Git 제외다.
코드/config/manual은 추적하고, 대표 결과는 검토 후 data/processed 또는 figures에 선별 보관한다.
이후 tcad로 push하는 절차는 이 문서 A.7절을 따른다. Project_Git 직접 merge는 하지 않는다.
다음 구현은 단층 두께/유전율 scaling 검사를 확장하고, 다층 계면 전위·전속 연속성을 검증하는 것이다.

Windows VS Code에서도 `data/raw/phase1/sio2_my_run_001/`을 열 수 있도록 WSL 실행 폴더를 복사했다.
원본은 WSL이며 Windows 쪽은 확인용 스냅샷이다. 자동 동기화가 아니므로 후속 실행 결과는 별도로 복사해야 한다.
탐색기에서 data → raw → phase1 → sio2_my_run_001을 펼쳐 PNG/CSV/JSON을 연다.
원시 결과는 Git 제외 정책을 유지하며 GitHub에는 코드·설정·문서의 재현 절차를 게시한다.

### B.9. 사용자 직접 실행 기록 양식

아래 양식을 실행별로 이 문서 안에 복사한다. 기존 B.7의 결과를 자신의 실제값 칸에 옮겨 적지 않는다.

#### 실험: [기준/두께 변경/전압 변경]

- 실행 일시와 run directory: 미기록
- 코드 commit/dirty 및 source hash: 미기록
- config 경로와 변경한 항목: 미기록
- 목적과 사전 예상: 미기록
- 테스트 결과 및 실행 종료코드: 미실행
- solver 수렴·반복 정보: 미기록

| 항목 | 해석값/기준 | 실제값 | 오차 | 판정 |
|---|---|---|---|---|
| C/A [F/cm²] | epsilon/t | 미측정 | 미측정 | 미판정 |
| E [+x, V/cm] | -dV/t | 미측정 | 미측정 | 미판정 |
| Potential 최대오차 [V] | <1e-9 | 미측정 | 해당 값 | 미판정 |
| Qleft+Qright [C/cm²] | 절댓값 <1e-14 | 미측정 | 해당 값 | 미판정 |
| 10/20/40 mesh 검사 | 각 4개 검사 PASS | 미실행 | CSV 참조 | 미판정 |

- 전위·전계 그래프 해석: 미기록
- 이전 실험과 달라진 점 및 물리적 이유: 미기록
- 실패/예상과 다른 값의 원인 점검: 미기록
- 결론과 다음 행동: 미기록

실패 시 단위 변환 → 양단 bias → epsilon → 접촉 전하 부호 → solver_info 순서로 확인한다.
오차가 기준보다 크다고 허용오차부터 늘리지 않는다. 실패 실행도 삭제하지 말고 수정 후 새 run으로 비교한다.

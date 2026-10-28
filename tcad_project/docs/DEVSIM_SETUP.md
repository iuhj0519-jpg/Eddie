# DEVSIM 개발환경 구축 가이드

환경 확인: 사용자 화면 기준 Ubuntu 26.04 LTS, Python 3.14.4, Git 2.53.0,
Gmsh 4.14.0-git, x86_64, WSL2이다. 사용자가 패키지 상태 정상임을 확인했다.
기존 Ubuntu를 유지하고 Python venv를 구성한다. DEVSIM 설치와 solver 실행은 아직 미확인이다.
프로젝트 계획: [최종 README](<../README_TCAD_MOSFET_PROJECT_Github 주소 반영본.md>).

## 1. Windows에서 WSL 확인

2026-09-20 사용자 화면에서 Ubuntu가 VERSION=2, STATE=Stopped로 등록된 것을 확인했다.
Stopped는 설치된 배포판이 꺼져 있다는 뜻이므로 재설치하지 않는다.
PowerShell에서 아래 명령으로 기존 Ubuntu를 시작한다.

```powershell
wsl -d Ubuntu
```

현재 기본 배포판은 docker-desktop이다. 필요하면 PowerShell에서
`wsl --set-default Ubuntu`로 기본값을 변경할 수 있으며 Docker 배포판을 삭제할 필요는 없다.
Ubuntu에 들어간 후 `cat /etc/os-release`, `whoami`, `uname -m`으로 버전·사용자·architecture를 확인한다.
배포판 이름 Ubuntu만으로 24.04인지 판단하지 않는다.


Windows PowerShell에서 실행한다.

```powershell
wsl --status
wsl --list --verbose
wsl --list --online
```

Ubuntu가 이미 있으면 배포판 이름과 VERSION=2를 확인하고 해당 배포판을 사용한다.
설치되지 않은 경우 관리자 PowerShell에서 다음을 실행한다.

```powershell
wsl --install -d Ubuntu-24.04
```

필요한 재부팅 후 Ubuntu를 열어 Linux 사용자 이름과 비밀번호를 설정한다.
배포판 이름이 online 목록과 다르면 목록에 표시된 정확한 이름을 사용한다.
기존 배포판이 WSL1이면 정확한 배포판 이름을 확인한 뒤 다음과 같이 전환한다.

```powershell
wsl --set-version Ubuntu-24.04 2
```

위 명령은 예시 이름이다. 이미 WSL2이면 실행할 필요가 없다.
E_ACCESSDENIED가 나면 권한·조직 정책·WSL 서비스 상태를 확인한다.
제한된 도구 세션의 접근 실패만으로 사용자 PC에 WSL이 없다고 판단하지 않는다.

공식 안내: [Microsoft WSL 설치](https://learn.microsoft.com/en-us/windows/wsl/install).

## 2. Ubuntu의 시스템 패키지

이하 명령은 PowerShell이 아닌 **Ubuntu Bash**에서 실행한다.

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv build-essential curl gmsh
python3 --version
git --version
gmsh --version
uname -m
```

현재 환경의 python3는 Python 3.14.4이다. 아래 venv에서 DEVSIM 및 의존성 설치,
pip check, import, 실제 solve까지 확인해야 이 조합의 동작을 확인할 수 있다.
호환성 문제가 발생하면 오류를 기록하고 지원되는 별도 Python 환경을 검토한다.
OS의 시스템 Python을 삭제하거나 교체하지 않는다.
아래 pip/MKL 경로는 x86_64 기준이다. aarch64에서 Intel MKL을 그대로 설치하지 말고
DEVSIM 공식 안내의 대체 수학 라이브러리 구성을 확인한다.

## 3. 작업 위치와 기존 계획서 가져오기

Eddie 저장소의 Project_Git에서 분기한 tcad를 [Git 운영 절차](GIT_WORKFLOW.md)에 따라
WSL의 ~/projects/Project_Git에 clone하고 TCAD_Project/로 이동한다.
그 경우 아래 독립 폴더 생성/문서 복사와 6절의 git init은 건너뛴다.
프로젝트 하위에 중첩 .git을 만들지 않는다.
아래 독립 폴더 방식은 Eddie의 tcad 작업 트리를 사용하지 않는 경우에만 적용한다.


Linux Python과 Gmsh를 사용할 작업 트리는 WSL의 Linux 파일시스템에 둔다.
OneDrive 폴더는 기존 자료의 출처로 두고, 두 위치를 동시에 수정하지 않는다.
아래 새 위치가 이미 있다면 먼저 내용을 확인하고 기존 작업 트리를 사용한다.

```bash
mkdir -p ~/projects/tcad-mosfet-device-optimization
cd ~/projects/tcad-mosfet-device-optimization
mkdir -p docs references
```

새 작업 트리로 계획서와 가이드를 가져온다. -n은 기존 파일을 덮어쓰지 않는다.

```bash
cp -n "/mnt/c/Users/iuhj0/OneDrive/바탕 화면/TCAD_Project/README.md" .
cp -n "/mnt/c/Users/iuhj0/OneDrive/바탕 화면/TCAD_Project/README_TCAD_MOSFET_PROJECT_Github 주소 반영본.md" .
cp -n "/mnt/c/Users/iuhj0/OneDrive/바탕 화면/TCAD_Project/docs/GIT_WORKFLOW.md" docs/
cp -n "/mnt/c/Users/iuhj0/OneDrive/바탕 화면/TCAD_Project/docs/DEVSIM_SETUP.md" docs/
```

원본 논문 PDF는 필요할 때 references/에 복사한다. 공개 저장소에 올릴지는 배포 권한을 확인한다.
이후 실행 config·결과·코드는 이 Linux 작업 트리를 기준으로 관리한다.

## 4. Python 가상환경과 패키지

처음 한 번:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "devsim==2.11.0" mkl numpy scipy pandas matplotlib pytest pyyaml
python -m pip check
```

Gmsh CLI는 apt로 설치했으므로 Python gmsh 패키지는 아직 필요하지 않다.
Notebook이 필요해지면 나중에 jupyterlab을 추가한다.
Conda와 pip의 MKL/NumPy를 섞지 않고 여기서는 venv + pip로 통일한다.

확인:

```bash
which python
python -m pip --version
python -c "import devsim; from importlib.metadata import version; print('DEVSIM', version('devsim'))"
python -c "import numpy, scipy, pandas, matplotlib, pytest, yaml; print('Scientific stack OK')"
```

which python은 프로젝트의 .venv/bin/python을 가리켜야 한다.
2026-09-12 확인한 PyPI 배포는 2.11.0이며 CPython 3.9+ Linux x86_64 wheel이 제공된다.
현재 프로젝트는 이 버전을 시작점으로 고정한다. 업그레이드는 별도 검증 후 수행한다.
[PyPI 배포 정보](https://pypi.org/project/devsim/),
[DEVSIM 공식 설치 안내](https://github.com/devsim/devsim/blob/main/INSTALL.md).

## 5. 실제 solver smoke test

import만으로 설치 완료를 판정하지 않는다.
공식 설치 안내의 testing/cap2.py를 **설치된 동일 버전 배포물**에서 찾아 실행한다.
이는 환경 점검이며 프로젝트의 독립적인 물리 validation을 대신하지 않는다.

```bash
mkdir -p tmp/smoke
python - <<'PY'
from importlib.metadata import distribution
from pathlib import Path
import os
import runpy

dist = distribution("devsim")
candidates = [
    Path(dist.locate_file(f)).resolve()
    for f in (dist.files or [])
    if str(f).replace("\\", "/").endswith("testing/cap2.py")
]
if len(candidates) != 1:
    raise SystemExit(
        "설치 배포물에서 testing/cap2.py 하나를 찾지 못했습니다. "
        "공식 devsim_data 위치 또는 동일 버전 예제 배포물을 확인하세요."
    )
example = candidates[0]
print("Example:", example)
os.chdir(Path("tmp/smoke").resolve())
runpy.run_path(str(example), run_name="__main__")
print("DEVSIM solver smoke test completed")
PY
```

종료코드 0, 마지막 completed 메시지, 실제 solve 로그를 확인한다.
실패 시 traceback을 보관하고 원인을 해결한 뒤 다음 단계로 진행한다.

예제가 없는 배포 구성에서는 다음으로 설치 파일 목록을 확인한다.

```bash
python -m pip show -f devsim
```

공식 devsim_data 또는 설치 버전과 일치하는 소스/예제 배포를 확보한다.
임의의 최신 main 예제로 버전 불일치를 만들지 않는다.
[공식 cap2 예제의 구조 참고](https://github.com/devsim/devsim/blob/main/testing/cap2.py).

## 6. 프로젝트 구조·Git·환경 기록

```bash
mkdir -p src/device src/physics src/solver src/extraction configs
mkdir -p validation/analytic validation/regression experiments tests
mkdir -p data/raw data/processed figures docs references tmp
```

새 Git 저장소인 경우에만:

```bash
git init -b main
```

에디터에서 .gitignore를 만들고 다음을 넣는다.

```gitignore
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
.pytest_cache/
tmp/
data/raw/
```

핵심 작은 regression I-V는 validation/regression/에 둬서 버전 관리한다.
모든 로그를 무조건 제외하지 않고, 중요한 convergence 결과는 data/processed/에 보관한다.

requirements.in에는 직접 선택한 패키지를 적는다.

```text
devsim==2.11.0
mkl
numpy
scipy
pandas
matplotlib
pytest
pyyaml
```

설치와 smoke test 성공 후 환경을 기록한다.

```bash
python -m pip freeze > requirements.lock.txt
python --version > docs/python-version.txt
gmsh --version > docs/gmsh-version.txt 2>&1
uname -a > docs/platform.txt
python -m pip check
git status
```

requirements.lock.txt는 해당 OS/architecture의 환경 snapshot이다.
동일 환경 재설치는 python -m pip install -r requirements.lock.txt를 사용한다.
다른 플랫폼에 그대로 적용되는 보편적 lockfile이라고 가정하지 않는다.

변경 확인 후 선택한 파일만 stage하고 commit한다.

```bash
git add README.md "README_TCAD_MOSFET_PROJECT_Github 주소 반영본.md" docs .gitignore requirements.in requirements.lock.txt
git commit -m "chore: establish TCAD project plan and verified environment"
```

Git 이름/이메일이 미설정이면 본인의 값으로 저장소 로컬 설정을 한 뒤 commit한다.

## 7. VS Code와 매 세션 시작

Windows VS Code에 WSL 확장을 설치하고 Ubuntu 프로젝트 폴더에서:

```bash
code .
```

Python interpreter는 .venv/bin/python을 선택한다.
tcad 브랜치 작업 트리에서는 매 세션을 다음으로 시작한다.

```bash
cd ~/projects/Project_Git/TCAD_Project
source .venv/bin/activate
git branch --show-current
git status
```

테스트가 구현된 뒤 pytest -q를 사용한다. 테스트 파일이 없는 초기 상태의
"no tests ran"을 검증 성공으로 기록하지 않는다.

## 8. 문제 해결 및 Phase 0 완료

| 증상 | 확인할 항목 |
|---|---|
| No matching distribution | Python 버전, uname -m, pip 버전, wheel 지원 |
| MKL/BLAS 로딩 실패 | 같은 venv의 mkl 설치, 공식 수학 라이브러리 설정 |
| externally-managed-environment | venv 활성화 여부; sudo pip 사용하지 않음 |
| devsim import 불가 | which python과 python -m pip가 같은 환경인지 |
| WSL/경로 오류 | PowerShell과 Bash 구분, 공백·한글 경로 따옴표 |
| Gmsh Python import 실패 | CLI와 Python API는 별도 설치임; 현재는 CLI 사용 |
| 예제 없음 | devsim_data 및 설치 버전에 맞는 예제 확인 |
| solve 실패 | 전체 로그와 모델/라이브러리 버전 보관, 원인 확인 |

- [ ] WSL2 Ubuntu에서 작업 폴더 접근
- [ ] venv Python과 의존성 import 성공
- [ ] pip check 성공
- [ ] 실제 capacitor solver smoke test 성공
- [ ] Gmsh CLI 실행 및 버전 기록
- [ ] 환경 snapshot과 Git 기록 완료

첫 개발 과제는 1D capacitor → 2층 capacitor이다.
이 단계에서 mesh, dielectric interface, 단위, charge/capacitance 추출을 익힌 뒤 MOSCAP으로 진행한다.

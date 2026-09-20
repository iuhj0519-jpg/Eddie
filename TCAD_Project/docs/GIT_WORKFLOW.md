# Project_Git / tcad 브랜치 운영

저장소: https://github.com/iuhj0519-jpg/Eddie.git
분기 기준 및 완료 후 통합 대상: Project_Git (저장소 이름이 아닌 브랜치 이름).
개발 브랜치: tcad. 프로젝트 경로: TCAD_Project/.
초기 분기 기준 commit: ae1c9928440e29245d22e65e116dc5d64840679a.
기존 네 개 프로젝트 폴더를 보존하며, main은 이번 작업의 통합 대상이 아니다.

## WSL 개발 작업 트리

tcad 브랜치를 원격에 구성한 이후 Ubuntu에서 실행한다.
아래 Project_Git은 로컬 clone 폴더 이름이며 원격 저장소 이름은 Eddie이다.

```bash
mkdir -p ~/projects
cd ~/projects
git clone --branch tcad https://github.com/iuhj0519-jpg/Eddie.git Project_Git
cd Project_Git
git status
git branch --show-current
cd TCAD_Project
```

이미 clone되어 있으면 새로 만들지 않고 해당 경로에서 상태를 확인한다.
미커밋 변경이 있는 상태에서 무조건 switch/pull하지 않는다.
Windows의 문서 준비본과 WSL 개발본은 Git commit/push/pull로 교환한다.
DEVSIM venv는 TCAD_Project/.venv에 만들며 Git에 포함하지 않는다.
프로젝트 하위에서 git init을 다시 실행하지 않는다.

## 개발

```bash
cd ~/projects/Project_Git
git switch tcad
git status
git diff
```

실제 구현한 단계의 입력·코드·검증 결과만 선택하여 stage한다.
구현 후 테스트가 존재할 때 pytest를 실행한다.
빈 테스트 폴더의 no tests ran을 PASS라고 기록하지 않는다.

```bash
git add TCAD_Project
git diff --cached --stat
git commit -m "feat(tcad): implement and validate the current phase"
git push -u origin tcad
```

## 프로젝트 완료 후 통합

1. tcad 브랜치의 코드·결과·재현성 문서를 검토한다.
2. Project_Git의 변경을 확인하고 필요 시 tcad에서 통합·충돌 해결 후 재검증한다.
3. base=Project_Git, compare=tcad인 PR을 열어 변경을 검토한다.
4. 검증 완료 후 PR merge 또는 일반 merge로 통합한다.
5. merge 확인 전 tcad 브랜치를 삭제하지 않는다.

이번 구조 준비 단계에서는 Project_Git 또는 main으로 merge를 수행하지 않는다.

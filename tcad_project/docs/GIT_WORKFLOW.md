# tcad 전용 개발과 Project_Git 통합

저장소: https://github.com/iuhj0519-jpg/Eddie.git
개발 브랜치: `tcad`. 현재 트리는 `tcad_project/`만 추적한다.
최종 통합 대상: `Project_Git` 브랜치이며 기본 브랜치 `main`과 구분한다.
초기 분기 기준: `ae1c9928440e29245d22e65e116dc5d64840679a`.

브랜치는 폴더 필터가 아니라 저장소 전체 스냅샷이다. 다른 프로젝트의 추적 제외도
삭제 변경으로 이력에 남는다. 과거 공통 이력을 유지하며 force push하지 않는다.
**tcad를 Project_Git에 직접 merge하거나 그대로 PR로 병합하지 않는다.**
다른 프로젝트를 보존하기 위해 아래 경로 한정 통합을 사용한다.

## WSL 작업 트리

아래 Project_Git은 로컬 clone 폴더 이름이다. 해당 폴더가 아직 없을 때 실행한다.

```bash
mkdir -p ~/projects
cd ~/projects
git clone --branch tcad https://github.com/iuhj0519-jpg/Eddie.git Project_Git
cd Project_Git/tcad_project
```

기존 clone은 저장소 루트에서 git status로 미커밋 변경을 확인·보존한 후
git switch tcad와 git pull --ff-only origin tcad를 실행한다.
개발 경로는 ~/projects/Project_Git/tcad_project이다.
venv는 tcad_project/.venv에 만들고 프로젝트 하위에서 git init을 실행하지 않는다.
Windows 자료 폴더 이름 TCAD_Project는 변경하지 않았다.

## 개발

저장소 루트에서 실행한다. 전체 폴더를 무조건 stage하지 않는다.

```bash
git status
git diff -- tcad_project
git add tcad_project
git diff --cached --stat
git commit -m "feat(tcad): implement and validate the current phase"
git push origin tcad
```

구현된 테스트가 있을 때 실행하고 결과를 기록한다. 빈 tests 폴더의
no tests ran은 검증 성공이 아니다. raw 결과, venv, PDF는 제외 규칙을 따른다.

## 완료 후 경로 한정 통합 (지금 실행하지 않음)

1. tcad 코드·결과·재현 문서를 검증하고 작업 트리를 깨끗하게 만든다.
2. 최신 원격 상태를 가져와 Project_Git 기반 새 통합 브랜치를 만든다.

```bash
git fetch origin refs/heads/Project_Git:refs/remotes/origin/Project_Git refs/heads/tcad:refs/remotes/origin/tcad
git switch -c integrate/tcad-project origin/Project_Git
```

3. Project_Git에 tcad_project/가 이미 있으면 먼저 비교한다. 아래 restore는 해당 경로를
   대체하므로 다른 작업자의 변경이 있으면 그대로 실행하지 말고 수동 통합한다.
   경로가 아직 없을 때는 다음과 같이 최종 스냅샷을 가져온다.

```bash
git restore --source=origin/tcad --staged --worktree -- tcad_project
git diff --cached --name-status
git diff --cached --check
```

4. 변경이 tcad_project/에만 한정되고 다른 프로젝트 삭제가 없는지 확인한다.
   통합 상태에서 테스트와 문서를 검증한 후 커밋·푸시한다.

```bash
git commit -m "feat(tcad): integrate validated TCAD project"
git push -u origin integrate/tcad-project
```

5. base=Project_Git, compare=integrate/tcad-project인 PR을 열고 승인 후 병합한다.

이 방식은 최종 스냅샷을 통합한다. 상세 개발 이력은 tcad에 남으므로 통합 후에도
tcad를 보존한다. 현재 구조 정리 단계에서는 통합이나 PR 생성을 하지 않는다.

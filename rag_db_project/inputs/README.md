# RAG Input Sources

이 디렉터리는 Agent가 코드 생성 전에 읽을 수 있는 승인 입력을 관리한다. 생성된 RTL, Agent patch 및 실행 결과는 이곳에 저장하지 않는다.

## 구성

- `reference_model/`: legacy FC-MLP 구현, model parameter와 baseline test data
- `systolic_controller/`: 이식 대상 Systolic Controller, 2D Array, Systolic Cell과 MAC PE 원본 RTL
- `specifications/`: reference, systolic accelerator, optimization 및 verification 요구사항

## 관리 규칙

1. 원본 코드는 가능한 한 byte 단위로 보존한다.
2. 각 SPEC은 `doc_id`, `version`, `status`와 requirement ID를 가진다.
3. `draft-for-review` 문서는 승인된 요구사항처럼 사용하지 않는다.
4. 현재 구현과 목표 요구사항을 As-Is/To-Be로 구분한다.
5. 단계별 허용 입력은 `manifests/phase_access_policy.yaml`로 제한한다.
6. 날짜는 기술 결과와 검색 품질에 영향을 주는 경우가 아니면 문서 metadata에 기록하지 않는다.

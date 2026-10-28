# 참고 자료 관리

기준 README 15절의 공식 DEVSIM GitHub 자료를 사용한다.

빌려온 코드마다 URL, commit/tag, 파일, 라이선스, 수정 사항을 기록한다.
재료 값은 단위·온도·조성·공정 조건·source DOI와 함께 기록한다.
제3자 PDF는 초기 원격 commit에 포함하지 않는다.

## PN voltage sweep 구현 참고 (준비, 실행 검증 전)

- 저장소: https://github.com/devsim/devsim
- 출처: DEVSIM LLC, Apache-2.0. 로컬 DEVSIM 2.11 설치본의 python_packages/simple_physics.py 및 simple_dd.py를 읽고 해당 helper를 호출한다. 설치본에 대응하는 Git commit은 확인하지 않았으며 임의 지정하지 않는다.
- simple_physics.py SHA-256: c1f66b11df7d1b96f41f123b9c5841681655438fc17e13e60906274f7d99490f
- simple_dd.py SHA-256: a3afeeb73a00199f481608587465ad42b453c715cdcb409240d6742574d0d91d
- 사용: CreatePE/CreateECE/CreateHCE, ohmic contact, SG current 및 Jacobian. helper 파일 자체는 수정하지 않는다.
- 프로젝트 차이: 물성은 JSON에서 명시, SRH 자동 생성 wrapper 제외, generation=0 명시, 양 방향 평형 초기화, 수렴 상태 복원, 접합 좌우 적분과 검증·출력은 프로젝트 코드에서 수행한다.
- 자세한 가정·단위·실행 조건은 [PN 문서 10절](../docs/PHASE1_PN_JUNCTION.md)을 따른다. helper를 사용한 사실은 runtime 검증 완료를 뜻하지 않는다.

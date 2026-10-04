# 오픈소스 프로젝트 분석


- **cap2:** 해석값과의 일치 및 유전율 조건 복원을 확인하고, interface를 중심으로 전위·전계·전속을 평가하는 테스트.
- **diode:** 순방향 I-V 경향을 확인하면서 solver 수렴과 전류 보존 정확도를 별도로 평가하는 테스트.
- **MOSFET:** 2D MOSFET의 구조·도핑·접촉 및 계면 조건을 구성하고 Poisson–drift-diffusion 해석의 수렴과 전위·전자농도 분포를 확인하는 테스트.
- **Bias Sweep:** Gate 전압을 설정한 뒤 고정하고 Drain 전압을 단계적으로 증가시켜 I-V, 전류 보존 및 전위·전자농도 변화를 확인하는 테스트.
- **Mobility 보정:** bulk·표면·속도포화 이동도 모델을 적용해 I-V와 이동도 공간 분포를 비교하고 Drain bias에 따른 이동도 저하 및 전류 증가 억제 경향을 확인하는 테스트.

cap2 실행 근거는 `tmp/opensource_tests/cap2-4rBfDV/run.log`, diode 실행 근거는
`tmp/opensource_tests/diode-Ka8Tsj/run.log` 및 `diode-Gbm4eo/run.log`와 사용자 확인 그래프다.
cap2의 유전율 변경 후 복원된 해가 원래 조건으로 돌아오는 것을 확인했다.
파라미터만 변경하고 재해석하기 전의 출력은 새 조건의 수렴해와 구분한다.
diode는 순방향 전류 증가와 단자 전류 합의 잔여값을 확인했다. 평형 부근의 작은 전류를
실제 누설 전류로 단정하지 않으며, 정상 종료·수렴·물리 정확도는 별도 판정한다.

## 목차

- 1. DEVSIM (devsim/devsim)
  - 1.1. cap2.py: 1D 다층 유전체 정전기
    - 1.1.1. 범위와 출처
    - 1.1.2. 블록 A: 구조를 수학적 구간으로 바꾸기
    - 1.1.3. 블록 B: 입력, 미지수, 파생량 구분
    - 1.1.4. 블록 C: edge_model과 미분
    - 1.1.5. 블록 D: equation으로 영역 잔차 구성
    - 1.1.6. 블록 E: contact_equation으로 양단 전위 고정
    - 1.1.7. 블록 F: interface_model과 interface_equation
    - 1.1.8. 블록 G: solve가 하는 일
    - 1.1.9. 손으로 구한 첫 해석의 예상값
    - 1.1.10. 첫 solve 이후의 코드
    - 1.1.11. 테스트 실행: 환경·경로·로그
    - 1.1.12. API·물리 결과 판정
  - 1.2. diode_1d.py: 1D PN 접합
    - 1.2.1. 범위와 출처
    - 1.2.2. 파일별 역할과 호출 흐름
    - 1.2.3. 구조·도핑과 capacitor의 차이
    - 1.2.4. 해석 단계와 미지수
    - 1.2.5. 현재 분석의 한계
    - 1.2.6. Region과 파일별 코드 위치
    - 1.2.7. Poisson 방정식과 접촉 조건
    - 1.2.8. Drift-diffusion과 전류
    - 1.2.9. 결합 solve와 sweep
    - 1.2.10. 테스트 실행과 bias별 출력
    - 1.2.11. 결과 판정과 산출물
  - 1.3. MOSFET 예제: 구조와 공간 분포
    - 1.3.1. 분석 대상과 파일 역할
    - 1.3.2. 구조·좌표·도핑 해석
    - 1.3.3. 전위 해석과 접촉·계면 조건
    - 1.3.4. Drift-diffusion 초기화와 수렴
    - 1.3.5. Potential·logElectrons 시각화 해석
    - 1.3.6. Channel 판정과 분석 한계
  - 1.4. Bias Sweep: 단자 특성과 전류 보존
    - 1.4.1. 실행 대상과 고정 조건
    - 1.4.2. Ramp와 상태별 출력 흐름
    - 1.4.3. VTM 번호와 bias 대응
    - 1.4.4. Potential·전자농도 변화
    - 1.4.5. I-V와 전류 보존 잔여값
    - 1.4.6. Gate 추가 진단과 채널 판정
    - 1.4.7. 출력 문제와 재현 시 주의점
  - 1.5. Mobility 보정: 이동도와 I-V 경향
    - 1.5.1. 실행 대상과 비교 조건
    - 1.5.2. Bulk·표면·속도포화 모델 연결
    - 1.5.3. Element 전류와 접촉 방정식
    - 1.5.4. I-V 정량 비교와 인과 해석 한계
    - 1.5.5. Solver·전류 보존 비교
    - 1.5.6. Bulk·표면 이동도 관찰
    - 1.5.7. 이동도 비율과 속도포화 관찰
    - 1.5.8. 색 범위·mesh·데이터 위치의 한계
    - 1.5.9. 산출물·재현성과 최종 판정
  - 1.6. 분석 종료 범위와 다음 Phase

## 1. DEVSIM (devsim/devsim)

### 1.1. cap2.py: 1D 다층 유전체 정전기

#### 1.1.1. 범위와 출처

분석 대상 버전은 DEVSIM 2.11.0이며, 공식 `testing/cap2.py`의 첫 DC 해석을 다룬다.
범위: 구조·물성·전위 방정식·경계조건·solver와 해석식 예상값. 최초 코드 독해일: 2026-09-23.
이후 예제 실행과 결과 경향 확인을 완료했다. 자체 소자의 정식 수치 검증 완료 보고서는 아니다.
아래 main 소스와 설치본의 완전한 동일성을 주장하지 않으며 설치본을 분석 기준으로 우선한다.

- 설치본 위치: `/home/iuhj0/projects/Project_Git/tcad_project/.venv/devsim_data/testing/cap2.py`
- [공식 예제](https://github.com/devsim/devsim/blob/main/testing/cap2.py): main은 변경될 수 있다.
- [DEVSIM 2.11.0 모델·방정식 설명](https://devsim.net/models.html)
- [API 및 solve 설명](https://devsim.net/CommandReference.html)
- 공식 예제의 라이선스 표시는 Apache-2.0이다. 실제 코드를 재사용할 때 원본 저작권·라이선스 표시를 보존하고 LICENSE/NOTICE를 확인한다.

#### 1.1.2. 블록 A: 구조를 수학적 구간으로 바꾸기

```text
x=0                      x=0.5                       x=1
top ├──── MySiRegion ──────┼────── MyOxRegion ──────────┤ bot
                          MySiOx
```

`pos`는 기준 위치, `tag`는 위치 이름, `ps`는 양의 방향 격자 간격이다.
`ns`를 생략하면 ps를 사용한다. 세 기준 위치만 있다고 node가 세 개뿐인 것은 아니다.
contact는 외부 경계, interface는 영역 사이 내부 경계이다.
`finalize_mesh`와 `create_device` 이후 물성·모델·방정식을 소자에 등록한다.
아직 전압이나 계면 조건을 적용한 것은 아니다.

#### 1.1.3. 블록 B: 입력, 미지수, 파생량 구분

| 분류 | 이름 | 의미/단위 |
|---|---|---|
| 입력 | Permittivity | epsilon1=11.1 epsilon0, epsilon2=3.9 epsilon0; F/cm |
| 입력 | topbias, botbias | 첫 해석에서 각각 1 V, 0 V |
| 등록 상수 | ElectricCharge | q=1.6e-19 C; 첫 정전기 플럭스 식에 사용되지 않음 |
| 미지수 | Potential | 각 region node의 전위 psi; V |
| 파생량 | ElectricField | edge 방향 전계 E; V/cm |
| 파생량 | PotentialEdgeFlux | 전속밀도 D=epsilon E; C/cm² |

`node_solution`으로 전위를 준비하고 `edge_from_node_model`로 양 끝 전위를
edge 식에서 참조할 수 있게 한다. 이때 아직 해가 구해진 것은 아니다.

#### 1.1.4. 블록 C: edge_model과 미분

edge는 소자의 외곽선이 아니라 인접한 격자점 사이 연결이다.
아래에서는 설명을 위해 n0에서 n1 방향을 +x로 잡는다.

$$
E_{01}=\frac{\psi_0-\psi_1}{h},\qquad h=|x_1-x_0|.
$$

`EdgeInverseLength`가 1/h이고, 이 식은 E=-dpsi/dx의 이산 표현이다.
물리적 +x 성분을 출력과 대조할 때는 실제 edge 방향도 확인한다.

전위에 대한 편미분은:

$$
\frac{\partial E_{01}}{\partial\psi_0}=\frac1h,
\qquad
\frac{\partial E_{01}}{\partial\psi_1}=-\frac1h.
$$

이것이 콜론이 있는 `ElectricField:Potential@n0`, `...@n1`의 의미다.
다른 물리량을 푸는 방정식이 아니라 Jacobian을 만들기 위한 민감도이다.

$$
D_{01}=\varepsilon E_{01},\qquad
\frac{\partial D_{01}}{\partial\psi_0}=\frac{\varepsilon}{h},\qquad
\frac{\partial D_{01}}{\partial\psi_1}=-\frac{\varepsilon}{h}.
$$

이는 유전율이 전위에 무관한 현재 예제의 결과이다. 코드의 diff는 식을 미분하는
기호 연산이며, 작은 전위 perturbation을 가해 수치 미분하는 명령이 아니다.

#### 1.1.5. 블록 D: equation으로 영역 잔차 구성

다음은 원본 API 인자의 의미를 나타낸 요약이다.

| 인자 | 값 | 해석 |
|---|---|---|
| name | PotentialEquation | 방정식 식별자; 이름 자체가 물리를 결정하지 않음 |
| variable_name | Potential | 갱신할 node 미지수 |
| edge_model | PotentialEdgeFlux | 면을 통과하는 플럭스 항 |
| node_model | 빈 문자열 | 체적 소스 항을 등록하지 않음 |
| time_node_model | 빈 문자열 | 시간 미분 항을 등록하지 않음 |
| variable_update | default | 일반적인 변수 갱신 방식 |

`node_model`이 비어 있어도 Potential node 미지수는 존재한다.
모델의 equation 문자열은 계산식 정의이고, `equation()` 함수는 해석 방정식 등록이다.

이 문제의 연속 방정식은 Gauss 법칙에서 자유 공간전하 rho=0인 경우이다.

$$
\frac{dD}{dx}=0,\quad D=-\varepsilon\frac{d\psi}{dx},
\quad \frac{d}{dx}\left(\varepsilon\frac{d\psi}{dx}\right)=0.
$$

각 제어체적에서 나가는 순전속을 0으로 만든다. 일정한 단면적을 나눈 1D 형태로,
내부 node i의 잔차를 다음처럼 쓸 수 있다.

$$
R_i=D_{i+1/2}-D_{i-1/2}
=\frac{\varepsilon_R}{h_R}(\psi_i-\psi_{i+1})
-\frac{\varepsilon_L}{h_L}(\psi_{i-1}-\psi_i)=0.
$$

따라서 인접 전위와 연결된 행렬 한 행은:

$$
-a_L\psi_{i-1}+(a_L+a_R)\psi_i-a_R\psi_{i+1}=0,
\qquad a_L=\varepsilon_L/h_L,\ a_R=\varepsilon_R/h_R.
$$

동일 영역·균일 격자에서는 psi_i=(psi_(i-1)+psi_(i+1))/2이다.
영역 내부 전위가 직선인 이유다. edge 전속 자체를 0으로 만드는 것이 아니다.
위 식은 이해를 위한 1D 정규화 유도이며 내부 행 번호·기하 가중치의 출력 형식까지
그대로 재현한 것은 아니다. 잔차 한 행 전체의 부호를 뒤집어도 해는 같다.

#### 1.1.6. 블록 E: contact_equation으로 양단 전위 고정

접촉용 node 식은 R_top=psi_top-1, R_bot=psi_bot-0이다.
이 식을 접촉의 PotentialEquation에 연결하면 해당 위치의 내부 방정식 대신
Dirichlet 경계조건을 적용한다. 미분은 각각 dR/dpsi=1이다.

`edge_charge_model`은 접촉 전하 계산에 쓸 플럭스 모델을 연결한다.
전압 경계조건과 전하 조회의 역할은 다르다. 이름에 charge가 있다고 해서
영역 내부 도핑/공간전하를 추가하는 것은 아니다. 이 예제에는 단자 전류 모델이 없다.

#### 1.1.7. 블록 F: interface_model과 interface_equation

계면에는 동일 위치에 놓인 서로 다른 region의 node 값이 존재한다.
`@r0`, `@r1`은 계면 양쪽 region을 가리키며, edge 양 끝의 `@n0`, `@n1`과 다르다.
r0/r1을 Si/Ox로 단정하기 전에 실제 계면의 region 순서를 확인한다.

$$
R_I=\psi_{r0}-\psi_{r1}=0,\quad
\frac{\partial R_I}{\partial\psi_{r0}}=1,\quad
\frac{\partial R_I}{\partial\psi_{r1}}=-1.
$$

`interface_model`은 이 식을 정의하고 `interface_equation`의 continuous 방식이
양쪽 보존 방정식을 결합하면서 추가 전위 관계를 적용한다.
현재처럼 자유 계면전하가 없는 경우, 같은 +x 방향을 기준으로:

$$
\psi_1=\psi_2,\qquad D_1=D_2,\qquad \varepsilon_1E_1=\varepsilon_2E_2.
$$

전위 연속 식 하나가 단독으로 전속 연속까지 표현하는 것은 아니다.
전속 보존은 결합한 영역 방정식에서 나온다. 전계는 일반적으로 연속이 아니다.
계면 트랩·고정 전하·전위 점프는 이 예제에 자동 포함되지 않는다.

#### 1.1.8. 블록 G: solve가 하는 일

첫 solve 설정은 dc, absolute_error=1.0, relative_error=1e-10,
maximum_iterations=30이다. dc는 시간에 따라 변하지 않는 상태를 뜻하며
바이어스 sweep이나 AC 정전용량 해석을 자동 수행하는 명령이 아니다.

전체 node 전위를 벡터 u로 묶으면 문제는 R(u)=0이다.

1. 현재 전위 추정값에서 edge 모델과 접촉·계면 잔차를 평가한다.
2. 위 편미분 모델을 사용해 Jacobian J=dR/du를 구성한다.
3. 선형 연립방정식 J(u^k) delta_u = -R(u^k)를 푼다.
4. default 갱신으로 u^(k+1)=u^k+delta_u를 만든다.
5. 갱신량 기반 수렴 조건을 확인하고 필요하면 반복한다.

현재는 상수 유전율과 선형 경계조건이므로 R(u)=A u-b인 선형 문제다.
이상적인 정확 연산에서는 한 Newton 보정으로 해에 도달할 수 있지만,
실제 로그에는 수렴 확인과 수치 정밀도 때문에 추가 반복이 나타날 수 있다.
후속 MOS 문제는 전하가 전위에 의존하므로 같은 선형성 가정을 적용할 수 없다.

absolute_error와 relative_error는 공식 API에서 갱신량 norm 및 상대 갱신량
기준으로 설명된다. 해석식 대비 물리 오차가 1e-10이라는 보증이 아니다.
예제의 허용오차를 향후 NMOS의 검증 기준으로 그대로 복사하지 않는다.

#### 1.1.9. 손으로 구한 첫 해석의 예상값

다음은 실행 측정값이 아니라, 첨부 구조와 첫 바이어스로 직접 유도한 값이다.
길이를 cm로 해석하고 t1=t2=0.5 cm, V_top=1 V, V_bot=0 V로 둔다.

$$
1=E_1t_1+E_2t_2
=D\left(\frac{t_1}{\varepsilon_1}+\frac{t_2}{\varepsilon_2}\right).
$$

따라서 단위 면적당 정전용량과 전속밀도는:

$$
C'=\left(\frac{t_1}{\varepsilon_1}+\frac{t_2}{\varepsilon_2}\right)^{-1}
=5.10822\times10^{-13}\ \mathrm{F/cm^2},\qquad D=C'\Delta V.
$$

| 값 | 해석식 예상 |
|---|---|
| D (+x) | 5.10822e-13 C/cm² |
| E1 | 0.52 V/cm |
| E2 | 1.48 V/cm |
| Si 영역 전압 강하 | 0.26 V |
| Ox 영역 전압 강하 | 0.74 V |
| 계면 전위 | 0.74 V |

$$
\psi(x)=\begin{cases}
1-0.52x,&0\le x\le0.5,\\
0.74-1.48(x-0.5),&0.5\le x\le1.
\end{cases}
$$

계면에서 기울기가 바뀌지만 전위는 연결된다. 물리적 전극 전하 밀도는
이 부호 기준에서 top에 +D, bot에 -D이다. 실제 get_contact_charge 출력은
1D 기하/면적 정규화와 contact 부호를 확인한 후 총전하 Q 또는 Q/A와 대조한다.
실제 면적 A가 주어지면 Q=C' A delta_V이다. 위 수치만으로 나노 소자 용량을 주장하지 않는다.

손계산을 더 단순화하면 미지수를 top, 계면, bot의 세 전위로 줄일 수 있다.
각 층 내부가 선형이므로 중간 격자점들을 제거한 동등한 문제는:

$$
\begin{bmatrix}
1&0&0\\
-a&a+b&-b\\
0&0&1
\end{bmatrix}
\begin{bmatrix}\psi_T\\\psi_I\\\psi_B\end{bmatrix}
=\begin{bmatrix}1\\0\\0\end{bmatrix},
\quad a=\varepsilon_1/t_1,\ b=\varepsilon_2/t_2.
$$

두 번째 행은 a(psi_I-psi_T)+b(psi_I-psi_B)=0, 즉 양쪽 전속의 보존이다.
따라서 psi_I=a/(a+b)=0.74 V이다.
이 3변수 표현은 손계산용이며, DEVSIM이 원래 mesh를 3 node로 줄인다는 뜻은 아니다.

#### 1.1.10. 첫 solve 이후의 코드

뒤쪽 코드는 유전율 변경·재해석, 전계 계산 방식 비교, 방정식 조회·삭제·복원,
배열 조작 등으로 나누어 읽는다. 마지막 출력 전체를 최초 물리 조건의 해로 취급하지 않는다.
파라미터를 바꾼 뒤 solve 전의 파생량은 기존 전위와 새 파라미터로 계산될 수 있어
새 경계값 문제의 해가 아니다.


#### 1.1.11. 테스트 실행: 환경·경로·로그

2026-09-24 관찰: 사용자 화면은 MINGW64이며 echo $? 출력은 49였다.
프로젝트 루트 run.log는 실제로 'Python ' 7바이트만 포함했다.
그 디렉터리에 cap2.py는 없고 설치본은 .venv/devsim_data/testing/cap2.py에 있다.
따라서 이번 실행을 cap2 성공으로 판단할 수 없다. 종료코드 49의 정확한 원인을
특정 Windows Python 실행 파일에 귀속할 정보는 없다. 이전 smoke test 성공과 구분한다.

VS Code에서 파일을 열어도 터미널의 작업 경로가 해당 파일의 폴더로 바뀌지는 않는다.
Windows Git Bash에서 WSL 경로를 보는 것과 Ubuntu Bash로 실행하는 것도 다르다.

1. PowerShell 또는 Git Bash에서 Ubuntu에 진입한다.

```bash
wsl -d Ubuntu
```

2. 이제부터 Ubuntu Bash에서 실행한다.

```bash
cd ~/projects/Project_Git/tcad_project
source .venv/bin/activate
pwd
command -v python
python -c 'import sys; print(sys.executable)'
ls .venv/devsim_data/testing/cap2.py
```

Python 경로는 /home/.../tcad_project/.venv/bin/python이어야 한다.
파일이 확인되지 않으면 다음 단계로 넘어가지 않는다.
MINGW64 터미널에서 가상환경 활성화 없이 그대로 실행하지 않는다.

3. 원본을 고유한 테스트 폴더에 복사하고 이동한다. 이전 결과를 덮어쓰지 않는다.

```bash
mkdir -p tmp/opensource_tests
tcad_cap_dir=$(mktemp -d "$PWD/tmp/opensource_tests/cap2-XXXXXX")
cp .venv/devsim_data/testing/cap2.py "$tcad_cap_dir/"
cd "$tcad_cap_dir"
sha256sum cap2.py
```

4. 화면과 로그를 동시에 보며 실행한다.

```bash
python -u cap2.py 2>&1 | tee run.log
tcad_cap_status=${PIPESTATUS[0]}
printf 'cap2 exit=%s\n' "$tcad_cap_status"
```

-u는 출력 버퍼링을 줄이고 tee는 화면과 파일에 함께 기록한다.
PIPESTATUS[0]는 Python 종료코드이며 파이프라인 직후 다른 명령 전에 저장한다.
echo $?만 쓰면 tee의 종료코드를 볼 수 있다.

기존의 > run.log는 표준출력을 파일로 보내고, 2>&1은 오류 출력도 합친다.
그래서 화면에 해석 로그가 안 보인다. 같은 로그 이름으로 재실행하면 덮어쓴다.

5. 종료 후 로그를 다시 읽는다.

```bash
head -n 40 run.log
tail -n 60 run.log
less run.log
```

less는 q로 종료한다. exit=0은 정상 종료일 뿐 물리/API 검증 통과가 아니다.
traceback이나 비영 종료코드가 있으면 먼저 실행 문제를 해결한다.

#### 1.1.12. API·물리 결과 판정

공식 cap2.py의 해당 블록 직후에 값을 조회한다.
파일 맨 끝에는 모델이 삭제되어 있으므로 마지막에 모든 물리량을 조회하면 안 된다.

| 구간 | 검증 항목 | 예상 결과 |
|---|---|---|
| 최초 solve | 전계·계면 전위 | E1=0.52, E2=1.48 V/cm, psiI=0.74 V |
| 두 epsilon을 epsilon0로 변경, solve 전 | 기존 전위 기반 D | 새 문제의 해가 아님; 양쪽 D 불일치 가능 |
| 변경 후 solve | 전압 분배 | E1=E2=1 V/cm, psiI=0.5 V, D=8.85e-14 C/cm² |
| 원래 물성 복원·solve | 기준해 회복 | 최초 전위·전계와 일치 |
| edge_average_model | 수동/내장 전계·미분 | 대응 배열이 허용오차 내 일치 |
| equation 삭제·재등록 | 목록·설정·해 | 삭제 시 제거, 재등록 후 동일 해 |
| get_matrix_and_rhs | 반환 구조·유한 값 | API 형식과 크기 확인; 모든 RHS가 0이라고 단정하지 않음 |
| 전체 전위 1.1, index 3을 0 | 값 변경 | 네 번째 원소만 0 |
| init_from=testing | node 값 복사 | testing과 같은 배열; 물리해 아님 |
| nv 복원 후 solve | 저장 전위 복원 | 기준 물리해 회복 |
| testcopy1 | 전계 복사·일부 변경 | 첫 -1, 끝 +2, 중간 기존값 유지 |
| testcopy2 | 전계-복사본 | E=0.52 기준 첫 1.52, 끝 -1.48, 중간 0 |
| 모델 삭제 | 모델 목록 | 해당 모델 제거; 이후 이 상태로 solve하지 않음 |
| array/list/bytes | 자료형별 입력 | 숫자 변환과 raw byte 재해석 구분 |

전계 부호와 값은 edge 방향을 확인한 후 비교한다.
bytes의 약 4.94e-324 출력은 정수 비트 패턴을 double로 해석한 값이며 물리량이 아니다.
후반 6원소·48바이트 전제는 원본 mesh와 자료형에 의존하므로 mesh 변경 후 그대로 쓰지 않는다.
삭제·변경 상태에서 재해석하려면 새 프로세스에서 원본을 처음부터 실행한다.


원본은 print와 solver 로그를 출력하며 설명문·그래프·자동 PASS/FAIL 보고서를 만들지 않는다.
수식 유도는 문서의 역할이고 실행 코드는 그 수치해와 API 동작을 보여준다.

다음은 테스트 복사본의 첫 solve 직후에 넣을 수 있는 검사 예시다.
원본 실행 로그를 보존한 뒤 cap2_review.py 등 별도 복사본에 적용한다.
파라미터 변경이나 모델 삭제 이후 파일 맨 끝에 넣지 않는다.

```python
import numpy as np
import devsim

print("[CAP-01] first solve: analytic potential comparison")
for r in devsim.get_region_list(device=device):
    x = np.asarray(devsim.get_node_model_values(
        device=device, region=r, name="x"))
    measured = np.asarray(devsim.get_node_model_values(
        device=device, region=r, name="Potential"))
    expected = np.where(x <= 0.5, 1.0 - 0.52*x,
                        0.74 - 1.48*(x - 0.5))
    error = float(np.max(np.abs(measured - expected)))
    print(f"region={r}, max_abs_error_V={error:.3e}")
    np.testing.assert_allclose(measured, expected, rtol=1e-8, atol=1e-10)
print("[PASS] CAP-01")
```

이 허용오차는 현재 선형 예제의 시작 기준이며 다른 소자에 그대로 적용하지 않는다.
위 코드는 이번 문서 수정에서 실행하지 않았다. assertion 통과 때만 PASS가 표시된다.
다른 블록도 단계 라벨 → 조회값 → 예상값 → assertion → PASS로 구성한다.

| 테스트 | 상태 | 판정 |
|---|---|---|
| 기존 설치 smoke test | 이전 화면에서 완료 확인 | 정량 검증과 별개 |
| 2026-09-24 루트 실행 | exit=49, 로그 'Python ' | 실패/해석 미확인 |
| CAP-01 및 후반 API assertion | 미실행 | 미판정 |

### 1.2. diode_1d.py: 1D PN 접합

#### 1.2.1. 범위와 출처

확인일: 2026-09-23. 분석 기준 환경은 DEVSIM 2.11.0이다.
최초 분석은 아래 공식 main 소스의 호출 흐름·구조·초기화에 대한 정적 분석이었다.
이후 diode 실행 및 순방향 I-V·전류 보존 경향 확인을 완료했다. 공식 main과 설치본의 전체 동일성은 별도 검증하지 않았다.

- [diode_1d.py](https://github.com/devsim/devsim/blob/main/examples/diode/diode_1d.py)
- [diode_common.py](https://github.com/devsim/devsim/blob/main/examples/diode/diode_common.py)
- [simple_physics.py](https://github.com/devsim/devsim/blob/main/python_packages/simple_physics.py)
- [model_create.py](https://github.com/devsim/devsim/blob/main/python_packages/model_create.py)
- 위 파일의 라이선스 표시는 Apache-2.0이다. main은 변할 수 있으므로 상세 수식 대조 시 설치본을 우선한다.
- 프로젝트 범위: 전위 초기화, Poisson/전자·정공 연속방정식 연결, 접촉 조건, DC sweep.
  현재 기록은 정적 코드 분석과 테스트 설계까지이며, 상세 테스트는 미실행이다.

#### 1.2.2. 파일별 역할과 호출 흐름

| 파일 | 역할 |
|---|---|
| diode_1d.py | 실행 순서, lifetime 지정, solve, bias sweep와 전류 출력 |
| diode_common.py | mesh, 도핑, 초기 전위 및 drift-diffusion 준비 |
| simple_physics.py | 물성, 전하·재결합·방정식·접촉 모델 |
| model_create.py | 모델 생성 및 미분 등록을 감싼 공통 함수 |

```text
CreateMesh → SetParameters → lifetime 지정 → SetNetDoping
→ InitialSolution → 전위만 미지수인 첫 DC solve
→ DriftDiffusionInitialSolution → 결합된 평형 DC solve
→ 접촉 bias 변경 → DC solve → 전자·정공·총전류 출력
```

주 실행 파일의 그래프 작성 부분은 주석 처리되어 있으므로 실행되는 코드와 구분한다.
공통 물리 코드에는 drift-diffusion 구성 중 SRH 생성 호출이 있다.
따라서 파일 머리말의 재결합 관련 주석만 보고 재결합이 없다고 판단하지 않는다.

#### 1.2.3. 구조·도핑과 capacitor의 차이

공식 main의 CreateMesh는 x=0부터 1e-5 cm(100 nm)까지 단일 Si region을 만든다.
접합 기준 위치는 0.5e-5 cm(50 nm)이며 양 끝 contact는 top과 bot이다.
중앙 tag는 mesh 기준점이며 별도의 재료 interface를 생성하지 않는다.

SetNetDoping은 왼쪽 acceptor, 오른쪽 donor의 계단형 분포를 정의한다.
각 측의 농도 크기는 1e18 cm^-3이며 NetDoping=Donors-Acceptors이다.
접합점의 정확한 값은 step(0) 정의를 확인해야 하며 추측하지 않는다.

cap2의 두 유전체 계면과 달리, 여기서는 같은 Si 내부에서 도핑 부호가 바뀌는 PN 접합이다.
따라서 PN 접합이라는 이유만으로 interface_model을 추가하는 구조가 아니다.

#### 1.2.4. 해석 단계와 미지수

첫 단계는 Potential만 독립 미지수로 둔다. 그러나 carrier가 없는 것은 아니다.
simple_physics의 평형 모델에서는 n과 p를 전위의 함수로 정의한다.

$$
n=n_i\exp(\psi/V_T),\qquad p=n_i^2/n,\qquad
\rho=q(p-n+N_D-N_A).
$$

Poisson 방정식은 div(D)-rho=0이다. 코드의 node 항은 물리적 rho의 음수이며,
cap2의 빈 체적 소스 항과 다르다. 전하가 전위에 의존하므로 첫 단계부터 비선형이다.

다음 단계에서 Electrons와 Holes를 독립 미지수로 만들고,
첫 전위 해의 IntrinsicElectrons/IntrinsicHoles 값으로 초기화한다.
그 뒤 전위·전자·정공 방정식을 함께 푼다.

여기서 IntrinsicElectrons라는 모델 이름은 도핑된 영역의 농도가 항상 n_i라는 뜻이 아니다.
양단 외부 bias가 0이어도 접촉의 도핑 의존 전위와 built-in potential은 존재할 수 있다.

#### 1.2.5. 현재 분석의 한계

설치본의 물성값·접촉 식·전류 이산화·SRH 항 및 전류 정규화를 상세 대조하지 않았다.
공식 예제의 고농도 및 상수 물성 가정은 보정된 제조 소자 모델로 간주하지 않는다.
손계산 가능한 평형 근사와 수치해의 차이는 후속 분석에서 조건을 명시해 해석해야 한다.


#### 1.2.6. Region과 파일별 코드 위치

주 실행 파일은 diode_1d.py이며, 수식은 호출된 함수의 정의부에 있다.

| 주 실행 파일의 호출 | 실제 정의 | 분석 내용 |
|---|---|---|
| diode_common.CreateMesh | diode_common.py: CreateMesh | 격자·region·contact |
| diode_common.SetParameters | diode_common.py → simple_physics.py: SetSiliconParameters | 300 K 물성 |
| diode_common.SetNetDoping | diode_common.py: SetNetDoping | Acceptors, Donors, NetDoping |
| diode_common.InitialSolution | diode_common.py → simple_physics.py: CreateSiliconPotentialOnly/Contact | 전위 방정식·접촉 |
| diode_common.DriftDiffusionInitialSolution | diode_common.py → simple_physics.py: CreateSiliconDriftDiffusion/AtContact | 결합 방정식·carrier 접촉 |
| CreateElectronCurrent/CreateHoleCurrent | simple_dd.py | 전류 이산화 |
| Create*Model, CreateSolution | model_create.py | 모델과 미분 등록 도우미 |

추가 출처: [simple_dd.py](https://github.com/devsim/devsim/blob/main/python_packages/simple_dd.py).
이하 함수·수식 분석은 공식 소스 기준이며 설치본과의 일치 여부는 실행 전에 대조한다.

```text
x [cm]       0                   0.5e-5                    1e-5
x [nm]       0                     50                       100
             │──────────────────────┼────────────────────────│
contact      top                                             bot
region       └──────────────── MyRegion ──────────────────────┘
material                              Si
doping       P형                     │                     N형
             NA=1e18 cm^-3           │          ND=1e18 cm^-3
NetDoping    -1e18 cm^-3             │             +1e18 cm^-3
                                    mid
                         도핑 접합이며 재료 interface 아님
```

SetNetDoping의 식은 NA(x)=1e18 step(xj-x), ND(x)=1e18 step(x-xj),
Nnet=ND-NA이다. xj=0.5e-5 cm이며 정확히 x=xj에서의 값은 step(0)을 확인한다.
접합 부근에는 mesh를 조밀하게 배치한다. cap2와 달리 Si region을 두 개 만들지 않는다.

#### 1.2.7. Poisson 방정식과 접촉 조건

정의부는 simple_physics.py의 CreateSiliconPotentialOnly와
CreateSiliconPotentialOnlyContact이다. 고유 carrier 농도는 n_int,
격자점 인덱스는 j로 표기해 혼동을 피한다.

$$
n=n_{\mathrm{int}}e^{\psi/V_T},\quad
p=n_{\mathrm{int}}e^{-\psi/V_T},\quad
\rho=q(p-n+N_D-N_A),\quad V_T=kT/q.
$$

IntrinsicElectrons는 위 n(psi)의 모델 이름이다. 농도가 항상 고유 농도라는 뜻이 아니다.
코드의 PotentialIntrinsicCharge는 -rho이며 kahan3는 합산의 수치 안정성을 위한 함수다.

$$
D=-\varepsilon\frac{d\psi}{dx},\qquad
\frac{dD}{dx}-\rho=0.
$$

단면적으로 나눈 내부 node 제어체적의 잔차와 중심 Jacobian 계수는:

$$
R_j=-a_L\psi_{j-1}+(a_L+a_R)\psi_j-a_R\psi_{j+1}
-\rho(\psi_j)\Delta x_j=0,\quad a_{L,R}=\varepsilon_{L,R}/h_{L,R},
$$

$$
\frac{d\rho}{d\psi}=-\frac{q(n+p)}{V_T},\qquad
\frac{\partial R_j}{\partial\psi_j}
=a_L+a_R+\frac{q(n_j+p_j)}{V_T}\Delta x_j.
$$

Delta x_j는 node 제어체적 길이다. 전위에 따라 전하와 Jacobian이 바뀌므로
첫 전위 해석부터 비선형이며 log_damp 방식으로 큰 갱신을 완화한다.

접촉은 이상화한 준중성·평형 조건이다. 완전 이온화·비축퇴 통계에서
n_c-p_c=Nnet, n_c p_c=n_int²이므로:

$$
n_c=\frac{N_{\mathrm{net}}+\sqrt{N_{\mathrm{net}}^2+4n_{\mathrm{int}}^2}}2,\quad
p_c=\frac{-N_{\mathrm{net}}+\sqrt{N_{\mathrm{net}}^2+4n_{\mathrm{int}}^2}}2.
$$

이는 수학적 표현이다. 실제 코드는 다수 carrier와 질량작용식을 사용하고
작은 양의 보정도 포함한다. 직접 뺄셈으로 소수 carrier를 구하면 유효숫자 손실이 생길 수 있다.

접촉 전위는 n형에서 bias+V_T ln(n_c/n_int), p형에서 bias-V_T ln(p_c/n_int)이다.
외부 bias가 모두 0이어도 내부 전위차는 존재한다.

$$
V_{\mathrm{bi}}\simeq V_T\ln\left(\frac{N_A N_D}{n_{\mathrm{int}}^2}\right).
$$

300 K, NA=ND=1e18 cm^-3, n_int=1e10 cm^-3이면 약 0.95 V이다.
p측 약 -0.477 V, n측 약 +0.477 V이고 평형 전계는 주로 N→P(-x) 방향이다.
모두 예제의 가정에서 유도한 예상값이며 실행 측정값이나 실측 보정값이 아니다.

#### 1.2.8. Drift-diffusion과 전류

DriftDiffusionInitialSolution은 Electrons, Holes를 독립 미지수로 만들고
첫 전위 해의 농도를 초기값으로 사용한다. 이후 미지수는 psi,n,p이고
바이어스 인가 시 소자 전체에 np=n_int²를 강제하지 않는다.

연속체 전류식은:

$$
J_n=q\mu_n nE+qD_n\frac{dn}{dx},\quad
J_p=q\mu_p pE-qD_p\frac{dp}{dx},\quad D_{n,p}=\mu_{n,p}V_T.
$$

simple_dd.py에서는 Scharfetter–Gummel 이산화를 사용한다.
edge n0→n1에서 v=(psi0-psi1)/V_T, 길이를 h로 두면:

$$
B(v)=\frac{v}{e^v-1},\quad B(0)=1,\quad B(-v)=B(v)+v,
$$

$$
J_n=\frac{q\mu_n V_T}{h}\{n_1 B(-v)-n_0 B(v)\},\quad
J_p=\frac{q\mu_p V_T}{h}\{p_0 B(-v)-p_1 B(v)\}.
$$

실제 식은 B(-v) 항등식과 kahan3를 이용한 동등한 형태다.
v=0에서 확산 전류로 환원되고 평형 Boltzmann 분포에서는 전류가 상쇄된다.

순 재결합 U=R-G의 SRH 모델은:

$$
U=\frac{np-n_{\mathrm{int}}^2}{\tau_p(n+n_1)+\tau_n(p+p_1)}.
$$

| equation | 미지수 | edge 항 | node 항 | time 항 |
|---|---|---|---|---|
| PotentialEquation | Potential | D | -rho | 없음 |
| ElectronContinuityEquation | Electrons | Jn | -qU | -qn |
| HoleContinuityEquation | Holes | Jp | +qU | +qp |

DC에서는 dJn/dx-qU=0, dJp/dx+qU=0이므로 d(Jn+Jp)/dx=0이다.
개별 carrier 전류가 위치에 따라 변해도 총전류는 보존되어야 한다.
전위는 log_damp, 농도는 positive 갱신을 사용한다.
주 실행 파일의 taun,taup=1e-8 s 설정은 공통 기본값을 덮어쓴다.
SRH 포함 여부는 머리말 주석이 아니라 실제 함수 호출로 판단한다.

#### 1.2.9. 결합 solve와 sweep

u=(psi,n,p)에 대해 R(u)=0을 구성하고 J delta_u=-R을 푼다.
교차 미분이 있는 결합 문제이지 세 독립 문제를 각각 푸는 것이 아니다.

순서는 potential-only 평형해 → DD 초기화 → DD 평형해 → bias별 해석이다.
top에 0~0.5 V를 0.1 V씩 인가하고 매번 solve하며 이전 해를 초기값으로 활용한다.
이는 시간 과도 해석이 아니다. P측 양의 bias는 순방향으로 주입 증가가 예상된다.

PrintCurrents 출력은 contact, bias, 전자 전류, 정공 전류, 총전류 순이다.
diode_1d.dat는 최종 bias의 공간 상태이며 전체 I-V 로그를 대체하지 않는다.
원본의 그래프 코드는 주석 상태이므로 자동 그래프 생성을 기대하지 않는다.

상수 이동도·비축퇴·고농도 가정의 한계를 보고하고 전류밀도와 단자 전류의
기하 정규화를 구분한다. epsilon0 단위는 F/cm이며 소스 주석도 차원 분석으로 검토한다.


#### 1.2.10. 테스트 실행과 bias별 출력

Ubuntu Bash에서 독립 실행한다. cap2와 Python 프로세스를 공유하지 않는다.

```bash
cd ~/projects/Project_Git/tcad_project
source .venv/bin/activate
command -v python
ls .venv/devsim_data/examples/diode/diode_1d.py .venv/devsim_data/examples/diode/diode_common.py
```

파일이 확인된 경우에만 계속한다.

```bash
mkdir -p tmp/opensource_tests
tcad_diode_dir=$(mktemp -d "$PWD/tmp/opensource_tests/diode-XXXXXX")
cp .venv/devsim_data/examples/diode/diode_1d.py "$tcad_diode_dir/"
cp .venv/devsim_data/examples/diode/diode_common.py "$tcad_diode_dir/"
cd "$tcad_diode_dir"
sha256sum diode_1d.py diode_common.py
python -u diode_1d.py 2>&1 | tee run.log
tcad_diode_status=${PIPESTATUS[0]}
printf 'diode exit=%s\n' "$tcad_diode_status"
```

diode_common.py는 주 실행 파일과 같은 폴더에 둔다. 공통 physics는 venv 패키지를 사용한다.
원본 PrintCurrents의 열은 contact, bias, electron current, hole current, total current 순이다.
반복 오차는 solver 과정이며 contact별 숫자는 해당 bias의 결과다.
원본은 이 숫자의 물리적 의미나 PASS/FAIL, 그래프를 자동 설명하지 않는다.

원본 로그를 보존한 뒤 diode_1d_review.py 복사본에서 단계 라벨을 추가한다.
아래는 삽입 위치 예시이며 새로운 sweep 루프를 추가하는 코드가 아니다.

```python
# 기존 while 루프 앞:
print("contact bias_V electron_current hole_current total_current")

# 기존 while 루프 안에서 set_parameter 다음, solve 앞:
print(f"[DIODE] top_bias={v:.2f} V: solve start")

# 기존 solve 성공 직후, PrintCurrents 앞:
print(f"[DIODE] top_bias={v:.2f} V: solve returned")
```

위 코드는 주석에 지정된 위치에 나누어 배치한다. solve returned는 물리 검증 PASS가 아니다.
실패 예외를 무시하거나 이전 bias 전류를 현재 bias의 결과로 저장하지 않는다.
종료코드 확인 후 run.log를 열고 각 0~0.5 V 단계의 수렴과 전류를 대응시킨다.

#### 1.2.11. 결과 판정과 산출물

평형 상태는 sweep 이전, 각 bias 상태는 solve 직후에 조회한다.
Potential, NetDoping, x, carrier 농도, edge 및 contact 전류를 관찰한다.
첫 potential-only 단계에서는 독립 Electrons/Holes가 아닌
IntrinsicElectrons/IntrinsicHoles를 사용한다.

| 조건 | 예상 관계 | 판정 주의 |
|---|---|---|
| 구조·도핑 | 단일 Si, 왼쪽 P/오른쪽 N | step(0) 확인 |
| 평형 전위 | N측이 P측보다 약 0.95 V 높음 | 예제 접촉·통계 가정의 근사 |
| 평형 전계 | N→P | edge 방향 확인 |
| 평형 총전류 | 거의 0 | 절대오차 필요 |
| 순방향 sweep | 주입 전류 크기 증가 | 실패 bias와 0 근처 잡음 구분 |
| 총전류 보존 | 일관된 단자 부호에서 Itop+Ibot≈0 | 개별 carrier 전류 보존 강제 금지 |
| 출력 | diode_1d.dat와 전류 로그 | dat는 마지막 상태; 그래프 자동 생성 안 됨 |

Shockley 식과의 정확한 일치를 API 테스트의 통과 조건으로 삼지 않는다.
비교는 |계산값-기준값| <= atol + rtol*|기준값|로 수행하며 atol은 단위별로 선정한다.
전위·전속·전류에 같은 atol을 무조건 쓰지 않는다.
정확한 테스트 허용오차는 비교 단위·solver 설정을 확인한 뒤 실행 전에 정하고 기록한다.

| 테스트 | 파일 버전·해시 | 예상값 | 실제값 | 허용오차 | 판정·로그 |
|---|---|---|---|---|---|
| DIODE-DC | 상단 실행 기록 참조; 해시 별도 보관 필요 | 위 표 | 순방향 I-V·전류 보존 경향 확인 | 정식 자동 검증의 단위별 허용오차는 후속 선정 | 경향 확인 완료; 전체 정량 assertion 통과는 미확정 |

tmp 원시 로그는 기본 Git 제외다. 검토한 요약·기준 데이터만 선별하여 보관한다.

원본 실행만으로 다음 산출물이 모두 만들어지는 것은 아니다.

| 산출물 | 내용 | 목적 |
|---|---|---|
| run.log | 수렴·오류·bias 라벨 | 실패 위치 확인 |
| iv.csv | bias, 각 접촉의 전자·정공·총전류, 수렴 상태 | I-V와 전류 보존 |
| equilibrium.csv | 평형 x, 전위, 농도 | 내장 전위·공핍 분포 |
| current_conservation.csv | bias별 Itop+Ibot와 오차 | 보존 검사 |
| diode_1d.dat | 원본이 생성하는 최종 공간 상태 | 마지막 bias 분석 |
| figures | 전위·농도·I-V 그래프 | 시각적 해석 |

CSV·그래프·assertion은 테스트 복사본 또는 별도 검증 코드에서 구현한다.
평형 상태는 sweep 전, bias별 결과는 각 solve 직후 추출해야 한다.
정상 종료, solver 수렴, 물리 타당성을 각각 따로 판정한다.

### 1.3. MOSFET 예제: 구조와 공간 분포

#### 1.3.1. 분석 대상과 파일 역할

실행·분석 대상은 `tmp/opensource_tests/mos-7yxXS6/`의 `mos_2d.py`,
`mos_2d_create.py`와 `run_first.log` 및 시각화 출력이다.
영역·도핑·접촉·산화막/반도체 계면을 구성하고, 전위 해석에서 carrier 연속방정식을 포함한
drift-diffusion 해석으로 진행하는 초기화 과정을 확인했다.

`mos_2d_create.py`는 mesh·영역·접촉·도핑을, `mos_2d.py`는 물리 모델 등록과 solve를 담당한다.
후속 Gmsh 실험은 `gmsh_mos2d_create.py`로 mesh를 불러온다. 내장 mesh 예제와 Gmsh 예제의
치수·mesh가 같다고 가정하지 않고 실행별 생성 파일을 구분한다.

#### 1.3.2. 구조·좌표·도핑 해석

내장 mesh 생성 코드에서 bulk 표면은 y=0, bulk 깊이는 양의 y, oxide와 gate는 음의 y 방향이다.
따라서 화면 아래 중앙에 gate가 보이는 것은 좌표계에 따른 배치이며 구조가 잘못 뒤집혔다는 뜻이 아니다.
`bulk_doping=-1e15`, source/drain `1e19`, gate `1e20`의 설정은 순 도핑의 부호와
고농도 영역을 구분하는 근거다. 이 수치를 다른 Gmsh 실행에 자동으로 대입하지 않는다.
gate 길이·oxide 두께·접합 깊이·채널 mesh 간격을 구분해야 하며, 화면 픽셀 길이로 실제 치수를 읽지 않는다.

#### 1.3.3. 전위 해석과 접촉·계면 조건

반도체에는 전하를 포함한 Poisson 방정식, 산화막에는 해당 유전체 전위 방정식을 적용한다.
접촉은 외부 bias를 주는 경계이고, bulk/oxide 및 gate/oxide는 내부 계면이다.
접촉 전위에는 carrier·도핑에 따른 내장 전위 기준이 포함될 수 있으므로 0 V bias를
전체 Potential=0으로 해석하지 않는다. 계면 전위 연속성과 전속/전하 조건은 별개의 검사 대상이다.

#### 1.3.4. Drift-diffusion 초기화와 수렴

먼저 Potential-only 상태를 풀고, 그 결과의 carrier 모델로 Electrons/Holes를 초기화한 뒤
전자·정공 연속방정식을 결합한다. 이는 처음부터 큰 bias의 결합 문제를 푸는 것과 다른 초기화 경로다.
로그에서는 방정식 수와 Newton 반복 횟수를 구분한다. solve 정상 종료만으로 mesh 독립성이나
모델의 실험적 정확도가 증명되지는 않는다. 전류 보존은 solve 수렴과 별도 확인한다.

#### 1.3.5. Potential·logElectrons 시각화 해석

ParaView에서 Potential과 logElectrons를 확인했다. Potential에는 내장 전위가 포함되므로
외부 단자 전압과 표시값이 반드시 같지는 않다. 고농도 source/drain과 gate 영역의 높은 전자농도,
bulk 내부의 농도 차이를 구분했다. 산화막에서 carrier 모델이 없으면 partial/빈 영역이 나타날 수 있다.
`logElectrons`는 코드의 `log(Electrons)/log(10)`이다. 농도를 cm^-3로 사용하는 모델에서
표시값 16은 10^16 cm^-3에 해당하며, 값 16 cm^-3를 뜻하지 않는다.
전체 색 범위가 여러 decade이면 계면의 변화가 화면에서 작게 보일 수 있다.
전위는 바뀌었지만 고농도 영역의 색이 거의 같다는 관찰만으로 bias가 적용되지 않았다고 결론내리지 않는다.

#### 1.3.6. Channel 판정과 분석 한계

전자농도가 높다는 사실만으로 gate가 유도한 inversion channel 또는 pinch-off를 확정하지 않았다.
VGS>Vth는 source 쪽 반전의 기본 조건이고, VGD>Vth는 단순 장채널 관점에서 drain 끝까지
반전이 유지되는 조건이다. Vg=Vd라는 사실만으로 채널 전체가 없다고 단정할 수 없다.
정량 판정에는 계면의 n/p·도핑·표면전위와 Gate 변화에 따른 프로파일이 필요하다.
이번에는 이러한 threshold 추출까지 수행하지 않고 구조·공간 분포 이해로 종료했다.

### 1.4. Bias Sweep: 단자 특성과 전류 보존

#### 1.4.1. 실행 대상과 고정 조건

대상: `tmp/opensource_tests/mos-bias-L1PTIK/gmsh_mos2d_review.py`,
`run_bias_review.log`, `bias_review/iv.csv`, `iv_summary.csv`, `id_vd.png`.
Gate를 0.5 V로 설정한 뒤 고정하고 Drain을 0.0–0.5 V까지 0.1 V 간격으로 증가시켰다.
Source/body는 0 V이며 상수 이동도 조건은 전자 400, 정공 200 cm²/(V·s)이다.

#### 1.4.2. Ramp와 상태별 출력 흐름

평형 → Gate ramp → Gate 고정 후 Drain ramp 순서로 진행한다.
`rampbias`는 이전 수렴해를 다음 bias 초기값으로 사용하며, 실제 수렴점의 bias를 출력과 함께 저장한다.
`gmsh_mos2d_review.py`의 stage 및 저장 callback은 각 상태의 전류와 VTM을 연결한다.
마지막에 한 번만 `write_devices`를 호출하면 중간 상태를 복원할 수 없으므로 solve 직후 저장이 필요하다.
CSV의 실제 bias를 우선하며 자동 step 조정이 있는 실행에서는 파일 번호만으로 bias를 추정하지 않는다.

#### 1.4.3. VTM 번호와 bias 대응

`000_equilibrium.vtm`은 평형, `001_gate_ramp.vtm`은 Gate 인가 후 Drain 0 V,
`002`–`006_drain_ramp.vtm`은 Drain 0.1–0.5 V 상태다.

| 상태 | Gate [V] | Drain [V] | 비교 목적 |
|---|---:|---:|---|
| 000_equilibrium | 0 | 0 | 기준 상태 |
| 001_gate_ramp | 0.5 | 0 | Gate 효과 |
| 002–006_drain_ramp | 0.5 | 0.1–0.5 | 고정 Gate에서 Drain 효과 |

#### 1.4.4. Potential·전자농도 변화

Potential은 Drain 쪽에서 증가하고 좌우 비대칭이 커졌으며, 전자농도 분포도 Drain 쪽에서 재분포했다.
이는 bias 적용의 공간적 응답이지, 이 그림만으로 threshold나 channel 형성을 정량 판정한 것은 아니다.

Drain 쪽 Potential은 높아지지만 그 주변 logElectrons가 반드시 같이 높아지는 것은 아니다.
비평형에서는 carrier 분포가 전위뿐 아니라 연속방정식·준페르미 준위에 의해 정해지므로
평형의 전위-농도 관계를 모든 bias에 그대로 적용하지 않는다.
Gate 0.5 V를 유지한 비교와 평형→Gate 인가 비교를 섞으면 원인 해석이 달라진다.

#### 1.4.5. I-V와 전류 보존 잔여값

Id는 Drain bias에 따라 증가했고 -Is와 거의 겹쳤다. 전류 보존 잔여값은
Ig+Id+Is+Ib로 계산하며 그래프의 최대 절댓값은 약 2.6e-12 raw API units였다.
축의 1e-12는 눈금에 곱하는 과학적 표기이며 A 단위를 부여하는 표시가 아니다.
2D 폭 정규화가 확정되지 않아 전류는 raw API units로 기록한다.

왼쪽 그래프는 개별 단자 전류, 오른쪽은 부호를 포함해 합한 잔여값이다.
오른쪽이 거의 0이라고 해서 Id가 bias에 무관하게 일정하다는 뜻이 아니다.
Ig/Ib가 작으면 Id와 -Is가 겹치지만, 보존 검사는 네 단자 모두를 포함해야 한다.
0 V 부근에는 상대오차의 분모가 작으므로 절대 잔여값을 함께 기록한다.

#### 1.4.6. Gate 추가 진단과 채널 판정

별도 channel 확인 탐색(`tmp/opensource_tests/channel-check-20260928/`)은
Drain 0.05 V에서 Gate 0–2 V를 변화시킨 추가 진단이며, 아래 mobility 비교의 Drain sweep과 구분한다.
기준 상태부터 전자가 많은 위치에서는 농도 증가만으로 Vth를 추출할 수 없다.
계면 line cut과 정식 threshold 추출은 이번 분석의 완료 조건에 포함하지 않았다.

#### 1.4.7. 출력 문제와 재현 시 주의점

ParaView 파일 창의 `...drain_ramp.vtm` Group은 여러 번호 파일을 묶은 표시일 수 있으므로
그룹을 펼쳐 실제 파일을 확인한다. Pipeline에서 파일을 선택하는 것과 눈 아이콘으로 표시하는 것은 다르다.
동일 위치의 두 상태를 동시에 표시하면 비교가 가려질 수 있으므로 한 상태씩 표시한다.
로드 실패는 Output Messages와 VTM 내부 VTU 경로를 확인하며, 캡처만으로 원인을 확정하지 않는다.

### 1.5. Mobility 보정: 이동도와 I-V 경향

#### 1.5.1. 실행 대상과 비교 조건

대상: `tmp/opensource_tests/mos-mobility-x4gvGg/gmsh_mos2d_kla.py` 및
`run-kla-plot-CR1TB3/run_review.log`, `run-kla-plot-CR1TB3/mobility_review/`의
`iv_mobility.csv`, 그래프와 `kla_drain_000`–`005.vtm`.
Gate 0.5 V 고정, Drain 0.0–0.5 V 조건이며 mobility 실험에 추가 Gate DOE는 적용하지 않았다.
설치본의 `Klaassen.py`, `mos_physics.py`, `ramp.py`, `simple_physics.py`를 모델 근거로 사용한다.

#### 1.5.2. Bulk·표면·속도포화 모델 연결

전자 이동도는 bulk Klaassen 모델에서 표면 보정, 속도포화 보정으로 이어진다.
| 코드/함수 | 생성·사용 물리량 | 확인할 의미 |
|---|---|---|
| Set_Mobility_Parameters, Klaassen_Mobility | mu_bulk_e, mu_bulk_h | bulk carrier 이동도 |
| CreateNormalElectricFieldFromCurrentFlow | Eparallel, Enormal | 전류 방향 기준 전계 성분 |
| Philips_Surface_Mobility | mu_e_0 | 표면 보정 후 이동도 |
| Philips_VelocitySaturation | mu_vsat_e | 평행 전계에 따른 속도포화 보정 |
| CreateElementModel2d | mu_ratio, mu_surf_ratio | bulk 대비 상대 변화 |

이 예제의 Enormal은 전류 방향에서 정의되므로 모든 위치에서 기하학적 oxide 법선과
동일하다고 가정하지 않는다. bulk 전체의 색 변화를 실제 계면 산란만의 효과로 단정하지 않는다.

#### 1.5.3. Element 전류와 접촉 방정식

`CreateElementElectronCurrent2d(..., "mu_vsat_e")`로 보정된 전자 전류를 만들고
`CreateElementElectronContinuityEquation`에 연결한다. body/drain/source에는
`CreateElementContactElectronContinuityEquation`을 적용한다.
이동도 그림만 추가하는 것과 실제 연속방정식의 전류 모델을 교체하는 것은 다르다.
정공까지 동일한 전자 보정 경로로 해석하지 않는다.

#### 1.5.4. I-V 정량 비교와 인과 해석 한계

| Vd [V] | 상수 이동도 Id [raw] | 보정 모델 Id [raw] | 상대 차이(근사) |
|---|---:|---:|---:|
| 0.1 | 0.43759 | 0.62765 | +43.4% |
| 0.2 | 0.93909 | 1.00942 | +7.5% |
| 0.3 | 1.53443 | 1.33753 | -12.8% |
| 0.4 | 2.22799 | 1.64847 | -26.0% |
| 0.5 | 3.01878 | 1.94932 | -35.4% |

보정은 모든 bias에서 전류를 감소시키는 상수 배율이 아니다. 낮은 bias에서는 전류가 더 크지만,
높은 bias에서는 증가가 억제되는 경향을 확인했다. 모델 및 이산화·solver 조건의 차이도 있으므로
이를 특정 산란항 하나의 순수 효과나 소자 설계 최적화 성과로 보고하지 않는다.

#### 1.5.5. Solver·전류 보존 비교

잔여값의 최대 절댓값은 그래프상 약 1.34e-9 raw이며, 해당 Id 약 0.628에 비하면 약 2.1e-9이다.
상수 이동도 실행과 solver 상대 허용오차도 다르므로 잔여값 크기만으로 물리 모델 정확도를 순위화하지 않는다.

#### 1.5.6. Bulk·표면 이동도 관찰

- `mu_bulk_e_Node`: 대략 61–1400 cm²/(V·s) 표시 범위에서 고농도 영역의 낮은 이동도를 확인했다. Drain에 따른 색 변화는 작았다.
- `mu_e_0`: 표면 보정 후 이동도. 0 V와 유한 Drain bias에서 삼각형 패턴 차이가 있었다. 전류 방향을 이용하는 모델의 경우 0 근처 방향 민감도가 원인일 수 있으나, 그림만으로 원인을 확정하지 않는다.

고농도 source/drain에서 bulk 이동도가 낮고 가볍게 도핑된 bulk 내부에서 높은 분포를 보였다.
Drain 변화보다 도핑에 따른 공간 차이가 큰 관찰이며, 모든 node 값이 정확히 일정했다는 검증은 아니다.
0 V 패턴의 원인을 확정하려면 전류 크기·방향 및 수렴 허용오차/mesh 민감도를 추가 확인해야 한다.

#### 1.5.7. 이동도 비율과 속도포화 관찰

- `mu_surf_ratio = mu_e_0/mu_bulk_e`: 0.1, 0.3, 0.5 V에서 전체 경향은 유사하고 국소 변화가 보였다. 비율 1은 bulk 대비 추가 감소가 작다는 뜻이지 절대 이동도가 높다는 뜻이 아니다.
- `mu_ratio = mu_vsat_e/mu_bulk_e`: Drain 증가에 따라 중앙의 Drain 쪽과 오른쪽에 낮은 비율 영역이 확대되는 경향을 확인했다.
- `mu_vsat_e`: 속도포화 보정 후 이동도 역시 Drain 쪽 저하 영역이 확대됐다. 속도포화 모델의 작동 경향이며 실제 속도 또는 단자 전류의 완전 포화를 입증한 것은 아니다.

ratio는 무차원, 절대 이동도는 모델의 cm²/(V·s) 단위로 구분한다.
낮은 ratio가 나타나는 곳의 전자농도와 전류 경로를 같이 보아야 단자 전류에 미치는 중요도를 판단할 수 있다.
bulk 전체의 단순 평균 이동도만으로 Id 변화율을 설명하지 않는다.

#### 1.5.8. 색 범위·mesh·데이터 위치의 한계

001/003/005는 각각 Drain 0.1/0.3/0.5 V다. 첨부 그림의 mu_ratio 색상 하한은
0.043/0.033/0.025, mu_vsat_e 하한은 약 37/27/20으로 달랐다.
이는 표시 범위이며 동일 위치의 실제값이나 검증된 전역 최솟값으로 단정하지 않는다.
정량 비교에는 같은 색 범위·동일 좌표 sampling이 필요하지만 이번에는 경향 확인으로 종료했다.
삼각형별 차이는 element 데이터 및 mesh/방향 의존성도 반영하므로 전부 물리적 급변으로 해석하지 않는다.

Node 값과 element 값은 데이터 위치가 다르다. ParaView의 Cell Data to Point Data 등으로
평활화하면 보기에는 부드러워져도 원래 element 값과 같지는 않으므로 변환 여부를 기록한다.
`partial`은 모든 블록에 해당 배열이 있지 않다는 표시이며, 빈 oxide 영역을 이동도 0으로 판정하지 않는다.

#### 1.5.9. 산출물·재현성과 최종 판정

VTM은 함께 생성된 VTU를 참조하므로 동일 상대 경로를 유지한다. 번호가 붙은 VTU는 영역 블록일 수 있으며
bias 번호와 혼동하지 않는다. ParaView에서는 한 상태만 표시하고 같은 물리량·색 범위를 비교한다.
PNG는 저장된 파일을 열어 확인하며 비대화형 plotting에서는 창이 자동으로 뜨지 않을 수 있다.

최종 리뷰 코드는 전류 수집·CSV·VTM 저장과 PNG 생성을 같은 실행 흐름에 포함했다.
이전 run 폴더의 파일을 열면 `kla_drain_000` 또는 CSV가 없을 수 있으므로 실제 실행 경로와
새 output 디렉터리를 먼저 확인한다. 기존 결과를 덮어쓰지 않는 생성 정책에서는 재실행마다 새 작업 폴더가 필요하다.
스크린샷은 정성 근거, CSV는 수치 근거, 코드·로그는 조건 근거로 구분한다.
대화에 첨부된 이미지 원본을 저장소의 figures에 모두 수집한 것은 아니므로 존재하지 않는 그림 링크는 만들지 않았다.

### 1.6. 분석 종료 범위와 다음 Phase

Git 준비부터 코드 구성·자동 테스트·커밋·완료 기준까지는 [Phase 1 통합 가이드와 실험 기록](PHASE1_SIO2_CAPACITOR.md)을 따른다.

이번 완료 범위는 오픈소스의 구성·해석 흐름 이해, 실행·수렴 확인, I-V 및 공간 분포의 경향 분석이다.
정량 보정된 제조 소자 모델, 전류 폭 정규화, Vth/SS/Ion/Ioff/DIBL 추출, mesh·bias 간격 독립성,
최적 설계 조건은 아직 확보하지 않았다. 'mobility 보정'은 모델 적용이며 측정 데이터에 대한 calibration을 뜻하지 않는다.

다음은 기준 README의 **Phase 1**이다. 기존 cap2·PN 실험을 자동 오차 검사로 전환하고 MOSCAP 검증을
추가하며, 단위·방정식·모델·경계조건을 문서화한다. 통과 후 **Phase 2**의 long-channel NMOS 및 추출
라이브러리로 진행한다. Gate length·산화막·도핑 대조실험과 제한 조건을 둔 최적화는 그 뒤에 수행한다.

후속 실험은 각 bias/설계점의 입력·모델 버전·수렴 상태·단자 전류·폭 정규화를 기록한다.
실패점은 0 A가 아닌 NaN/실패 상태로 보존하고 제외 이유를 보고한다.
tmp 출력은 기본 Git 제외이므로 재현 명령, 코드 버전, 설정 및 필요한 기준 데이터·해시를 별도 보관한다.
본 문서 갱신에서 새 simulation 또는 전체 assertion 재실행은 수행하지 않았다.

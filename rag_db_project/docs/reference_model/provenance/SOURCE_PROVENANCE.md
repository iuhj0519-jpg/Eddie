# Reference Source Provenance

- 문서 ID: REF-PROV-001
- 상태: recorded
- 수집일: 2026-08-27

## 원본

```text
C:\intelFPGA\RTL_Design\CNN-Handwritten-Digit-MNIST-main\
CNN-Handwritten-Digit-MNIST-main\Network\Vivado\src\fpga
```

테스트 데이터 원본:

```text
C:\intelFPGA\RTL_Design\CNN-Handwritten-Digit-MNIST-main\
CNN-Handwritten-Digit-MNIST-main\Network\Vivado\CNN-MNIST-Arty-Z7\
CNN-MNIST-Arty-Z7.sim\sim_1\behav\xsim
```

## 포함 정책

- `rtl/*.v`: 포함
- `tb/top_sim.v`: 포함
- `rtl/w_*.mif`: 포함
- `rtl/b_*.mif`: 포함
- `rtl/sigContent.mif`: 포함
- `test_data_0000.txt`~`test_data_0099.txt`: 포함

## 제외 정책

- `top_sim.v.bak`: backup이므로 제외
- `component.xml`: Vivado IP packaging metadata로 ModelSim reference 재현에 불필요
- `xgui/zyNet_v1_0.tcl`: Vivado GUI packaging script로 reference inference에 불필요
- test vector 0100 이후: 현재 100-sample baseline 범위 밖
- 원본 Vivado/XSim 생성 디렉터리: 파생 artifact이므로 제외

복사본은 원본을 수정하지 않는다. 향후 ingestion에서 각 파일의 SHA-256을 산출하고 Git commit과 함께 `source_manifest.yaml`에 기록한다.

# 마지막 Power 분석: 실제 Simulation 활동을 Post-Route에 반영

## 현재 결과와 종료 기준

2026-09-08 ppa_final/power.rpt도 Total 0.332 W, Confidence Low,
Simulation Activity File `---`, Design Nets Matched `NA`이다. report_power 재실행만으로 SAIF가 생기지는 않는다.
아래 절차는 안내이며 아직 SAIF 활동 수집이나 활동 기반 Power 분석을 실행한 것은 아니다.

1. 동일 입력 100개·동일 클록 조건에서 각 모델의 SAIF와 Golden 결과를 수집한다.
2. 해당 모델/버전 Post-Route DCP에 SAIF를 매핑하고 미매칭 보고서를 검토한다.
3. 원래 vectorless 보고서와 새 보고서를 함께 보관하고 조건·coverage·한계를 기록한다.
4. Confidence High를 강제로 만들기 위해 Toggle Rate를 임의로 조정하지 않는다.
   SAIF를 넣어도 매핑률 또는 I/O/환경 조건이 부족하면 Low가 남을 수 있다.
5. 이는 활동 기반 추정 전력이며 보드 실측 전력이 아니다. 현재 100 MHz Timing 실패도 별도로 남긴다.

## A. Vivado Simulator(XSim)에서 SAIF 생성

아래 외부 실행 명령은 **PowerShell** 전용이다. Vivado Tcl Console 또는 cmd에 `&` 명령을 붙여 넣지 않는다.
별도 실험 복사본을 권장하며 `project/workspace/<target>`와 `project/inputs/reference_model/testdata` 구조를
유지한다. RTL/TB가 사용하는 `memory/` 및 `../../inputs/...` 상대경로를 변경하지 않는다.
간단히 기존 target 폴더에서 실행하면 RTL은 바뀌지 않지만 xsim 실행 산출물이 생긴다.

```powershell
Set-Location 'C:\Users\iuhj0\Eddie\rag_db_project\workspace\optimized_accelerator'
$rtlSources = @(Get-ChildItem -LiteralPath rtl -Filter '*.sv' | Sort-Object Name | ForEach-Object FullName)
& 'C:\Xilinx\Vivado\2022.1\bin\xvlog.bat' -sv -i rtl $rtlSources tb/top_sim.sv
# 직전 명령 성공을 확인한 뒤에만 다음 단계 실행
& 'C:\Xilinx\Vivado\2022.1\bin\xelab.bat' -debug typical -s power_snapshot work.top_sim
& 'C:\Xilinx\Vivado\2022.1\bin\xsim.bat' power_snapshot -gui
```

XSim의 Simulation Tcl Console에서(합성 DCP Console이 아님):

```tcl
restart
set power_dir {C:/intelFPGA/18.1/dnn_optimization_project/vivado_ppa_compare/workspace_optimized/power_activity}
file mkdir $power_dir
set observed [get_objects -r /top_sim/device_under_test/*]
if {[llength $observed] == 0} {error "DUT scope was not found"}
open_saif "$power_dir/mnist_100.saif"
log_saif $observed
run all
close_saif
```

`device_under_test`는 현재 TB의 실제 DUT instance 이름이다. FINAL_RESULT 99/1과
REFERENCE_GOLDEN_MATCH PASS를 확인한다. Timeout/Fatal/입력파일 누락이면 해당 활동 파일을 유효 증거로 쓰지 않는다.
SAIF를 닫은 다음 시뮬레이터를 종료한다. 캡처 구간은 reset부터 정상 완료까지의 전체 실행구간으로 두 모델을 통일하고
SAIF DURATION 및 Transcript를 보관한다. steady-state 구간을 따로 측정한다면 batch 범위를 명시해 별도 파일로 남긴다.
Systolic Prototype은 Set-Location과 출력 경로를 workspace_systolic로 바꾸어 별도로 반복한다.

## B. 기존 Vivado Post-Route DCP에 적용

해당 모델의 post_route.dcp를 연 Vivado GUI의 **Tcl Console**에서 실행한다.

```tcl
set power_dir {C:/intelFPGA/18.1/dnn_optimization_project/vivado_ppa_compare/workspace_optimized/power_activity}
read_saif -strip_path top_sim/device_under_test -out_file "$power_dir/saif_mapping.rpt" "$power_dir/mnist_100.saif"
report_power -file "$power_dir/power_saif.rpt"
report_switching_activity -file "$power_dir/switching_activity.rpt"
```

`-strip_path`에는 맨 앞 `/`를 넣지 않는다. 매핑 실패 시 SAIF 내부 INSTANCE와 DCP 계층을 확인한다.
LUT 최적화로 RTL 내부 Net 이름이 바뀔 수 있으므로 RTL SAIF가 모든 Gate Net에 직접 매핑되는 것은 아니다.
매핑이 부족하면 Post-Synthesis Functional Simulation의 SAIF를 추가 검토한다. 현재 Timing이 실패하므로
Post-Route Timing Simulation 결과를 정상 100 MHz 동작의 근거로 사용할 수는 없다.

## 캡처 및 보관

| 증거 | 확인 항목 |
|---|---|
| Simulation Transcript | 100개 입력, Golden 일치, 캡처 구간 |
| SAIF | DURATION/TIMESCALE, DUT scope, 파일 SHA-256 |
| saif_mapping.rpt | 매칭/미매칭 정보; 핵심 Memory/DSP/제어가 빠지지 않았는지 |
| Power Summary / Confidence Level | Activity File, Design Nets Matched, Low 원인 및 confidence |
| Power Settings | 주파수·온도·전압·공정·I/O 조건을 두 모델에서 통일 |
| On-Chip Components / Hierarchical | Total/Dynamic/Static, Logic/Signals/BRAM/DSP별 전력 |

보관 위치: artifacts/power/<target>/run_001/ (실제로 생성한 파일만 저장).
비교표는 Total/Dynamic/Static과 SAIF coverage/조건을 함께 제시한다.
에너지/이미지는 유효한 같은 구간에 대해 `평균 Power × 해당 구간 시간 / 완료 이미지 수`로 계산하되,
현재 결과에는 Timing 미충족이라는 한계를 반드시 표시한다.

명령은 설치된 Vivado 2022.1의 doc/eng/man/open_saif, log_saif, read_saif, get_objects,
report_switching_activity 설명을 확인했다. 외부 Web/LLM 또는 Historical Baseline을 사용하지 않았다.

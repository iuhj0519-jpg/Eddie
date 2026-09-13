# Vivado 프로젝트/Simulation 진단 — 2026-09-13

실제 RTL은 변경하지 않았다. 첨부 화면과 로컬 XPR/Tcl/소스를 대조한 결과다.

## 확인된 원인

1. `vivado_ppa_compare/rag_workspace_systolic/rag_workspace_systolic.xpr`는 `$PPRDIR/../../Weight_SRAM.sv`,
   `NPU_Top.sv`, `zyNet.sv`, `top_sim.sv`를 참조한다. 이는 Git의 `workspace/optimized_accelerator`가 아니라
   `C:/intelFPGA/18.1/dnn_optimization_project` 루트 소스다. Unified Buffer가 있다는 것만으로 같은 버전이 아니다.
2. XPR의 Design/Simulation Top이 모두 `top_sim`이다. RTL Analysis/Synthesis의 Top은 `zyNet`,
   Simulation Top은 `top_sim`으로 분리해야 한다.
3. 첫 오류 `[Synth 8-27] string type not supported`는 루트 `Weight_SRAM.sv:39`의
   `string mif_file_name;`이다. 뒤의 initial block은 `$sformatf`로 이름을 만들어 `$readmemb`한다.
   이 코드가 Vivado RTL elaboration의 합성 처리 경로에서 거부되었고, 상위 모듈 오류는 연쇄 실패다.
   Simulation elaboration과 Open Elaborated Design은 같은 과정이 아니다. Top만 바꿔도 이 Weight 코드 문제는 남을 수 있다.
4. 실제 `rag_workspace_systolic.sim/sim_1/behav/xsim/top_sim.tcl:11`은 `run 1000ns`이다.
   GUI의 1 us 시점은 초기 실행 길이이며 완료/Timeout 증거가 아니다.

## 올바른 프로젝트로 확인

- 먼저 Sources 각 파일의 Properties/Location이 `C:/Users/iuhj0/Eddie/rag_db_project/workspace/optimized_accelerator/rtl/`인지 확인한다.
- Design Sources에는 해당 RTL만, Simulation Sources에는 `tb/top_sim.sv`를 등록한다. 서로 다른 디렉터리의 동명 모듈을 혼합하지 않는다.
- Design Top=zyNet, Simulation Top=top_sim. Sources에서 해당 모듈을 우클릭해 Set as Top을 각각 설정한다.
- include directory는 해당 rtl 폴더다. TB의 `memory/`와 `../../inputs/reference_model/testdata` 상대경로가
  실행 디렉터리에서 실제로 존재하는지 확인한다. 파일을 프로젝트에 추가했다는 것만으로 상대경로가 일치하지는 않는다.
- 필요하면 기존 [Power 절차](../../experiments/automation_loop/final_review_20260908/POWER_SAIF_GUIDE.md)의
  target 폴더에서 xvlog/xelab/xsim을 실행하는 방법을 사용한다. 경로 보존을 위해 복사본도 project/workspace/target 구조를 유지한다.

Vivado 프로젝트 Tcl Console에서 읽기 전용으로 확인:

```tcl
get_property TOP [get_filesets sources_1]
get_property TOP [get_filesets sim_1]
get_files -of_objects [get_filesets sources_1]
get_files -of_objects [get_filesets sim_1]
```

## display 출력 확인

Behavioral Simulation으로 돌아가 XSim Tcl Console에서 `run all`을 실행하거나 Run All 버튼을 누른다.
정상 진행이면 `$display`는 Tcl Console의 Simulation 출력에 나타난다. Messages 탭은 주로 도구 진단용이다.
Git optimized TB는 192/195행에 샘플 PASS/FAIL, 204행에 `FINAL_RESULT ... ACCURACY=...`,
210행에 `REFERENCE_GOLDEN_MATCH PASS`, 213행에 `$finish`가 있다. 전체 샘플이 끝나기 전에는 최종 Accuracy가 없다.
루트 TB의 출력 문구는 다르므로 그것을 Git optimized 결과라고 기록하면 안 된다.

로그 후보는 `<project>.sim/sim_1/behav/xsim/simulate.log`이며 버전/실행 방식에 따라 xsim.log도 확인한다.
현재 해당 GUI 프로젝트의 simulate.log는 0 byte이므로 Accuracy/완료를 확인할 로그가 아직 없다.
GUI Console 전체 출력도 저장해 함께 제공한다. `run all` 후 멈춤/오류가 있으면 최초 ERROR/FATAL과 메모리 파일 경고부터 확인한다.
시뮬레이션 시간이 계속 증가하고 완료하지 않는 경우에만 핸드셰이크/종료 조건 등을 추가 진단한다.

필요 자료: 올바른 파일 경로와 Top 화면, compile.log, elaborate.log, simulate.log 또는 전체 Console,
FINAL_RESULT/Golden/finish 부분. 현재 자료로 Accuracy가 얼마인지 또는 Git optimized DUT가 실패했는지는 단정하지 않는다.

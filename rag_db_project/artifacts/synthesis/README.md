# Synthesis Artifacts

Vivado가 생성한 합성 결과를 대상별·Run별로 보존한다.

```text
synthesis/
├─ systolic_prototype/run_###/
└─ optimized_accelerator/run_###/
```

각 Run은 `utilization.rpt`, `utilization_hierarchical.rpt`, `ram_utilization.rpt`, `timing_summary.rpt`, `power.rpt`, `run_summary.txt`, `run_manifest.yaml`을 포함할 수 있다.

`post_synthesis.dcp`는 GUI에서 합성 설계를 다시 열기 위한 Binary Checkpoint이다. 크기가 크고 재생성 가능하므로 일반 Git에는 기본적으로 포함하지 않는다. 보존할 필요가 있으면 Git LFS를 사용한다.

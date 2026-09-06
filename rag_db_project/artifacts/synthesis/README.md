# Synthesis Artifacts

Vivado `synth_design` 이후의 논리 Netlist 기준 결과를 저장한다.

```text
synthesis/<target>/run_###/
├── utilization.rpt
├── utilization_hierarchical.rpt
├── ram_utilization.rpt
├── timing_summary.rpt
├── power.rpt
├── run_summary.txt
└── run_manifest.yaml
```

이 단계의 Timing과 Power는 Placement·Routing 지연이 반영되지 않았거나 추정 정확도가 낮을 수 있다. 배치·배선 이후 결과는 `artifacts/implementation/`에 별도로 저장한다.

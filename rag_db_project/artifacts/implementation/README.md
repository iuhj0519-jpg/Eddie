# Implementation And Post-Route Artifacts

Vivado `opt_design → place_design → phys_opt_design → route_design` 이후의 물리 구현 결과를 저장한다.

```text
implementation/<target>/run_###/
├── utilization_post_route.rpt
├── utilization_hierarchical_post_route.rpt
├── timing_summary_post_route.rpt
├── power_post_route.rpt
├── route_status.rpt
├── drc.rpt
└── run_manifest.yaml
```

Post-Route Timing은 실제 배치와 Routing 지연을 반영하므로 Synthesis Timing보다 Sign-off에 가깝다. `route_status.rpt`의 Unrouted Net이 0이고 `drc.rpt`의 위반이 없으며 Setup/Hold/Pulse Width 조건을 모두 만족해야 Timing Closure로 판정한다.

Power는 Post-Route Netlist를 사용해도 SAIF/VCD Switching Activity가 없고 Confidence가 `Low`이면 비교용 추정치로만 사용한다. 큰 DCP는 Git에 직접 넣지 않고 보관 위치와 SHA-256을 Run Manifest에 기록한다.


# SPEC change proposal — pending human approval

This is an additive overlay; baseline SPEC is not replaced or weakened.

Proposal digest: `3ca659b63730219bc990290a443064754ace482b2cc595e668c80fae68804e45`

## REQ-LOOP-USER-REQUEST-001-1

- Type: developer_request
- Findings: USER-REQUEST_001-1
- Before/evidence: {"raw_request": "1. 현재 SPEC 보완안에는 Weight SRAM 밖에 없습니다. diagnosis에서는 많은 문제가 탐지되었음에도 보완할 내용에는 SRAM 문제만 있는 이유를 설명해주세요."}
- Required change: 1. 현재 SPEC 보완안에는 Weight SRAM 밖에 없습니다. diagnosis에서는 많은 문제가 탐지되었음에도 보완할 내용에는 SRAM 문제만 있는 이유를 설명해주세요.
- Acceptance: []
- Verification: Define measurable acceptance before approval.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-USER-REQUEST-001-2

- Type: developer_request
- Findings: USER-REQUEST_001-2
- Before/evidence: {"raw_request": "2. Simulation 결과를 얻기 위해 workspace/optimized_accelerator(Unified Buffer 존재)에 대한 새로운 프로젝트 파일을 만들고 Vivado를 실행했지만, 1000ns에서 끊겼으며 Accuracy에 대한 display 출력이 TCL Console 창에 출력되지 않았습니다. 그리고 Schematic을 확인해보기 위해 elaboration을 실행했지만 실패했습니다. 어디에서 display를 확인하는 지와 왜 elaboration이 실패했는지 알려주세요."}
- Required change: 2. Simulation 결과를 얻기 위해 workspace/optimized_accelerator(Unified Buffer 존재)에 대한 새로운 프로젝트 파일을 만들고 Vivado를 실행했지만, 1000ns에서 끊겼으며 Accuracy에 대한 display 출력이 TCL Console 창에 출력되지 않았습니다. 그리고 Schematic을 확인해보기 위해 elaboration을 실행했지만 실패했습니다. 어디에서 display를 확인하는 지와 왜 elaboration이 실패했는지 알려주세요.
- Acceptance: []
- Verification: Define measurable acceptance before approval.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

## REQ-LOOP-USER-REQUEST-001-3

- Type: developer_request
- Findings: USER-REQUEST_001-3
- Before/evidence: {"raw_request": "3. 위에서 언급한 자동화 Loop의 요구 단계를 사진으로 다시 첨부했습니다. 이를 모두 구현해야 합니다. Git에 이들을 구성해주세요. 아마 Simulation Log도 필요할 텐데 Vivado 시뮬레이션이 끝나는 대로 첨부하겠습니다."}
- Required change: 3. 위에서 언급한 자동화 Loop의 요구 단계를 사진으로 다시 첨부했습니다. 이를 모두 구현해야 합니다. Git에 이들을 구성해주세요. 아마 Simulation Log도 필요할 텐데 Vivado 시뮬레이션이 끝나는 대로 첨부하겠습니다.
- Acceptance: []
- Verification: Define measurable acceptance before approval.
- Benefit: Remove the cited violation or demonstrate a justified PPA improvement.
- Risk: Do not suppress a warning or relax a requirement merely to obtain PASS.

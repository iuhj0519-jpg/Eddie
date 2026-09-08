# 승인 기반 RTL Automation Loop

## 최신 승인 대상 (2026-09-08)

현재 검토 대상은 `review_20260908`이다. 아래의 2026-09-07 명령 예제는 이전 기록이며,
실제 승인/resume 시 `--run-id review_20260908`을 사용한다. 기존 run_001/run_002와 이전 review는 보존한다.
최종 테이블과 Power 절차: [최종 정리](../../experiments/automation_loop/final_review_20260908/diagnosis.md).

`PPA-MEMORY-MAPPING-001`은 SRAM이라는 모듈 이름과 실제 FPGA Block RAM 매핑을 구분한다.
설정에서 block_ram이 요청된 Weight 계층의 RAMB18/RAMB36이 0이면 LUT hotspot 비율과 무관하게 검출한다.
기존 SRAM 5-bank 요구(REQ-SYS-009)와 물리 BRAM 필수 매핑 보완안(REQ-OPT-MEM-026)은 구분하며,
후자는 아직 승인 대기다. BRAM 하나의 존재만으로 전체 저장 구조/5-lane 공급이 검증되는 것은 아니다.

## 탐지 범위

기존 PPA-DSP/WEIGHT/TIMING/POWER 4개 Finding은 탐지 범위의 제한 목록이 아니다.
모든 허용된 실행 증거를 검토하고 기능·Protocol·성능·자원·메모리·Timing·Power·DRC·Reset 및
이전 실행 대비 회귀까지 개선 후보를 기록한다. 규칙만으로 모든 설계 결함을 발견한다고 보장하지 않는다.
보고서/계측이 없는 항목은 UNKNOWN으로 coverage.json에 기록한다. 원본의 미분류 경고도 Agent와 사람이 검토한다.

현재 Post-Route 근거에 따른 우선 검토 대상은 **Weight 메모리 접근 구조, 주소 계산, 큰 선택 회로,
파이프라인 및 Fanout**이다. 대상은 Weight 블록으로 제한하지 않고 실패 경로와 자원 집중 블록 전체에 적용한다.

| 분석 대상 | 입력 증거 | Finding / 확인 사항 |
|---|---|---|
| Weight/다른 메모리 접근 | 계층별 자원, RAM, critical paths | BRAM 추론, LUT 집중, 접근 지연 |
| 주소 계산 | 실패 경로의 주소/제어 Net | PPA-ADDRESS-001; 폭·연산·주소 파이프라인 가설 |
| 큰 선택 회로 | 실패 경로 MUXF 및 논리 단계 | PPA-MUX-001; 선택 회로 재구성 검토 |
| 파이프라인 | Logic Levels, DSP/BRAM DRC | PPA-PIPELINE-001; Valid/주소/Scheduler 정렬 필수 |
| Fanout/배선 | high_fanout_nets, critical_paths | PPA-FANOUT-001, PPA-ROUTE-DELAY-001 |
| Setup/Hold/Pulse | min_max timing summary | 각각 독립 판정; Hold 없는 보고서는 Hold 통과 증거가 아님 |
| DSP/PE | 계층별 DSP, cycle-level PE 계측 | DSP 개수는 PE Utilization이 아님 |
| DRC | 모든 요약 Rule | DRC-<Rule>; Reset/IO/출력레지스터 경고 포함 |
| 증거 부족 | coverage.json | EVIDENCE-COVERAGE-001; 누락을 PASS로 처리하지 않음 |

## 알고리즘 및 파일 역할

`SPEC Requirement ID → 실패 증거 → 승인된 수정 내용 → 재검증 결과`

1. analyze: artifacts를 파싱하고 원본 해시, Workspace RTL/TB/Memory/Scripts 해시, 설정 해시를 고정한다.
2. diagnosis.md, findings.yaml, coverage.json, spec_change_proposal.md를 사람이 검토한다.
3. approve: Finding마다 승인/거절 및 승인 SPEC Requirement ID를 연결한다. 승인 전 RTL/SPEC을 변경하지 않는다.
4. resume: 승인과 증거 바인딩을 확인한다. Agent는 허용된 로컬 RAG 근거만 사용해 proposed_patch.diff와
   patch_trace.yaml을 작성한다. 외부 LLM/API·Web·Historical Baseline은 사용하지 않는다.
5. 격리 복사본에 기존 RTL 파일만 패치한다. TB, Golden, Memory, SPEC 변경은 이 실행 경로에서 금지한다.
6. ModelSim Compile → Simulation → Vivado Synthesis를 실제 실행한다. 실패/Timeout이면 후속 도구는 건너뛴다.
7. 성공/실패 모두 원본 로그를 수집하고 다음 run_###을 자동 생성·분석한다. 다음 Run은 새 승인 대기 상태다.
8. 동일 Finding 반복/횟수 상한에서는 재계획을 요청한다. 패치를 원래 Workspace로 자동 승격하거나 Push하지 않는다.

Python은 도구 실행·파싱·승인 Gate를 담당한다. 수정안 생성은 현재 작업 Agent의 단계이며 Python만으로
임의의 RTL 수정안을 생성하는 외부 서비스는 없다. Agent는 pending_human_approval에서 반드시 멈춘다.

| 파일 | 역할 |
|---|---|
| __init__.py | Python 패키지 표시; 합성 영향 없음 |
| parsers.py / detectors.py | 요약 및 경로·Fanout·DRC 정규화와 탐지 |
| run_loop.py | 분석/승인/격리 적용/실행/후속 Run 생성 |
| tool_flow.py / synthesis.tcl | 로컬 ModelSim/Vivado 어댑터; 100 MHz, xc7z020clg400-1 |
| test_automation.py | 임시 Fixture를 쓰는 안전성·회귀 테스트; DUT 검증과 구분 |
| smoke_tools.py | 미수정 Workspace 복사본으로 실제 도구 어댑터 검증 |

## 실행 예

프로젝트 루트에서 `python rag/automation/run_loop.py analyze --target optimized_accelerator --artifact-root artifacts/implementation/optimized_accelerator/run_001 --run-id review_20260907`

review_YYYYMMDD는 승인 전 근거 분석용이며 run_003 등 Debugging 실행 번호를 소비하지 않는다.
과거 run_001/run_002는 불변 이력으로 유지한다. 바인딩이 없는 과거 Run 승인은 차단되며 새 review를 승인해야 한다.

사용자 명시 승인 뒤에만:

`python rag/automation/run_loop.py approve --target optimized_accelerator --run-id review_20260907 --finding-id <ID> --decision approved --requirement-id <승인된-SPEC-ID>`

모든 항목 검토 후 `python rag/automation/run_loop.py resume --target optimized_accelerator --run-id review_20260907`.
패치가 없으면 patch_request.json 생성 후 Agent를 기다린다. Agent가 패치·추적 문서를 작성한 뒤 resume로 실행한다.

```yaml
changes:
  - finding_id: PPA-ADDRESS-001
    requirement_id: <승인된-SPEC-ID>
    files: [rtl/weight_sram.sv]
    explanation: <근거와 변경 내용; 실제 승인 범위만 포함>
```

## 원본과 후속 Run

- artifacts/verification/<target>/<child_run>: compile.log, simulation.log, protocol_assertions.log, verification_result.json
- artifacts/synthesis/<target>/<child_run>: synthesis.log, utilization/timing/power/ram/critical_paths/high_fanout/drc 보고서
- artifacts/automation_loop/<target>/<child_run>: 위 원본의 분석용 복사본, execution_result.json
- experiments/automation_loop/<target>/<run>: diagnosis/findings/coverage/approval/gate/progress/patch_trace/revalidation_result
- .automation_debug/<target>/<parent_run>: 패치된 격리 복사본과 별도 로컬 Git; 원본 및 main/Project_Git 불변

기존 TB가 출력하지 않는 PE 활동/Protocol coverage를 성공값으로 만들어 넣지 않는다. 전체 샘플 예측은
가능할 때 이전 실행과 비교하며 근거가 없으면 UNKNOWN이다. 합성 어댑터 성공도 Post-Route/실측 Power
및 전체 Protocol 회귀 통과와 다르다. 최종 승격은 이를 별도로 검증하고 사람이 수락해야 한다.

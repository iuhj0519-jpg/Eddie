# 로컬 개발 환경 및 검증

TradingAgents 0.5.1 기반 Windows 환경이다. 유료 API 키 없이 Ollama의 `qwen3:4b`를 사용한다.

## 설치 구성

| 구성 요소 | 버전 / 설정 |
|---|---|
| Python | 전용 3.12.14, 프로젝트 `.venv` |
| uv | 0.12.19 |
| Ollama | 0.34.4, CPU 실행 |
| 모델 | qwen3:4b, Q4_K_M |
| 문맥 / 동시 요청 | 8192 / 1 |
| PC | Core Ultra 7 155H, RAM 약 31.6 GiB |

작업 폴더는 `C:/Users/iuhj0/OneDrive/바탕 화면/TradingAgents_Local/repository`, 전용 런타임은 `%LOCALAPPDATA%/TradingAgentsRuntime`이다. 기존 Python과 다른 프로젝트 환경은 변경하지 않는다. 모델·가상환경·서버 로그는 Git에 포함하지 않는다.

Ollama는 [공식 Windows 배포본](https://github.com/ollama/ollama/releases/tag/v0.34.4)의 CPU/Vulkan 파일 및 라이선스를 사용한다. 이 PC에는 NVIDIA CUDA 라이브러리를 설치하지 않았다. Intel GPU/NPU 가속은 검증 범위에 포함하지 않는다.

## 새 환경 설치

```powershell
git clone --single-branch --branch tradingagents-local https://github.com/iuhj0519-jpg/Eddie.git TradingAgents_Local
cd TradingAgents_Local
$runtime = "$env:LOCALAPPDATA/TradingAgentsRuntime"
$env:UV_PYTHON_INSTALL_DIR = "$runtime/python"
& "$runtime/uv/uv.exe" python install 3.12.14
& "$runtime/uv/uv.exe" venv --python 3.12.14 .venv
& "$runtime/uv/uv.exe" pip install --python .venv/Scripts/python.exe -r docs/requirements-local-windows.txt
& "$runtime/uv/uv.exe" pip install --python .venv/Scripts/python.exe --no-deps -e .
```

위 명령은 `runtime/uv/uv.exe`와 `runtime/ollama/ollama.exe`가 준비된 상태를 전제로 한다. 새 PC에서는 [uv 공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/) 및 [Ollama Windows 안내](https://docs.ollama.com/windows)에 따라 해당 경로에 실행 파일과 동봉 라이브러리를 먼저 준비한다. 현재 PC에는 이미 설치되어 있다.

## 서버 시작과 모델 설치

프로젝트 루트에서 실행한다. 포트 11434가 사용 중이면 시작기는 기존 서버를 바꾸지 않고 오류를 반환한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start_local_ollama.ps1
```

시작기는 `OLLAMA_NO_CLOUD=1`, `OLLAMA_HOST=127.0.0.1:11434`, 문맥 8192, 동시 추론 1개, 로딩 모델 1개를 적용하고 서버 로그의 클라우드 비활성화를 확인한다. 실행 정책 우회는 이 PowerShell 프로세스에만 적용된다. 자동 시작이나 전역 환경변수는 설정하지 않는다.

모델을 처음 설치할 때만 다음 명령을 실행한다. 모델 파일 다운로드에는 인터넷이 필요하다.

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/pull' -Method Post -ContentType 'application/json' -Body '{"model":"qwen3:4b","stream":false}' -TimeoutSec 3600
```

## JSON 및 도구 호출 검사

```powershell
$state = Get-Content "$env:LOCALAPPDATA/TradingAgentsRuntime/server-state.json" -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe scripts/local_llm_smoke.py --server-log $state.stderr_log
```

검사 항목:

1. 서버의 클라우드 비활성화 및 로컬 모델 설치 확인.
2. 외부 LLM 주소와 허용되지 않은 요청 경로를 전송 전에 거부.
3. Ollama JSON 출력에서 매출 1200, 영업이익 180, USD, 미보고 부채 `null` 보존.
4. 실제 TradingAgents 클라이언트의 JSON schema 응답 확인.
5. 모델이 현금흐름 계산 도구와 인자를 생성하고, Python이 `123.50 - 42.75 = 80.75`를 계산한 뒤 모델이 반환값을 읽는 과정 확인.

검증기는 프록시·리다이렉트·호스팅 추적·SDK 자동 재시도를 끄고 HTTP 요청을 loopback의 지정 경로로 제한한다. SDK가 요구하는 `LOCAL_ONLY` 값은 실제 API 키가 아니다. OpenAI SDK는 로컬 호환 API의 통신에만 사용된다.

Ollama 호환 요청에는 `reasoning_effort=none`, `max_tokens=1024`를 명시한다. 네이티브 JSON 요청은 `think=false`, `num_predict=256`이다. [Ollama 호환 API 명세](https://docs.ollama.com/api/openai-compatibility)를 따른다.

결과·응답시간·요청 주소는 `reports/local-smoke.json`에 저장된다. 게시된 검증 결과는 [validation/local-llm-smoke.json](validation/local-llm-smoke.json)에 있다. 이 검사는 작은 고정 자료의 연결 확인이며 금융 추론 정확도, 장문 처리 또는 반복 안정성 평가가 아니다.

## 운영 범위

전체 분석 그래프의 로컬 전용 실행기는 별도 구현 범위다. 원본 `main.py`와 CLI에는 클라우드 공급자 설정이 있으므로 이 환경의 실행 진입점은 위 검증 스크립트로 한정한다. 유료 API 키를 추가할 필요가 없다.

모델은 마지막 요청 후 5분간 유지된다. 즉시 메모리를 반환하려면 다음을 실행한다.

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/generate' -Method Post -ContentType 'application/json' -Body '{"model":"qwen3:4b","keep_alive":0}'
```

후속 구현 범위는 [구현 계획](LOCAL_IMPLEMENTATION_KO.md)을 참고한다.

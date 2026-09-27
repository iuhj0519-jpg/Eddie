"""Exercise a local 4B model without creating a trading graph or using market APIs.

Run with the project venv. Only loopback HTTP to Ollama is permitted by this
script's HTTP transport; it does not change the upstream app's defaults.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

MODEL = "qwen3:4b"
BASE = "http://127.0.0.1:11434"
ALLOWED_PATHS = {"/api/version", "/api/tags", "/api/show", "/api/chat", "/v1/chat/completions"}


def main():
    # Do not inherit optional hosted tracing from a development shell.
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-log", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/local-smoke.json"))
    args = parser.parse_args()
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "requests": [],
        "checks": [],
        "passed": False,
    }

    def guard(request):
        url = request.url
        if (
            url.scheme != "http"
            or url.host != "127.0.0.1"
            or url.port != 11434
            or url.path not in ALLOWED_PATHS
        ):
            raise ValueError("Blocked non-local or unexpected request")
        report["requests"].append({"method": request.method, "url": str(url)})

    def check(name, fn):
        started = time.perf_counter()
        value = fn()
        report["checks"].append(
            {
                "name": name,
                "passed": True,
                "seconds": round(time.perf_counter() - started, 3),
                "result": value,
            }
        )
        print(f"PASS {name}", flush=True)
        return value

    try:
        log = args.server_log.read_text(encoding="utf-8", errors="replace")
        if "Ollama cloud disabled: true" not in log:
            raise RuntimeError("Server log does not confirm disabled cloud features")
        report["cloud_disabled_log_verified"] = True
        # No inherited proxy, no redirects, no SDK retries, no cloud credentials.
        with httpx.Client(
            timeout=300, trust_env=False, follow_redirects=False, event_hooks={"request": [guard]}
        ) as http:

            def api(path, body=None):
                response = (
                    http.get(BASE + path) if body is None else http.post(BASE + path, json=body)
                )
                response.raise_for_status()
                return response.json()

            report["ollama"] = api("/api/version")
            models = api("/api/tags")["models"]
            matches = [m for m in models if m["name"] == MODEL]
            if len(matches) != 1:
                raise RuntimeError("Expected the installed qwen3:4b model")
            report["model_metadata"] = matches[0]
            info = api("/api/show", {"model": MODEL})
            if info.get("remote_host") or info.get("remote_model"):
                raise RuntimeError("Remote model rejected")
            report["capabilities"] = info.get("capabilities")

            # Verify the request guard without sending anything to the network.
            def blocked_endpoints():
                rejected = []
                for url in [
                    "https://api.openai.com/v1/chat/completions",
                    "https://ollama.com/api/chat",
                    "http://127.0.0.1:11434/api/pull",
                ]:
                    try:
                        guard(httpx.Request("POST", url))
                    except ValueError:
                        rejected.append(url)
                    else:
                        raise AssertionError("Forbidden request was accepted")
                return rejected

            check("reject_external_endpoints", blocked_endpoints)

            schema = {
                "title": "FinancialSnapshot",
                "description": "Extract only supplied financial data; preserve missing values.",
                "type": "object",
                "properties": {
                    "revenue": {"type": "integer"},
                    "operating_income": {"type": "integer"},
                    "currency": {"type": "string"},
                    "debt": {"type": "null"},
                },
                "required": ["revenue", "operating_income", "currency", "debt"],
                "additionalProperties": False,
            }

            def native_json():
                result = api(
                    "/api/chat",
                    {
                        "model": MODEL,
                        "stream": False,
                        "think": False,
                        "format": schema,
                        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 256},
                        "messages": [
                            {
                                "role": "user",
                                "content": "Extract JSON only: revenue 1200 USD, operating income 180 USD. "
                                "Debt is not reported; set debt to null. Preserve the given numbers.",
                            }
                        ],
                    },
                )
                parsed = json.loads(result["message"]["content"])
                assert parsed == {
                    "revenue": 1200,
                    "operating_income": 180,
                    "currency": "USD",
                    "debt": None,
                }, parsed
                return {
                    "parsed": parsed,
                    "prompt_tokens": result.get("prompt_eval_count"),
                    "output_tokens": result.get("eval_count"),
                }

            check("native_json_values_and_missing_data", native_json)

            from langchain_core.messages import HumanMessage, ToolMessage

            from tradingagents.llm_clients.factory import create_llm_client

            # This is the actual TradingAgents client factory, explicitly local.
            llm = create_llm_client(
                "ollama",
                MODEL,
                base_url=BASE + "/v1",
                api_key="LOCAL_ONLY",
                http_client=http,
                max_retries=0,
                timeout=300,
                temperature=0,
                max_tokens=1024,
            ).get_llm()
            # LangChain sends max_completion_tokens; Ollama documents max_tokens.
            # Explicitly disable thinking for schema-constrained Qwen output.
            llm = llm.model_copy(
                update={"extra_body": {"reasoning_effort": "none", "max_tokens": 1024}}
            )

            def adapter_json():
                response = llm.with_structured_output(schema, method="json_schema").invoke(
                    "Extract JSON: revenue=1200, operating_income=180, currency=USD, debt unknown/null. /no_think"
                )
                assert response == {
                    "revenue": 1200,
                    "operating_income": 180,
                    "currency": "USD",
                    "debt": None,
                }, response
                return response

            check("tradingagents_adapter_json_schema", adapter_json)

            tool = {
                "type": "function",
                "function": {
                    "name": "calculate_free_cash_flow",
                    "description": "Calculate free cash flow from operating cash flow minus capital expenditures.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operating_cash_flow": {"type": "number"},
                            "capital_expenditures": {"type": "number"},
                        },
                        "required": ["operating_cash_flow", "capital_expenditures"],
                        "additionalProperties": False,
                    },
                },
            }

            def roundtrip():
                user = HumanMessage(
                    content="Call calculate_free_cash_flow for operating cash flow 123.50 and capital expenditures 42.75. Use the tool, do not compute yourself. /no_think"
                )
                response = llm.bind_tools([tool]).invoke([user])
                assert len(response.tool_calls) == 1, str(response)
                call = response.tool_calls[0]
                assert call["name"] == "calculate_free_cash_flow", call
                values = call["args"]
                assert set(values) == {"operating_cash_flow", "capital_expenditures"}, values
                assert Decimal(str(values["operating_cash_flow"])) == Decimal("123.50"), values
                assert Decimal(str(values["capital_expenditures"])) == Decimal("42.75"), values
                # Execute the one permitted function locally, never arbitrary model code.
                answer = Decimal(str(values["operating_cash_flow"])) - Decimal(
                    str(values["capital_expenditures"])
                )
                result = {"free_cash_flow": str(answer)}
                final = llm.invoke(
                    [
                        user,
                        response,
                        ToolMessage(content=json.dumps(result), tool_call_id=call["id"]),
                    ]
                )
                assert "80.75" in final.content, final.content
                return {
                    "tool_call": call,
                    "executed_result": result,
                    "final": final.content,
                    "call_usage": response.usage_metadata,
                    "final_usage": final.usage_metadata,
                }

            check("tradingagents_tool_execution_and_result", roundtrip)
        report["passed"] = True
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Evidence: {args.output}", flush=True)


if __name__ == "__main__":
    main()

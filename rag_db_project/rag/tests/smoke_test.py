#!/usr/bin/env python3
"""Retrieval and data-leakage smoke tests for the prototype index."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import yaml

RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RAG_DIR.parent
sys.path.insert(0, str(RAG_DIR / "retrieve"))

from search import search  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = yaml.safe_load(
        (RAG_DIR / "config" / "prototype_index.yaml").read_text(encoding="utf-8")
    )
    database_path = RAG_DIR / "data" / config["index_id"] / "rag_index.sqlite3"
    require(database_path.is_file(), f"missing index: {database_path}")
    dense_weight = float(config["hybrid_retrieval"]["dense_weight"])
    sparse_weight = float(config["hybrid_retrieval"]["sparse_weight"])

    cases = [
        {
            "id": "result_register_protocol",
            "query": "REQ-SYS-024 AXI-Lite 0x08 class result storage fifth read clear",
            "expected_path": "inputs/specifications/02_systolic_accelerator/",
            "expected_token": "REQ-SYS-024",
        },
        {
            "id": "reference_interrupt",
            "query": "Reference Model intr out_valid axis_in_data_ready",
            "expected_path": "inputs/",
            "expected_token": "intr",
        },
        {
            "id": "controller_states",
            "query": "Systolic Controller IDLE RUN DONE_STATE i_start o_busy o_done",
            "expected_path": "inputs/systolic_controller/",
            "expected_token": "DONE_STATE",
        },
        {
            "id": "controller_skew",
            "query": "Systolic Controller cnt row column skew latched_mat_a latched_mat_b",
            "expected_path": "inputs/systolic_controller/",
            "expected_token": "latched_mat_a",
        },
        {
            "id": "fixed_point_saturation",
            "query": "Q15.11 Q5.5 saturation comparator three-way MUX overflow",
            "expected_path": "inputs/specifications/02_systolic_accelerator/",
            "expected_token": "Q5.5",
        },
    ]

    report_cases: list[dict[str, object]] = []
    for case in cases:
        results = search(database_path, case["query"], 8, dense_weight, sparse_weight)
        require(results, f"no retrieval result: {case['id']}")
        require(
            any(str(item["source_path"]).startswith(case["expected_path"]) for item in results[:5]),
            f"expected path missing from top 5: {case['id']}",
        )
        require(
            any(case["expected_token"] in str(item["content"]) for item in results[:5]),
            f"expected evidence missing from top 5: {case['id']}",
        )
        require(
            all(
                not str(item["source_path"]).startswith(
                    ("historical_baselines/", "workspace/", "verification/", "experiments/", "artifacts/")
                )
                for item in results
            ),
            f"denied path leaked into results: {case['id']}",
        )
        report_cases.append(
            {
                "id": case["id"],
                "status": "PASS",
                "top_result": results[0]["source_path"],
                "top_chunk_id": results[0]["chunk_id"],
            }
        )

    connection = sqlite3.connect(database_path)
    try:
        approved_count = connection.execute("SELECT COUNT(*) FROM source_files").fetchone()[0]
        indexed_source_count = connection.execute(
            "SELECT COUNT(*) FROM source_files WHERE indexed_for_retrieval = 1"
        ).fetchone()[0]
        chunk_count = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        fts_count = connection.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
        dense_count = connection.execute("SELECT COUNT(*) FROM dense_vectors").fetchone()[0]
        denied_count = connection.execute(
            """SELECT COUNT(*) FROM chunks WHERE
               source_path LIKE 'historical_baselines/%' OR
               source_path LIKE 'workspace/%' OR
               source_path LIKE 'verification/%' OR
               source_path LIKE 'experiments/%' OR
               source_path LIKE 'artifacts/%'"""
        ).fetchone()[0]
    finally:
        connection.close()

    require(approved_count == 246, f"approved source catalog mismatch: {approved_count}")
    require(indexed_source_count == 23, f"retrieval source count mismatch: {indexed_source_count}")
    require(chunk_count > 0, "no chunks were ingested")
    require(fts_count == chunk_count, "FTS row count mismatch")
    require(dense_count == chunk_count, "dense vector count mismatch")
    require(denied_count == 0, "denied sources were ingested")

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "approved_source_count": approved_count,
        "retrieval_source_count": indexed_source_count,
        "chunk_count": chunk_count,
        "fts_row_count": fts_count,
        "dense_vector_count": dense_count,
        "denied_chunk_count": denied_count,
        "cases": report_cases,
    }
    report_path = RAG_DIR / "runs" / str(config["index_id"]) / "smoke_test.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

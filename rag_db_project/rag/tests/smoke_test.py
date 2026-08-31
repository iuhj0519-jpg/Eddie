#!/usr/bin/env python3
"""Run phase-specific retrieval and leakage smoke tests."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import yaml

RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RAG_DIR.parent
sys.path.insert(0, str(RAG_DIR / "retrieve"))

from search import search  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=RAG_DIR / "config" / "prototype_index.yaml",
    )
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    database_path = project_root / "rag" / "data" / config["index_id"] / "rag_index.sqlite3"
    if not database_path.is_file():
        raise FileNotFoundError(f"index is not built: {database_path}")

    dense_weight = float(config["hybrid_retrieval"]["dense_weight"])
    sparse_weight = float(config["hybrid_retrieval"]["sparse_weight"])
    smoke = config.get("smoke_test", {})
    cases = list(smoke.get("cases", []))
    require(cases, "smoke_test.cases is empty")
    denied_prefixes = tuple(smoke.get("denied_prefixes", []))

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
            all(not str(item["source_path"]).startswith(denied_prefixes) for item in results),
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
        paths = [row[0] for row in connection.execute("SELECT source_path FROM chunks")]
    finally:
        connection.close()

    denied_count = sum(path.startswith(denied_prefixes) for path in paths)
    require(approved_count > 0, "approved source catalog is empty")
    require(indexed_source_count > 0, "retrieval source catalog is empty")
    require(chunk_count > 0, "no chunks were ingested")
    require(fts_count == chunk_count, "FTS row count mismatch")
    require(dense_count == chunk_count, "dense vector count mismatch")
    require(denied_count == 0, "denied sources were ingested")

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "index_id": config["index_id"],
        "phase": config["phase"],
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

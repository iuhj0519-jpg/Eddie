#!/usr/bin/env python3
"""Search the local prototype-generation hybrid RAG index."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from pathlib import Path

import yaml

RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RAG_DIR.parent
sys.path.insert(0, str(RAG_DIR))

from rag_index import cosine_similarity, dense_feature_vector, tokenize  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=RAG_DIR / "config" / "prototype_index.yaml",
    )
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--trust-tier", choices=["T0", "T1"])
    parser.add_argument("--path-prefix")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def safe_fts_query(query: str) -> str:
    terms = []
    for token in tokenize(query):
        escaped = token.replace('"', '""')
        if escaped and escaped not in terms:
            terms.append(escaped)
    return " OR ".join(f'"{term}"' for term in terms[:32])


def normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    minimum = min(scores.values())
    shifted = {key: value - minimum for key, value in scores.items()}
    maximum = max(shifted.values())
    if maximum <= 0:
        return {key: 1.0 for key in scores}
    return {key: value / maximum for key, value in shifted.items()}


def search(
    database_path: Path,
    query: str,
    top_k: int,
    dense_weight: float,
    sparse_weight: float,
    trust_tier: str | None = None,
    path_prefix: str | None = None,
) -> list[dict[str, object]]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        dimension = int(metadata["dense_dimension"])
        query_vector = dense_feature_vector(query, dimension)
        dense_scores: dict[str, float] = {}
        for row in connection.execute("SELECT chunk_id, vector_json FROM dense_vectors"):
            dense_scores[row["chunk_id"]] = cosine_similarity(
                query_vector, json.loads(row["vector_json"])
            )

        sparse_scores: dict[str, float] = {}
        fts_query = safe_fts_query(query)
        if fts_query:
            sql = """
                SELECT c.chunk_id, -bm25(chunks_fts, 1.0, 2.0, 3.0, 4.0) AS score
                FROM chunks_fts
                JOIN chunks c ON c.row_id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY score DESC
                LIMIT 200
            """
            for row in connection.execute(sql, (fts_query,)):
                sparse_scores[row["chunk_id"]] = float(row["score"])

        dense_normalized = normalize(dense_scores)
        sparse_normalized = normalize(sparse_scores)
        candidates = set(dense_scores) | set(sparse_scores)
        combined = {
            chunk_id: dense_weight * dense_normalized.get(chunk_id, 0.0)
            + sparse_weight * sparse_normalized.get(chunk_id, 0.0)
            for chunk_id in candidates
        }
        ranked_ids = sorted(candidates, key=lambda item: (-combined[item], item))
        results: list[dict[str, object]] = []
        for chunk_id in ranked_ids:
            row = connection.execute(
                "SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()
            if row is None:
                continue
            if trust_tier and row["trust_tier"] != trust_tier:
                continue
            if path_prefix and not row["source_path"].startswith(path_prefix):
                continue
            results.append(
                {
                    "rank": len(results) + 1,
                    "score": round(combined[chunk_id], 8),
                    "dense_score": round(dense_scores.get(chunk_id, 0.0), 8),
                    "sparse_score": round(sparse_scores.get(chunk_id, 0.0), 8),
                    "chunk_id": chunk_id,
                    "source_path": row["source_path"],
                    "source_hash": row["source_hash"],
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "version": row["version"],
                    "status": row["status"],
                    "trust_tier": row["trust_tier"],
                    "chunk_type": row["chunk_type"],
                    "module": row["module"],
                    "symbol": row["symbol"],
                    "heading": row["heading"],
                    "requirement_ids": row["requirement_ids"].split(),
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "parent_id": row["parent_id"],
                    "previous_chunk_id": row["previous_chunk_id"],
                    "next_chunk_id": row["next_chunk_id"],
                    "content": row["content"],
                }
            )
            if len(results) >= top_k:
                break
        return results
    finally:
        connection.close()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    config = yaml.safe_load(args.config.resolve().read_text(encoding="utf-8"))
    database_path = project_root / "rag" / "data" / config["index_id"] / "rag_index.sqlite3"
    if not database_path.is_file():
        raise FileNotFoundError(f"index is not built: {database_path}")
    top_k = args.top_k or int(config["hybrid_retrieval"]["default_top_k"])
    results = search(
        database_path,
        args.query,
        top_k,
        float(config["hybrid_retrieval"]["dense_weight"]),
        float(config["hybrid_retrieval"]["sparse_weight"]),
        args.trust_tier,
        args.path_prefix,
    )
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for result in results:
            location = f"{result['source_path']}:{result['line_start']}"
            print(f"[{result['rank']}] {result['score']:.4f} {location}")
            print(f"    {result['doc_id']} | {result['chunk_type']} | {result['symbol'] or result['heading']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

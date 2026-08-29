#!/usr/bin/env python3
"""Chunk approved sources and ingest them into a local hybrid SQLite index."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RAG_DIR.parent
sys.path.insert(0, str(RAG_DIR))

from rag_index import dense_feature_vector, dump_json, sha256_file, stable_id  # noqa: E402


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
REQUIREMENT_RE = re.compile(r"\bREQ-[A-Z]+-[0-9]+\b")
MODULE_RE = re.compile(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)", re.MULTILINE)
RTL_BOUNDARY_RE = re.compile(r"^\s*(always\b|initial\b|function\b|task\b|generate\b|endmodule\b)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=RAG_DIR / "config" / "prototype_index.yaml",
    )
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def run_manifest_validation(project_root: Path) -> None:
    validator = project_root / "manifests" / "validate_manifests.ps1"
    validator_argument = str(validator)
    if sys.platform != "win32":
        validator_argument = subprocess.check_output(
            ["wslpath", "-w", str(validator)], text=True
        ).strip()
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        validator_argument,
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError("manifest validation failed; ingestion aborted")


def read_checksum_inventory(project_root: Path, relative_path: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    inventory_path = project_root / relative_path
    for line_number, line in enumerate(inventory_path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValueError(f"invalid checksum line {line_number}: {line!r}")
        checksum, source_path = match.groups()
        checksums[source_path.replace("\\", "/")] = checksum
    return checksums


def verify_approved_sources(project_root: Path, checksums: dict[str, str]) -> None:
    mismatches: list[str] = []
    for source_path, expected_hash in checksums.items():
        full_path = project_root / source_path
        if not full_path.is_file():
            mismatches.append(f"missing: {source_path}")
        elif sha256_file(full_path) != expected_hash:
            mismatches.append(f"hash mismatch: {source_path}")
    if mismatches:
        raise RuntimeError("approved source verification failed:\n" + "\n".join(mismatches))


def retrieval_patterns(access_policy: dict, phase: str) -> list[str]:
    phase_policy = access_policy["phases"][phase]
    if not phase_policy.get("enabled", False):
        raise RuntimeError(f"phase is disabled: {phase}")
    return list(phase_policy["retrieval_allow"])


def expand_retrieval_sources(project_root: Path, patterns: list[str]) -> list[Path]:
    sources: set[Path] = set()
    for pattern in patterns:
        matches = sorted(project_root.glob(pattern))
        if not matches:
            raise RuntimeError(f"retrieval allow pattern matched no files: {pattern}")
        sources.update(path for path in matches if path.is_file())
    return sorted(sources, key=lambda item: item.as_posix().lower())


def markdown_metadata(lines: list[str], source_path: str) -> dict[str, object]:
    title = Path(source_path).stem
    doc_id = "DOC-" + stable_id(source_path, length=12).upper()
    version = None
    status = None
    for line in lines[:20]:
        heading = HEADING_RE.match(line)
        if heading and heading.group(1) == "#":
            title = heading.group(2)
        if line.startswith("- 문서 ID:"):
            doc_id = line.split(":", 1)[1].strip()
        elif line.startswith("- 버전:"):
            version = line.split(":", 1)[1].strip()
        elif line.startswith("- 상태:"):
            status = line.split(":", 1)[1].strip()
    return {"title": title, "doc_id": doc_id, "version": version, "status": status}


def base_chunk(
    source_path: str,
    source_hash: str,
    metadata: dict[str, object],
    chunk_type: str,
    line_start: int,
    line_end: int,
    content: str,
    *,
    heading: str | None = None,
    module: str | None = None,
    symbol: str | None = None,
) -> dict[str, object]:
    requirements = sorted(set(REQUIREMENT_RE.findall(content)))
    identity = stable_id(source_path, source_hash, chunk_type, line_start, line_end, heading, symbol)
    return {
        "chunk_id": "chunk-" + identity,
        "source_path": source_path,
        "source_hash": source_hash,
        "doc_id": metadata["doc_id"],
        "title": metadata["title"],
        "version": metadata.get("version"),
        "status": metadata.get("status"),
        "trust_tier": "T0" if source_path.lower().endswith(".md") else "T1",
        "chunk_type": chunk_type,
        "module": module,
        "symbol": symbol,
        "heading": heading,
        "requirement_ids": requirements,
        "line_start": line_start,
        "line_end": line_end,
        "parent_id": "doc-" + stable_id(source_path, source_hash),
        "previous_chunk_id": None,
        "next_chunk_id": None,
        "content": content.strip() + "\n",
    }


def split_long_section(lines: list[str], start_index: int, max_chars: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(lines):
        size = 0
        end = cursor
        while end < len(lines) and (size + len(lines[end]) + 1 <= max_chars or end == cursor):
            size += len(lines[end]) + 1
            end += 1
        ranges.append((start_index + cursor, start_index + end - 1))
        cursor = end
    return ranges


def chunk_markdown(path: Path, project_root: Path, source_hash: str, max_chars: int) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    source_path = path.relative_to(project_root).as_posix()
    metadata = markdown_metadata(lines, source_path)
    starts = [index for index, line in enumerate(lines) if HEADING_RE.match(line)]
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    starts.append(len(lines))
    chunks: list[dict[str, object]] = []

    for section_index in range(len(starts) - 1):
        section_start = starts[section_index]
        section_end = starts[section_index + 1]
        section_lines = lines[section_start:section_end]
        if not any(line.strip() for line in section_lines):
            continue
        heading_match = HEADING_RE.match(section_lines[0]) if section_lines else None
        heading = heading_match.group(2) if heading_match else metadata["title"]

        requirement_lines = [
            offset for offset, line in enumerate(section_lines) if re.match(r"^\s*-\s+REQ-[A-Z]+-[0-9]+:", line)
        ]
        if requirement_lines:
            prefix = section_lines[: requirement_lines[0]]
            if any(line.strip() for line in prefix):
                content = "\n".join(prefix)
                chunks.append(
                    base_chunk(
                        source_path,
                        source_hash,
                        metadata,
                        "markdown_heading",
                        section_start + 1,
                        section_start + len(prefix),
                        content,
                        heading=str(heading),
                    )
                )
            for offset in requirement_lines:
                content = "\n".join([section_lines[0], section_lines[offset]])
                chunks.append(
                    base_chunk(
                        source_path,
                        source_hash,
                        metadata,
                        "requirement",
                        section_start + offset + 1,
                        section_start + offset + 1,
                        content,
                        heading=str(heading),
                        symbol=REQUIREMENT_RE.search(section_lines[offset]).group(0),
                    )
                )
            continue

        if len("\n".join(section_lines)) <= max_chars:
            ranges = [(section_start, section_end - 1)]
        else:
            ranges = split_long_section(section_lines, section_start, max_chars)
        for part, (range_start, range_end) in enumerate(ranges, 1):
            content_lines = lines[range_start : range_end + 1]
            if part > 1 and heading_match:
                content_lines = [section_lines[0], "", *content_lines]
            chunks.append(
                base_chunk(
                    source_path,
                    source_hash,
                    metadata,
                    "markdown_heading",
                    range_start + 1,
                    range_end + 1,
                    "\n".join(content_lines),
                    heading=str(heading),
                    symbol=f"section_part_{part}" if len(ranges) > 1 else None,
                )
            )
    return chunks


def module_context(lines: list[str], context_lines: int) -> str:
    end = min(len(lines), context_lines)
    for index in range(end):
        if ");" in lines[index]:
            end = index + 1
            break
    return "\n".join(lines[:end])


def chunk_rtl(path: Path, project_root: Path, source_hash: str, max_lines: int, context_lines: int) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    source_path = path.relative_to(project_root).as_posix()
    module_match = MODULE_RE.search(text)
    module_name = module_match.group(1) if module_match else path.stem
    metadata = {
        "title": f"RTL module {module_name}",
        "doc_id": f"RTL-{module_name}",
        "version": None,
        "status": "approved-source",
    }
    context = module_context(lines, context_lines)
    boundaries = {0, len(lines)}
    for index, line in enumerate(lines):
        if RTL_BOUNDARY_RE.match(line):
            boundaries.add(index)
    ordered = sorted(boundaries)
    ranges: list[tuple[int, int, str]] = []
    for boundary_index in range(len(ordered) - 1):
        start = ordered[boundary_index]
        stop = ordered[boundary_index + 1]
        if stop <= start:
            continue
        cursor = start
        while cursor < stop:
            end = min(cursor + max_lines, stop)
            first_line = lines[cursor].strip() if cursor < len(lines) else ""
            boundary_match = RTL_BOUNDARY_RE.match(first_line)
            label = boundary_match.group(1) if boundary_match else "declarations"
            ranges.append((cursor, end - 1, label))
            cursor = end

    chunks: list[dict[str, object]] = []
    for part, (start, end, label) in enumerate(ranges, 1):
        excerpt = "\n".join(lines[start : end + 1])
        content = (
            f"[MODULE CONTEXT: {module_name}]\n{context}\n\n"
            f"[RTL SEGMENT: lines {start + 1}-{end + 1}]\n{excerpt}"
        )
        chunks.append(
            base_chunk(
                source_path,
                source_hash,
                metadata,
                "verilog_symbol",
                start + 1,
                end + 1,
                content,
                module=module_name,
                symbol=f"{module_name}:{label}:{part}",
            )
        )
    return chunks


def link_adjacent_chunks(chunks: list[dict[str, object]]) -> None:
    by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
    for chunk in chunks:
        by_source[str(chunk["source_path"])].append(chunk)
    for source_chunks in by_source.values():
        source_chunks.sort(key=lambda item: (int(item["line_start"]), str(item["chunk_id"])))
        for index, chunk in enumerate(source_chunks):
            chunk["previous_chunk_id"] = source_chunks[index - 1]["chunk_id"] if index else None
            chunk["next_chunk_id"] = source_chunks[index + 1]["chunk_id"] if index + 1 < len(source_chunks) else None


def create_database(
    database_path: Path,
    chunks: list[dict[str, object]],
    approved_sources: dict[str, str],
    dimension: int,
    metadata: dict[str, str],
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=FULL;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE source_files (
                source_path TEXT PRIMARY KEY,
                source_hash TEXT NOT NULL,
                indexed_for_retrieval INTEGER NOT NULL
            );
            CREATE TABLE chunks (
                row_id INTEGER PRIMARY KEY,
                chunk_id TEXT UNIQUE NOT NULL,
                source_path TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                title TEXT NOT NULL,
                version TEXT,
                status TEXT,
                trust_tier TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                module TEXT,
                symbol TEXT,
                heading TEXT,
                requirement_ids TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                parent_id TEXT NOT NULL,
                previous_chunk_id TEXT,
                next_chunk_id TEXT,
                content TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                content,
                title,
                symbol,
                requirement_ids,
                tokenize='unicode61'
            );
            CREATE TABLE dense_vectors (
                chunk_id TEXT PRIMARY KEY,
                dimension INTEGER NOT NULL,
                vector_json TEXT NOT NULL
            );
            CREATE INDEX chunks_source_path_idx ON chunks(source_path);
            CREATE INDEX chunks_doc_id_idx ON chunks(doc_id);
            CREATE INDEX chunks_symbol_idx ON chunks(symbol);
            """
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            sorted(metadata.items()),
        )
        indexed_paths = {str(chunk["source_path"]) for chunk in chunks}
        connection.executemany(
            "INSERT INTO source_files(source_path, source_hash, indexed_for_retrieval) VALUES (?, ?, ?)",
            [
                (source_path, source_hash, int(source_path in indexed_paths))
                for source_path, source_hash in sorted(approved_sources.items())
            ],
        )
        for row_id, chunk in enumerate(chunks, 1):
            requirements = " ".join(chunk["requirement_ids"])
            connection.execute(
                """INSERT INTO chunks VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )""",
                (
                    row_id,
                    chunk["chunk_id"],
                    chunk["source_path"],
                    chunk["source_hash"],
                    chunk["doc_id"],
                    chunk["title"],
                    chunk["version"],
                    chunk["status"],
                    chunk["trust_tier"],
                    chunk["chunk_type"],
                    chunk["module"],
                    chunk["symbol"],
                    chunk["heading"],
                    requirements,
                    chunk["line_start"],
                    chunk["line_end"],
                    chunk["parent_id"],
                    chunk["previous_chunk_id"],
                    chunk["next_chunk_id"],
                    chunk["content"],
                ),
            )
            connection.execute(
                "INSERT INTO chunks_fts(rowid, content, title, symbol, requirement_ids) VALUES (?, ?, ?, ?, ?)",
                (row_id, chunk["content"], chunk["title"], chunk["symbol"] or "", requirements),
            )
            searchable_text = " ".join(
                [
                    str(chunk["title"]),
                    str(chunk["heading"] or ""),
                    str(chunk["symbol"] or ""),
                    requirements,
                    str(chunk["content"]),
                ]
            )
            vector = dense_feature_vector(searchable_text, dimension)
            connection.execute(
                "INSERT INTO dense_vectors(chunk_id, dimension, vector_json) VALUES (?, ?, ?)",
                (chunk["chunk_id"], dimension, json.dumps(vector, separators=(",", ":"))),
            )
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else project_root / "rag" / "data" / str(config["index_id"])
    )

    run_manifest_validation(project_root)
    checksum_inventory_path = project_root / config["checksum_inventory"]
    checksums = read_checksum_inventory(project_root, config["checksum_inventory"])
    verify_approved_sources(project_root, checksums)

    policy = yaml.safe_load((project_root / config["access_policy"]).read_text(encoding="utf-8"))
    patterns = retrieval_patterns(policy, config["phase"])
    sources = expand_retrieval_sources(project_root, patterns)
    denied_roots = tuple(
        entry.split("/**", 1)[0].rstrip("/")
        for entry in policy["phases"][config["phase"]].get("deny", [])
    )

    chunks: list[dict[str, object]] = []
    for path in sources:
        relative_path = path.relative_to(project_root).as_posix()
        if relative_path not in checksums:
            raise RuntimeError(f"retrieval source is absent from checksum inventory: {relative_path}")
        if any(relative_path == root or relative_path.startswith(root + "/") for root in denied_roots):
            raise RuntimeError(f"denied retrieval source: {relative_path}")
        if path.suffix.lower() == ".md":
            chunks.extend(
                chunk_markdown(
                    path,
                    project_root,
                    checksums[relative_path],
                    int(config["chunking"]["markdown_max_chars"]),
                )
            )
        elif path.suffix.lower() in {".v", ".sv"}:
            chunks.extend(
                chunk_rtl(
                    path,
                    project_root,
                    checksums[relative_path],
                    int(config["chunking"]["rtl_max_lines"]),
                    int(config["chunking"]["rtl_context_lines"]),
                )
            )
        else:
            raise RuntimeError(f"unsupported retrieval source type: {relative_path}")

    chunks.sort(key=lambda item: (str(item["source_path"]), int(item["line_start"]), str(item["chunk_id"])))
    link_adjacent_chunks(chunks)
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / "chunks.jsonl"
    chunks_path.write_text(
        "".join(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n" for chunk in chunks),
        encoding="utf-8",
    )

    database_path = output_dir / "rag_index.sqlite3"
    dimension = int(config["dense_index"]["dimension"])
    database_metadata = {
        "schema_version": "1.0",
        "index_id": str(config["index_id"]),
        "phase": str(config["phase"]),
        "source_git_tag": str(config["source_git_tag"]),
        "source_inventory_sha256": sha256_file(checksum_inventory_path),
        "dense_algorithm": str(config["dense_index"]["algorithm"]),
        "dense_dimension": str(dimension),
        "sparse_engine": str(config["sparse_index"]["engine"]),
        "chunk_count": str(len(chunks)),
    }
    create_database(database_path, chunks, checksums, dimension, database_metadata)

    counts_by_type: dict[str, int] = defaultdict(int)
    counts_by_tier: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        counts_by_type[str(chunk["chunk_type"])] += 1
        counts_by_tier[str(chunk["trust_tier"])] += 1

    receipt = {
        "schema_version": "1.0",
        "status": "built",
        "index_id": config["index_id"],
        "phase": config["phase"],
        "source_git_tag": config["source_git_tag"],
        "source_inventory_sha256": sha256_file(checksum_inventory_path),
        "approved_source_count": len(checksums),
        "retrieval_source_count": len(sources),
        "chunk_count": len(chunks),
        "chunk_counts_by_type": dict(sorted(counts_by_type.items())),
        "chunk_counts_by_trust_tier": dict(sorted(counts_by_tier.items())),
        "dense_algorithm": config["dense_index"]["algorithm"],
        "dense_dimension": dimension,
        "sparse_engine": config["sparse_index"]["engine"],
        "sparse_ranking": config["sparse_index"]["ranking"],
        "artifacts": {
            "chunks": {
                "path": chunks_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(chunks_path),
            },
            "database": {
                "path": database_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(database_path),
            },
        },
    }
    receipt_path = output_dir / "build_receipt.json"
    dump_json(receipt_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

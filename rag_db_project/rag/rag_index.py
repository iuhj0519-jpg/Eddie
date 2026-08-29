"""Shared deterministic indexing and retrieval helpers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*|[0-9]+|[가-힣]+")
IDENTIFIER_SPLIT_RE = re.compile(r"[_$]+|(?<=[a-z0-9])(?=[A-Z])")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(*parts: object, length: int = 24) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return sha256_bytes(payload)[:length]


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in TOKEN_RE.finditer(text):
        token = match.group(0).lower()
        tokens.append(token)
        if re.fullmatch(r"[a-z_][a-z0-9_$]*", token):
            subtokens = [part.lower() for part in IDENTIFIER_SPLIT_RE.split(match.group(0)) if len(part) > 1]
            tokens.extend(subtokens)
    return tokens


def dense_feature_vector(text: str, dimension: int) -> list[float]:
    """Create a dependency-free dense vector from tokens and character trigrams.

    This is deterministic feature hashing, not a learned language-model embedding.
    It keeps ingestion reproducible offline and is paired with SQLite FTS5 BM25.
    """

    values = [0.0] * dimension
    features: list[str] = []
    for token in tokenize(text):
        features.append("tok:" + token)
        if len(token) >= 4:
            features.extend("c3:" + token[index : index + 3] for index in range(len(token) - 2))

    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] & 1 else -1.0
        values[index] += sign

    norm = math.sqrt(sum(value * value for value in values))
    if norm:
        values = [round(value / norm, 8) for value in values]
    return values


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

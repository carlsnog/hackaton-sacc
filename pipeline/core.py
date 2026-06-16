from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import unicodedata
from pathlib import Path
from typing import Iterable


NULL_MARKERS = {"", "#NULO", "#NE", "-1", "-3"}
NULL_REASONS = {
    "": "VAZIO",
    "#NULO": "NULO_FONTE",
    "-1": "NULO_FONTE",
    "#NE": "NAO_EXISTIA_REGISTRO",
    "-3": "NAO_EXISTIA_REGISTRO",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: str | Path) -> dict:
    target = Path(path)
    if not target.is_absolute():
        target = project_root() / target
    return json.loads(target.read_text(encoding="utf-8"))


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_name = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_name = re.sub(r"\s+\(PB\)$", "", ascii_name, flags=re.IGNORECASE)
    return re.sub(r"[^A-Z0-9]+", " ", ascii_name.upper()).strip()


def nullable_number(value: str, cast=float):
    if value.strip().upper() in NULL_MARKERS:
        return None
    return cast(value)


def nullable_number_with_reason(value: str, cast=float):
    normalized = value.strip().upper()
    if normalized in NULL_MARKERS:
        return None, NULL_REASONS[normalized]
    return cast(value), None


def abstention_rate(abstentions: int, eligible_voters: int) -> float | None:
    return 100 * abstentions / eligible_voters if eligible_voters else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_snapshot_id(paths: Iterable[Path], config: dict) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(sha256_file(path).encode())
    transformation_config = {"pipeline_version": config.get("pipeline_version", "unversioned"), "score": config["score"]}
    digest.update(json.dumps(transformation_config, ensure_ascii=True, sort_keys=True).encode())
    return digest.hexdigest()[:16]


def percentile_ranks(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [0.5]
    ordered = sorted(values)
    return [sum(candidate <= value for candidate in ordered) - 1 for value in values]


def normalized_percentile_ranks(values: list[float]) -> list[float]:
    raw = percentile_ranks(values)
    if len(values) <= 1:
        return raw
    return [value / (len(values) - 1) for value in raw]


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys))
    return numerator / denominator if denominator else None


def spearman(xs: list[float], ys: list[float]) -> float | None:
    def ranks(values: list[float]) -> list[float]:
        ordered = sorted(values)
        return [
            statistics.mean(index + 1 for index, candidate in enumerate(ordered) if candidate == value)
            for value in values
        ]

    return pearson(ranks(xs), ranks(ys))


def load_env() -> None:
    if os.environ.get("TESTING") == "true":
        return
    env_path = project_root() / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

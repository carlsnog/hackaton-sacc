from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from pipeline.core import load_json, project_root


FIELDS = [
    "indicador",
    "ano",
    "nivel_territorial",
    "codigo_localidade",
    "localidade",
    "variavel",
    "unidade",
    "valor",
    "classificacao",
    "categoria",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_json(url: str, timeout: int, retries: int) -> bytes:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with urlopen(url, timeout=timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"SIDRA respondeu HTTP {response.status}")
                return response.read()
        except Exception as error:  # pragma: no cover - network failure path
            last_error = error
            if attempt < retries:
                time.sleep(attempt)
    raise RuntimeError(f"Falha ao consultar SIDRA apos {retries} tentativas: {last_error}")


def decode_json(content: bytes) -> list[dict]:
    decoded = gzip.decompress(content) if content.startswith(b"\x1f\x8b") else content
    return json.loads(decoded)


def build_url(base_url: str, source: dict) -> str:
    variables = "|".join(source["variables"])
    classifications = quote(source["classifications"], safe="")
    return (
        f"{base_url}/{source['table']}/periodos/{source['period']}/variaveis/{quote(variables, safe='')}"
        f"?localidades=N3%5B25%5D%7CN6%5BN3%5B25%5D%5D&classificacao={classifications}"
    )


def local_name(series: dict) -> str:
    locality = series["localidade"]
    name = locality["nome"]
    return name.replace(" - PB", " (PB)") if locality["nivel"]["id"] == "N6" else name


def level_name(series: dict) -> str:
    return series["localidade"]["nivel"]["nome"]


def classification(result: dict, category_dimension: str | None = None) -> tuple[str, str]:
    names, categories = [], []
    for item in result["classificacoes"]:
        if category_dimension and item["id"] != category_dimension:
            continue
        names.append(item["nome"])
        categories.append(next(iter(item["categoria"].values())))
    return " | ".join(names), " | ".join(categories)


def normalize_sidra_value(value: str) -> str:
    return "0" if value == "-" else value


def standardized_rows(payload: list[dict], indicators: dict[str, str], category_dimension: str | None = None) -> list[dict]:
    rows = []
    for variable in payload:
        indicator = indicators[variable["id"]]
        for result in variable["resultados"]:
            classification_name, category = classification(result, category_dimension)
            for series in result["series"]:
                rows.append(
                    {
                        "indicador": indicator,
                        "ano": next(iter(series["serie"])),
                        "nivel_territorial": level_name(series),
                        "codigo_localidade": series["localidade"]["id"],
                        "localidade": local_name(series),
                        "variavel": variable["variavel"],
                        "unidade": variable["unidade"],
                        "valor": normalize_sidra_value(next(iter(series["serie"].values()))),
                        "classificacao": classification_name,
                        "categoria": category,
                    }
                )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate(rows: list[dict], expected_rows: int, indicator: str) -> None:
    if len(rows) != expected_rows:
        raise ValueError(f"{indicator}: esperadas {expected_rows} linhas, recebidas {len(rows)}")
    municipality_codes = {row["codigo_localidade"] for row in rows if row["nivel_territorial"] == "Município"}
    if len(municipality_codes) != 223:
        raise ValueError(f"{indicator}: esperados 223 municipios, recebidos {len(municipality_codes)}")


def run(config_path: str = "config/sidra.json") -> dict:
    config = load_json(config_path)
    root = project_root()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / config["raw_directory"] / stamp
    output_dir = root / config["output_directory"]
    raw_dir.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"started_at": now(), "status": "running", "sources": []}
    generated: dict[str, list[dict]] = {}
    try:
        for key in ("income", "income_ranges"):
            source = config[key]
            url = build_url(config["base_url"], source)
            raw = request_json(url, config["timeout_seconds"], config["retries"])
            raw_path = raw_dir / f"sidra_{source['table']}_{source['period']}.json"
            raw_path.write_bytes(raw)
            payload = decode_json(raw)
            rows = standardized_rows(payload, source["variables"], source.get("category_dimension"))
            generated[key] = rows
            manifest["sources"].append(
                {
                    "table": source["table"],
                    "period": source["period"],
                    "url": url,
                    "raw_path": str(raw_path.relative_to(root)),
                    "sha256": sha256(raw),
                    "size_bytes": len(raw),
                    "standardized_rows": len(rows),
                }
            )
        income_by_indicator = {}
        for row in generated["income"]:
            income_by_indicator.setdefault(row["indicador"], []).append(row)
        ranges_by_indicator = {}
        for row in generated["income_ranges"]:
            ranges_by_indicator.setdefault(row["indicador"], []).append(row)
        outputs = [
            ("2022_renda_media_domiciliar_per_capita_paraiba.csv", income_by_indicator["Renda média domiciliar per capita"], 224),
            ("2022_renda_mediana_domiciliar_per_capita_paraiba.csv", income_by_indicator["Renda mediana domiciliar per capita"], 224),
            ("2022_distribuicao_por_faixas_de_renda_paraiba.csv", ranges_by_indicator["Distribuição por faixas de renda"], 2688),
            ("2022_percentual_por_faixas_de_renda_paraiba.csv", ranges_by_indicator["Percentual por faixas de renda"], 2688),
        ]
        consolidated = []
        for filename, rows, expected in outputs:
            validate(rows, expected, filename)
            write_csv(output_dir / filename, rows)
            consolidated.extend(rows)
        validate(consolidated, 5824, "indicadores_socioeconomicos_paraiba.csv")
        write_csv(output_dir / "indicadores_socioeconomicos_paraiba.csv", consolidated)
        manifest.update({"finished_at": now(), "status": "success", "standardized_rows": len(consolidated)})
        (raw_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
    except Exception as error:
        manifest.update({"finished_at": now(), "status": "failed", "error": str(error)})
        (raw_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/sidra.json")
    args = parser.parse_args()
    print(json.dumps(run(args.config), ensure_ascii=False, indent=2))

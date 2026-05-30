from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pipeline.core import (
    abstention_rate,
    load_json,
    normalize_name,
    normalized_percentile_ranks,
    project_root,
    sha256_file,
    stable_snapshot_id,
)

SCHOOLING_FIELDS = (
    "ANALFABETO",
    "ENSINO FUNDAMENTAL COMPLETO",
    "ENSINO FUNDAMENTAL INCOMPLETO",
    "ENSINO MÉDIO COMPLETO",
    "ENSINO MÉDIO INCOMPLETO",
    "LÊ E ESCREVE",
    "SUPERIOR COMPLETO",
    "SUPERIOR INCOMPLETO",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript((project_root() / "pipeline/schema.sql").read_text(encoding="utf-8"))
    existing = {row[1] for row in connection.execute("PRAGMA table_info(mart_municipio_eleicao)")}
    for name, definition in (
        ("pib_mil_reais", "REAL"),
        ("sexo_feminino", "INTEGER"),
        ("sexo_masculino", "INTEGER"),
        ("escolaridade_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("escolaridade_predominante", "TEXT"),
        ("escolaridade_predominante_total", "INTEGER"),
    ):
        if name not in existing:
            connection.execute(f"ALTER TABLE mart_municipio_eleicao ADD COLUMN {name} {definition}")


def add_quality(quality: dict, level: str, code: str, message: str, **details) -> None:
    quality.setdefault("messages", []).append({"level": level, "code": code, "message": message, **details})


def load_electoral(rows: list[dict], quality: dict) -> list[dict]:
    required = {
        "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCAO",
        "codigo_ibge", "pib_mil_reais", "FEMININO", "MASCULINO", *SCHOOLING_FIELDS,
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Arquivo eleitoral sem colunas obrigatorias")
    result = []
    seen = set()
    for row in rows:
        if row["SG_UF"] != "PB":
            continue
        code = row["CD_MUNICIPIO"].strip()
        if code in seen:
            raise ValueError(f"Codigo TSE duplicado no agregado municipal: {code}")
        seen.add(code)
        aptos = int(row["QT_APTOS"])
        comparecimento = int(row["QT_COMPARECIMENTO"])
        abstencoes = int(row["QT_ABSTENCAO"])
        if aptos != comparecimento + abstencoes:
            raise ValueError(f"Falha de reconciliacao eleitoral em {code}")
        taxa = abstention_rate(abstencoes, aptos)
        schooling = {field: int(float(row[field])) for field in SCHOOLING_FIELDS}
        schooling_predominant = max(schooling, key=schooling.get)
        if taxa is None:
            add_quality(quality, "warning", "ELECTORAL_ZERO_DENOMINATOR", "Municipio sem eleitores aptos", cod_tse=code)
        elif not 0 <= taxa <= 100:
            raise ValueError(f"Taxa de abstencao fora do intervalo esperado em {code}")
        result.append(
            {
                "cod_tse": code,
                "municipio": row["NM_MUNICIPIO"].strip(),
                "aptos": aptos,
                "comparecimento": comparecimento,
                "abstencoes": abstencoes,
                "brancos": int(row["VOTOS_BRANCOS"]),
                "nulos": int(row["VOTOS_NULOS"]),
                "taxa": taxa or 0.0,
                "cod_ibge": row["codigo_ibge"].strip(),
                "pib_mil_reais": float(row["pib_mil_reais"]),
                "sexo_feminino": int(float(row["FEMININO"])),
                "sexo_masculino": int(float(row["MASCULINO"])),
                "escolaridade": schooling,
                "escolaridade_predominante": schooling_predominant,
                "escolaridade_predominante_total": schooling[schooling_predominant],
            }
        )
    quality["electoral"] = {
        "grain": "municipio agregado; inclui contexto local de PIB, sexo e escolaridade",
        "rows": len(result),
        "reconciliation_errors": 0,
        "expected_pb_municipalities": 223,
    }
    if len(result) != 223:
        raise ValueError(f"Esperados 223 municipios eleitorais PB, recebidos {len(result)}")
    add_quality(quality, "info", "ELECTORAL_UNIVERSE_VALIDATED", "Universo eleitoral PB validado", rows=len(result))
    return result


def load_income(rows: list[dict], low_income_categories: list[str], quality: dict) -> list[dict]:
    municipalities: dict[str, dict] = {}
    for row in rows:
        if row["nivel_territorial"] != "Município":
            continue
        code = row["codigo_localidade"].strip()
        item = municipalities.setdefault(code, {"cod_ibge": code, "municipio": row["localidade"], "faixas": {}})
        indicator = row["indicador"]
        if indicator == "Renda média domiciliar per capita":
            item["ano_renda"] = int(row["ano"])
            item["renda_media"] = float(row["valor"])
        elif indicator == "Renda mediana domiciliar per capita":
            item["ano_renda"] = int(row["ano"])
            item["renda_mediana"] = float(row["valor"])
        elif indicator == "Percentual por faixas de renda" and row["categoria"] != "Total":
            item["ano_faixas"] = int(row["ano"])
            item["faixas"][row["categoria"]] = float(row["valor"])
    result = []
    for item in municipalities.values():
        if "renda_media" not in item or "renda_mediana" not in item:
            continue
        faixas = item["faixas"]
        item["ano_faixas"] = item.get("ano_faixas", item["ano_renda"])
        invalid_percentages = {category: value for category, value in faixas.items() if not 0 <= value <= 100}
        if invalid_percentages:
            raise ValueError(f"Percentuais de renda fora do intervalo esperado em {item['cod_ibge']}: {invalid_percentages}")
        faixa_sum = sum(faixas.values())
        item["soma_pct_faixas"] = faixa_sum
        if faixas and not 99.9 <= faixa_sum <= 100.1:
            raise ValueError(f"Soma das faixas de renda fora da tolerancia em {item['cod_ibge']}: {faixa_sum}")
        item["pct_baixa_renda"] = sum(faixas.get(category, 0.0) for category in low_income_categories)
        predominant = max(faixas, key=faixas.get) if faixas else None
        item["faixa_predominante"] = predominant
        item["faixa_predominante_pct"] = faixas.get(predominant) if predominant else None
        result.append(item)
    quality["income"] = {
        "grain": "municipio x periodo; faixas de renda usam periodo proprio",
        "municipalities": len(result),
        "expected_full_pb_municipalities": 223,
        "coverage_warning": "Fonte socioeconomica local parcial" if len(result) < 223 else None,
        "faixa_percentage_sum_min": min((row["soma_pct_faixas"] for row in result), default=None),
        "faixa_percentage_sum_max": max((row["soma_pct_faixas"] for row in result), default=None),
        "faixa_percentage_sum_tolerance": [99.9, 100.1],
    }
    if len(result) < 223:
        add_quality(
            quality,
            "warning",
            "SOCIOECONOMIC_PARTIAL_COVERAGE",
            "Fonte socioeconomica local nao cobre todos os municipios PB",
            available=len(result),
            expected=223,
        )
    return result


def build_crosswalk(electoral: list[dict], income: list[dict], quality: dict) -> tuple[list[dict], list[dict]]:
    income_by_code = {row["cod_ibge"]: row for row in income}
    income_by_name = {normalize_name(row["municipio"]): row for row in income}
    dimension, unmatched = [], []
    for row in electoral:
        normalized = normalize_name(row["municipio"])
        matched = income_by_code.get(row["cod_ibge"]) or income_by_name.get(normalized)
        method = "provided_ibge_code" if row["cod_ibge"] in income_by_code else "local_name_fallback"
        dimension.append(
            {
                "cod_tse": row["cod_tse"],
                "cod_ibge": matched["cod_ibge"] if matched else None,
                "municipio": row["municipio"],
                "normalized": normalized,
                "method": method if matched else "unmatched_local_source",
            }
        )
        if not matched:
            unmatched.append({"cod_tse_municipio": row["cod_tse"], "municipio": row["municipio"]})
    quality["crosswalk"] = {
        "method": "provided_ibge_code",
        "matched": len(dimension) - len(unmatched),
        "unmatched": len(unmatched),
        "warning": None,
    }
    add_quality(quality, "info", "CROSSWALK_IBGE_CODE", "Correspondencias construidas pelo codigo IBGE presente na fonte local", matched=len(dimension) - len(unmatched), unmatched=len(unmatched))
    return dimension, unmatched


def write_rag_documents(connection: sqlite3.Connection, snapshot_id: str, directory: Path) -> None:
    target = directory / snapshot_id
    target.mkdir(parents=True, exist_ok=True)
    sources = [
        dict(row)
        for row in connection.execute("SELECT source_name, path, sha256 FROM source_manifest WHERE snapshot_id = ?", (snapshot_id,))
    ]
    totals = connection.execute(
        "SELECT SUM(total_aptos) aptos, SUM(total_abstencoes) abstencoes FROM mart_municipio_eleicao WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    recorte_rate = abstention_rate(totals["abstencoes"], totals["aptos"])
    for row in connection.execute("SELECT * FROM mart_municipio_eleicao WHERE snapshot_id = ?", (snapshot_id,)):
        data = dict(row)
        delta = data["taxa_abstencao_pct"] - recorte_rate
        faixas = json.loads(data["faixas_json"])
        document = {
            "metadata": {
                "snapshot_id": snapshot_id,
                "cod_ibge_municipio": data["cod_ibge_municipio"],
                "ano_eleicao": data["ano_eleicao"],
                "turno": data["turno"],
                "ano_referencia_renda": data["ano_referencia_renda"],
                "ano_referencia_faixas": data["ano_referencia_faixas"],
                "score_version": data["score_version"],
            },
            "data": {
                "taxa_abstencao_pct": data["taxa_abstencao_pct"],
                "delta_abstencao_vs_recorte_pct": delta,
                "renda_pc_media": data["renda_pc_media"],
                "renda_pc_mediana": data["renda_pc_mediana"],
                "faixas_renda_pct": faixas,
                "pct_baixa_renda": data["pct_baixa_renda"],
                "faixa_renda_predominante": data["faixa_renda_predominante"],
                "score_vulnerabilidade": data["score_vulnerabilidade"],
                "score_weights": json.loads(data["score_weights_json"]),
                "pib_mil_reais": data["pib_mil_reais"],
                "sexo_feminino": data["sexo_feminino"],
                "sexo_masculino": data["sexo_masculino"],
                "escolaridade": json.loads(data["escolaridade_json"]),
                "escolaridade_predominante": data["escolaridade_predominante"],
            },
            "sources": sources,
            "text": (
                f"Municipio: {data['municipio']}. Codigo IBGE: {data['cod_ibge_municipio']}. "
                f"Eleicao: {data['ano_eleicao']}, turno {data['turno']}. "
                f"Taxa de abstencao: {data['taxa_abstencao_pct']:.2f}%. "
                f"Diferenca contra a taxa ponderada do recorte local: {delta:+.2f} pontos percentuais. "
                f"Renda domiciliar per capita mediana: R$ {data['renda_pc_mediana']:.2f}. "
                f"PIB municipal: R$ {data['pib_mil_reais']:.2f} mil. "
                f"Sexo feminino: {data['sexo_feminino']}; sexo masculino: {data['sexo_masculino']}. "
                f"Escolaridade predominante: {data['escolaridade_predominante']}. "
                f"Faixa de renda predominante: {data['faixa_renda_predominante']} "
                f"({data['faixa_renda_predominante_pct']:.2f}%). "
                f"Score exploratorio: {data['score_vulnerabilidade']:.2f}/100. "
                "Os dados descrevem associacao territorial agregada e nao demonstram causalidade."
            ),
        }
        (target / f"{data['cod_ibge_municipio']}.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def run(config_path: str = "config/settings.json") -> str:
    config = load_json(config_path)
    if abs(sum(config["score"]["weights"].values()) - 1.0) > 1e-9:
        raise ValueError("Os pesos do score devem somar 1")
    root = project_root()
    electoral_path = root / config["electoral_source"]
    income_path = root / config["socioeconomic_source"]
    db_path = root / config["database_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    report_dir = root / config["report_directory"]
    report_dir.mkdir(parents=True, exist_ok=True)
    snapshot_id = stable_snapshot_id([electoral_path, income_path], config)
    run_id = str(uuid.uuid4())
    quality: dict = {"snapshot_id": snapshot_id, "run_id": run_id, "started_at": now(), "status": "running"}
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    connection.execute(
        "INSERT INTO pipeline_run VALUES (?, ?, ?, NULL, 'running', ?)",
        (run_id, snapshot_id, quality["started_at"], json.dumps(quality, ensure_ascii=False)),
    )
    connection.commit()
    try:
        electoral_raw, income_raw = read_csv(electoral_path), read_csv(income_path)
        electoral = load_electoral(electoral_raw, quality)
        income = load_income(income_raw, config["score"]["low_income_categories"], quality)
        dimension, unmatched = build_crosswalk(electoral, income, quality)
        quality["unmatched_municipalities"] = unmatched
        for name, path, rows in (("electoral_local", electoral_path, electoral_raw), ("socioeconomic_local", income_path, income_raw)):
            connection.execute(
                "INSERT OR IGNORE INTO source_manifest VALUES (?, ?, ?, ?, ?, ?)",
                (snapshot_id, name, str(path.relative_to(root)), sha256_file(path), path.stat().st_size, len(rows)),
            )
        connection.executemany(
            "INSERT OR IGNORE INTO dim_municipio VALUES (?, ?, ?, ?, ?, 'PB', 1, ?)",
            [(snapshot_id, row["cod_tse"], row["cod_ibge"], row["municipio"], row["normalized"], row["method"]) for row in dimension],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO fact_abstencao_municipio VALUES (?, 2022, 'LOCAL-2022', 'Eleicao 2022 - agregado municipal local', 1, ?, ?, ?, ?, ?, ?, ?)",
            [(snapshot_id, row["cod_tse"], row["aptos"], row["comparecimento"], row["abstencoes"], row["brancos"], row["nulos"], row["taxa"]) for row in electoral],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO fact_renda_municipio VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(snapshot_id, row["cod_ibge"], row["municipio"], row["ano_renda"], row["ano_faixas"], row["renda_media"], row["renda_mediana"], json.dumps(row["faixas"], ensure_ascii=False), row["pct_baixa_renda"], row["faixa_predominante"], row["faixa_predominante_pct"]) for row in income],
        )
        bridge = {row["cod_tse"]: row["cod_ibge"] for row in dimension if row["cod_ibge"]}
        income_map = {row["cod_ibge"]: row for row in income}
        joined = [(row, income_map[bridge[row["cod_tse"]]]) for row in electoral if row["cod_tse"] in bridge]
        abst_ranks = normalized_percentile_ranks([row[0]["taxa"] for row in joined])
        income_ranks = normalized_percentile_ranks([row[1]["renda_mediana"] for row in joined])
        low_ranks = normalized_percentile_ranks([row[1]["pct_baixa_renda"] for row in joined])
        weights = config["score"]["weights"]
        mart_rows = []
        for index, (vote, income_row) in enumerate(joined):
            income_low = 1 - income_ranks[index]
            score = 100 * (
                weights["abstencao"] * abst_ranks[index]
                + weights["renda_baixa"] * income_low
                + weights["pct_baixa_renda"] * low_ranks[index]
            )
            mart_rows.append((
                snapshot_id, income_row["cod_ibge"], vote["cod_tse"], vote["municipio"], 2022, "LOCAL-2022",
                "Eleicao 2022 - agregado municipal local", 1, income_row["ano_renda"], income_row["ano_faixas"],
                vote["aptos"], vote["comparecimento"], vote["abstencoes"], vote["brancos"], vote["nulos"], vote["taxa"],
                income_row["renda_media"], income_row["renda_mediana"], json.dumps(income_row["faixas"], ensure_ascii=False),
                income_row["pct_baixa_renda"], income_row["faixa_predominante"], income_row["faixa_predominante_pct"],
                abst_ranks[index], income_low, low_ranks[index], score, config["score"]["version"],
                json.dumps(weights, ensure_ascii=False, sort_keys=True),
                vote["pib_mil_reais"], vote["sexo_feminino"], vote["sexo_masculino"],
                json.dumps(vote["escolaridade"], ensure_ascii=False, sort_keys=True),
                vote["escolaridade_predominante"], vote["escolaridade_predominante_total"],
            ))
        connection.executemany("INSERT OR IGNORE INTO mart_municipio_eleicao VALUES (" + ",".join("?" * 34) + ")", mart_rows)
        quality["mart"] = {
            "rows": len(mart_rows),
            "coverage": "complete" if len(mart_rows) == 223 else "partial",
            "missing_income": 223 - len(mart_rows),
        }
        add_quality(quality, "info", "MART_PUBLISHED", "Mart analitico publicado", rows=len(mart_rows), snapshot_id=snapshot_id)
        quality["status"], quality["finished_at"] = "success", now()
        connection.execute(
            "UPDATE pipeline_run SET finished_at = ?, status = 'success', details_json = ? WHERE run_id = ?",
            (quality["finished_at"], json.dumps(quality, ensure_ascii=False), run_id),
        )
        connection.commit()
        write_rag_documents(connection, snapshot_id, root / config["rag_directory"])
        (report_dir / f"{snapshot_id}.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
        return snapshot_id
    except Exception as error:
        quality["status"], quality["finished_at"], quality["error"] = "failed", now(), str(error)
        connection.execute(
            "UPDATE pipeline_run SET finished_at = ?, status = 'failed', details_json = ? WHERE run_id = ?",
            (quality["finished_at"], json.dumps(quality, ensure_ascii=False), run_id),
        )
        connection.commit()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/settings.json")
    args = parser.parse_args()
    print(run(args.config))

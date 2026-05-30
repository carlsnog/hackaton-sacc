from __future__ import annotations

import json
import sqlite3
import statistics
from pathlib import Path

from pipeline.core import load_json, project_root


SORT_FIELDS = {
    "municipio": "municipio",
    "taxa_abstencao_pct": "taxa_abstencao_pct",
    "renda_pc_mediana": "renda_pc_mediana",
    "renda_pc_media": "renda_pc_media",
    "score_vulnerabilidade": "score_vulnerabilidade",
    "pct_baixa_renda": "pct_baixa_renda",
}


class AnalyticsRepository:
    def __init__(self, config: dict | None = None):
        self.config = config or load_json("config/settings.json")
        self.db_path = project_root() / self.config["database_path"]

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def active_snapshot(self, connection: sqlite3.Connection) -> str:
        row = connection.execute(
            "SELECT snapshot_id FROM pipeline_run WHERE status = 'success' ORDER BY finished_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            raise RuntimeError("Nenhum snapshot publicado. Execute o pipeline.")
        return row["snapshot_id"]

    def filters(self, params: dict, connection: sqlite3.Connection) -> tuple[str, list]:
        defaults = self.config["defaults"]
        snapshot = params.get("snapshot_id") or self.active_snapshot(connection)
        try:
            values = [
                snapshot,
                int(params.get("ano_eleicao", defaults["ano_eleicao"])),
                int(params.get("turno", defaults["turno"])),
                int(params.get("ano_renda", defaults["ano_renda"])),
            ]
        except ValueError as error:
            raise ValueError("Filtros temporais devem ser inteiros") from error
        where = "snapshot_id = ? AND ano_eleicao = ? AND turno = ? AND ano_referencia_renda = ?"
        search = params.get("busca", "").strip()
        if search:
            where += " AND municipio LIKE ?"
            values.append(f"%{search}%")
        return where, values

    def serialize_municipality(self, row: sqlite3.Row | dict) -> dict:
        item = dict(row)
        item["faixas_renda_pct"] = json.loads(item.pop("faixas_json"))
        item["score_weights"] = json.loads(item.pop("score_weights_json"))
        item["score_components"] = {
            "percentil_abstencao": item["percentil_abstencao"],
            "percentil_renda_baixa": item["percentil_renda_baixa"],
            "percentil_baixa_renda": item["percentil_baixa_renda"],
        }
        return item

    def sources(self, connection: sqlite3.Connection, snapshot_id: str) -> list[dict]:
        return [
            dict(row)
            for row in connection.execute("SELECT * FROM source_manifest WHERE snapshot_id = ? ORDER BY source_name", (snapshot_id,))
        ]

    def list_municipalities(self, params: dict) -> dict:
        with self.connect() as connection:
            where, values = self.filters(params, connection)
            try:
                page = max(1, int(params.get("page", 1)))
                page_size = int(params.get("page_size", self.config["api"]["default_page_size"]))
            except ValueError as error:
                raise ValueError("page e page_size devem ser inteiros") from error
            if not 1 <= page_size <= self.config["api"]["max_page_size"]:
                raise ValueError(f"page_size deve estar entre 1 e {self.config['api']['max_page_size']}")
            sort = params.get("sort", "taxa_abstencao_pct")
            if sort not in SORT_FIELDS:
                raise ValueError(f"Ordenacao invalida: {sort}")
            order = params.get("order", "desc").lower()
            if order not in {"asc", "desc"}:
                raise ValueError("order deve ser asc ou desc")
            total = connection.execute(f"SELECT COUNT(*) total FROM mart_municipio_eleicao WHERE {where}", values).fetchone()["total"]
            rows = connection.execute(
                f"SELECT * FROM mart_municipio_eleicao WHERE {where} ORDER BY {SORT_FIELDS[sort]} {order}, municipio ASC LIMIT ? OFFSET ?",
                [*values, page_size, (page - 1) * page_size],
            ).fetchall()
            return {"items": [self.serialize_municipality(row) for row in rows], "page": page, "page_size": page_size, "total": total}

    def export_municipalities(self, params: dict) -> list[dict]:
        with self.connect() as connection:
            where, values = self.filters(params, connection)
            sort = params.get("sort", "taxa_abstencao_pct")
            if sort not in SORT_FIELDS:
                raise ValueError(f"Ordenacao invalida: {sort}")
            order = params.get("order", "desc").lower()
            if order not in {"asc", "desc"}:
                raise ValueError("order deve ser asc ou desc")
            rows = connection.execute(
                f"SELECT * FROM mart_municipio_eleicao WHERE {where} ORDER BY {SORT_FIELDS[sort]} {order}, municipio ASC",
                values,
            ).fetchall()
            return [self.serialize_municipality(row) for row in rows]

    def summary(self, params: dict) -> dict:
        from pipeline.core import pearson, spearman

        with self.connect() as connection:
            where, values = self.filters(params, connection)
            rows = [dict(row) for row in connection.execute(f"SELECT * FROM mart_municipio_eleicao WHERE {where}", values)]
            if not rows:
                raise ValueError("Nenhum municipio disponivel para o recorte")
            xs = [row["renda_pc_mediana"] for row in rows if row["renda_pc_mediana"] is not None]
            ys = [row["taxa_abstencao_pct"] for row in rows if row["renda_pc_mediana"] is not None]
            aptos, abstencoes = sum(row["total_aptos"] for row in rows), sum(row["total_abstencoes"] for row in rows)
            return {
                "snapshot_id": rows[0]["snapshot_id"],
                "ano_eleicao": rows[0]["ano_eleicao"],
                "turno": rows[0]["turno"],
                "ano_referencia_renda": rows[0]["ano_referencia_renda"],
                "ano_referencia_faixas": rows[0]["ano_referencia_faixas"],
                "municipios_validos": len(rows),
                "cobertura": "parcial: somente municipios com renda na fonte local",
                "total_aptos": aptos,
                "total_abstencoes": abstencoes,
                "taxa_abstencao_pct": 100 * abstencoes / aptos if aptos else None,
                "renda_pc_mediana_dos_municipios": statistics.median(xs) if xs else None,
                "correlacao_pearson": pearson(xs, ys),
                "correlacao_spearman": spearman(xs, ys),
                "municipios_excluidos_correlacao": len(rows) - len(xs),
                "nota_metodologica": "Correlacao descreve associacao territorial agregada e nao demonstra causalidade.",
                "sources": self.sources(connection, rows[0]["snapshot_id"]),
            }

    def municipality(self, cod_ibge: str, params: dict) -> dict | None:
        with self.connect() as connection:
            where, values = self.filters(params, connection)
            row = connection.execute(
                f"SELECT * FROM mart_municipio_eleicao WHERE {where} AND cod_ibge_municipio = ?",
                [*values, cod_ibge],
            ).fetchone()
            if not row:
                return None
            item = self.serialize_municipality(row)
            summary = self.summary(params)
            item["delta_abstencao_vs_pb_recorte"] = item["taxa_abstencao_pct"] - summary["taxa_abstencao_pct"]
            item["comparacao_recorte"] = summary
            item["sources"] = self.sources(connection, item["snapshot_id"])
            return item

    def ranking(self, params: dict) -> dict:
        metric = params.get("metric", "taxa_abstencao_pct")
        if metric not in SORT_FIELDS or metric == "municipio":
            raise ValueError(f"Metrica de ranking invalida: {metric}")
        try:
            limit = int(params.get("limit", 10))
        except ValueError as error:
            raise ValueError("limit deve ser inteiro") from error
        maximum = self.config["api"]["max_ranking_limit"]
        if not 1 <= limit <= maximum:
            raise ValueError(f"limit deve estar entre 1 e {maximum}")
        order = params.get("order", "desc").lower()
        result = self.list_municipalities({**params, "sort": metric, "order": order, "page": 1, "page_size": limit})
        return {"metric": metric, "order": order, "filters": {key: params[key] for key in ("ano_eleicao", "turno", "ano_renda") if key in params}, **result}

    def income_groups(self, params: dict) -> list[dict]:
        with self.connect() as connection:
            where, values = self.filters(params, connection)
            rows = connection.execute(
                f"""SELECT faixa_renda_predominante grupo, taxa_abstencao_pct, renda_pc_mediana
                FROM mart_municipio_eleicao WHERE {where}
                ORDER BY grupo""",
                values,
            ).fetchall()
            groups: dict[str, list[dict]] = {}
            for row in rows:
                groups.setdefault(row["grupo"], []).append(dict(row))
            return [
                {
                    "grupo": group,
                    "regra_aplicada": "faixa de renda domiciliar per capita com maior percentual de domicilios",
                    "municipios": len(items),
                    "taxa_abstencao_media": statistics.mean(item["taxa_abstencao_pct"] for item in items),
                    "taxa_abstencao_mediana": statistics.median(item["taxa_abstencao_pct"] for item in items),
                    "taxa_abstencao_desvio_padrao": statistics.pstdev(item["taxa_abstencao_pct"] for item in items),
                    "taxa_abstencao_min": min(item["taxa_abstencao_pct"] for item in items),
                    "taxa_abstencao_max": max(item["taxa_abstencao_pct"] for item in items),
                    "renda_pc_mediana_media": statistics.mean(item["renda_pc_mediana"] for item in items),
                }
                for group, items in groups.items()
            ]

    def pipeline_status(self) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM pipeline_run ORDER BY started_at DESC LIMIT 1").fetchone()
            if not row:
                return {"status": "not_run"}
            item = dict(row)
            details = json.loads(item.pop("details_json"))
            item["details"] = {
                key: details[key]
                for key in ("electoral", "income", "crosswalk", "mart", "messages")
                if key in details
            }
            return item

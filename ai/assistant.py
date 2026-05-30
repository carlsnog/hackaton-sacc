from __future__ import annotations

import json
import logging
import re

from app.repositories.analytics import AnalyticsRepository
from pipeline.core import load_json, normalize_name, project_root


logger = logging.getLogger(__name__)


class Assistant:
    def __init__(self, repository: AnalyticsRepository | None = None):
        self.repository = repository or AnalyticsRepository()
        self.config = load_json("config/ai.json")

    def prompt(self, name: str) -> str:
        return (project_root() / self.config["prompts"][name]).read_text(encoding="utf-8").strip()

    def answer(self, question: str) -> dict:
        normalized = normalize_name(question)
        lowered = question.lower()
        if any(term in lowered for term in self.config["guardrails"]["blocked_terms"]):
            logger.info(json.dumps({"event": "assistant_refusal", "reason": "neutrality_guardrail"}))
            return {"kind": "refusal", "answer": self.prompt("refusal")}
        if any(term in lowered for term in ("correlação", "correlacao", "relação", "relacao", "pobreza")):
            summary = self.repository.summary({})
            return {
                "kind": "summary_tool",
                "tool": "GET /api/v1/resumo",
                "data": summary,
                "answer": (
                    f"No recorte de {summary['ano_eleicao']}, turno {summary['turno']}, com renda de "
                    f"{summary['ano_referencia_renda']} e {summary['municipios_validos']} municípios analisados, "
                    "os dados permitem observar padrões territoriais entre renda e ausência eleitoral. "
                    f"{self.prompt('methodology')}"
                ),
            }
        match = re.search(r"\btop\s*(\d+)?", lowered)
        if match or "ranking" in lowered:
            limit = int(match.group(1)) if match and match.group(1) else 10
            metric = "score_vulnerabilidade" if "score" in lowered or "indice" in lowered or "índice" in lowered or "vulnerab" in lowered else "taxa_abstencao_pct"
            ranking = self.repository.ranking({"metric": metric, "limit": limit})
            lines = [f"{index + 1}. {item['municipio']}: {item[metric]:.2f}" for index, item in enumerate(ranking["items"])]
            return {
                "kind": "ranking_tool",
                "tool": "GET /api/v1/rankings",
                "data": ranking,
                "answer": f"Lista ordenada por {metric}, eleição 2022, turno 1, renda 2022:\n" + "\n".join(lines),
            }
        municipalities = self.repository.list_municipalities({"page_size": self.repository.config["api"]["max_page_size"]})["items"]
        for item in municipalities:
            if normalize_name(item["municipio"]) in normalized:
                detail = self.repository.municipality(item["cod_ibge_municipio"], {})
                return {
                    "kind": "municipality_tool",
                    "tool": "GET /api/v1/municipios/{cod_ibge}",
                    "data": detail,
                    "answer": (
                        f"{detail['municipio']}: taxa de abstenção de {detail['taxa_abstencao_pct']:.2f}% "
                        f"na eleição de {detail['ano_eleicao']}, turno {detail['turno']}; renda mediana per capita "
                        f"de R$ {detail['renda_pc_mediana']:.2f} em {detail['ano_referencia_renda']}; "
                        f"índice de atenção {detail['score_vulnerabilidade']:.2f}/100."
                    ),
                }
        return {
            "kind": "help",
            "answer": self.prompt("help"),
        }

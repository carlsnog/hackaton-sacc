from __future__ import annotations

import json
import logging
import re

from ai.llm import create_provider
from app.repositories.analytics import AnalyticsRepository
from pipeline.core import load_json, normalize_name, project_root


logger = logging.getLogger(__name__)


class Assistant:
    def __init__(self, repository: AnalyticsRepository | None = None):
        self.repository = repository or AnalyticsRepository()
        self.config = load_json("config/ai.json")
        self.llm = create_provider(self.config)

    def prompt(self, name: str) -> str:
        return (project_root() / self.config["prompts"][name]).read_text(encoding="utf-8").strip()

    def _enrich(self, result: dict) -> dict:
        if result.get("kind") in ("refusal", "help"):
            result["llm"] = False
            return result
        prompt_key = {
            "municipality_tool": "enrichment_municipality",
            "compare_tool": "enrichment_compare",
        }.get(result["kind"], "enrichment_general")
        system_prompt = self.prompt(prompt_key)
        data = result.get("data", {})
        text = self.llm.enrich(system_prompt, data)
        if text:
            result["answer"] = text
            result["llm"] = True
        else:
            result["llm"] = False
        return result

    def answer(self, question: str) -> dict:
        normalized = normalize_name(question)
        lowered = question.lower()
        if any(term in lowered for term in self.config["guardrails"]["blocked_terms"]):
            logger.info(json.dumps({"event": "assistant_refusal", "reason": "neutrality_guardrail"}))
            return {"kind": "refusal", "answer": self.prompt("refusal")}
        if any(term in lowered for term in ("correlação", "correlacao", "relação", "relacao", "pobreza")):
            summary = self.repository.summary({})
            return self._enrich({
                "kind": "summary_tool",
                "tool": "GET /api/v1/resumo",
                "data": summary,
                "answer": (
                    f"No recorte de {summary['ano_eleicao']}, turno {summary['turno']}, com renda de "
                    f"{summary['ano_referencia_renda']} e {summary['municipios_validos']} municípios analisados, "
                    "a cobertura local ainda é reduzida para destacar uma conclusão estatística sobre a relação entre renda e ausência eleitoral. "
                    f"{self.prompt('methodology')}"
                ),
            })
        match = re.search(r"\btop\s*(\d+)?", lowered)
        if match or "ranking" in lowered:
            limit = int(match.group(1)) if match and match.group(1) else 10
            metric = "score_vulnerabilidade" if "score" in lowered or "indice" in lowered or "índice" in lowered or "vulnerab" in lowered else "taxa_abstencao_pct"
            ranking = self.repository.ranking({"metric": metric, "limit": limit})
            lines = [f"{index + 1}. {item['municipio']}: {item[metric]:.2f}" for index, item in enumerate(ranking["items"])]
            return self._enrich({
                "kind": "ranking_tool",
                "tool": "GET /api/v1/rankings",
                "data": ranking,
                "answer": f"Lista ordenada por {metric}, eleição 2022, turno 1, renda 2022:\n" + "\n".join(lines),
            })
        municipalities = self.repository.list_municipalities({"page_size": 100})["items"]
        if any(term in lowered for term in ("compare", "comparar", "diferença", "diferenca", " vs ", " x ")):
            matched = []
            for item in municipalities:
                if normalize_name(item["municipio"]) in normalized:
                    matched.append(self.repository.municipality(item["cod_ibge_municipio"], {}))
            if len(matched) >= 2:
                return self._enrich({
                    "kind": "compare_tool",
                    "tool": "GET /api/v1/municipios/{cod_ibge} (multi)",
                    "data": matched,
                    "answer": f"Dados de {', '.join(m['municipio'] for m in matched)}.",
                })
        for item in municipalities:
            if normalize_name(item["municipio"]) in normalized:
                detail = self.repository.municipality(item["cod_ibge_municipio"], {})
                return self._enrich({
                    "kind": "municipality_tool",
                    "tool": "GET /api/v1/municipios/{cod_ibge}",
                    "data": detail,
                    "answer": (
                        f"{detail['municipio']}: taxa de abstenção de {detail['taxa_abstencao_pct']:.2f}% "
                        f"na eleição de {detail['ano_eleicao']}, turno {detail['turno']}; renda mediana per capita "
                        f"de R$ {detail['renda_pc_mediana']:.2f} em {detail['ano_referencia_renda']}; "
                        f"índice de atenção {detail['score_vulnerabilidade']:.2f}/100."
                    ),
                })
        return {
            "kind": "help",
            "answer": self.prompt("help"),
        }

import unittest

from ai.assistant import Assistant
from app.repositories.analytics import AnalyticsRepository
from pipeline.run_pipeline import run


class RepositoryAndAssistantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run()
        cls.repository = AnalyticsRepository()
        cls.assistant = Assistant(cls.repository)

    def test_summary_is_weighted_and_traceable(self):
        summary = self.repository.summary({})
        self.assertEqual(summary["municipios_validos"], 223)
        self.assertAlmostEqual(summary["taxa_abstencao_pct"], 17.013058255630266)
        self.assertEqual(summary["eleitores_aptos_paraiba"], 3225826)
        self.assertEqual(summary["abrangencia_eleitores_paraiba_pct"], 100)
        self.assertEqual(summary["abrangencia_territorial_pct"], 100)
        self.assertEqual(len(summary["sources"]), 2)

    def test_detail_exposes_score_components_and_faixas(self):
        detail = self.repository.municipality("2507507", {})
        self.assertEqual(detail["municipio"], "JOÃO PESSOA")
        self.assertIn("percentil_abstencao", detail["score_components"])
        self.assertIn("Até 1/4 de salário mínimo", detail["faixas_renda_pct"])
        self.assertEqual(len(detail["sources"]), 2)

    def test_income_groups_expose_rule_median_and_dispersion(self):
        groups = self.repository.income_groups({})
        self.assertGreater(len(groups), 0)
        self.assertIn("regra_aplicada", groups[0])
        self.assertIn("taxa_abstencao_mediana", groups[0])
        self.assertIn("taxa_abstencao_desvio_padrao", groups[0])

    def test_export_is_not_paginated(self):
        self.assertEqual(len(self.repository.export_municipalities({})), 223)

    def test_status_keeps_healthcheck_compact(self):
        status = self.repository.pipeline_status()
        self.assertEqual(status["status"], "success")
        self.assertNotIn("unmatched_municipalities", status["details"])

    def test_assistant_uses_tools_and_editable_prompts(self):
        ranking = self.assistant.answer("top 3 por score")
        self.assertEqual(ranking["kind"], "ranking_tool")
        self.assertEqual(len(ranking["data"]["items"]), 3)
        correlation = self.assistant.answer("qual a relação entre pobreza e abstenção?")
        self.assertEqual(correlation["kind"], "summary_tool")
        self.assertIn(self.assistant.prompt("methodology"), correlation["answer"])
        self.assertNotIn("Pearson", correlation["answer"])
        refusal = self.assistant.answer("quero persuadir eleitor")
        self.assertEqual(refusal, {"kind": "refusal", "answer": self.assistant.prompt("refusal")})

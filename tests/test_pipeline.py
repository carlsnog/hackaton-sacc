import json
import sqlite3
import unittest

from pipeline.core import load_json, project_root
from pipeline.run_pipeline import run


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = run()
        cls.config = load_json("config/settings.json")
        cls.connection = sqlite3.connect(project_root() / cls.config["database_path"])

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def count(self, table):
        return self.connection.execute(f"SELECT COUNT(*) FROM {table} WHERE snapshot_id = ?", (self.snapshot,)).fetchone()[0]

    def test_preserves_complete_electoral_universe(self):
        self.assertEqual(self.count("fact_abstencao_municipio"), 223)

    def test_builds_complete_local_mart(self):
        self.assertEqual(self.count("mart_municipio_eleicao"), 223)

    def test_score_weights_sum_to_one(self):
        weights = self.config["score"]["weights"]
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_reconciles_all_electoral_rows(self):
        errors = self.connection.execute(
            "SELECT COUNT(*) FROM fact_abstencao_municipio WHERE snapshot_id = ? AND total_aptos != total_comparecimento + total_abstencoes",
            (self.snapshot,),
        ).fetchone()[0]
        self.assertEqual(errors, 0)

    def test_report_records_percentage_validation_and_structured_warnings(self):
        report = json.loads((project_root() / self.config["report_directory"] / f"{self.snapshot}.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(report["income"]["faixa_percentage_sum_min"], 99.9)
        self.assertLessEqual(report["income"]["faixa_percentage_sum_max"], 100.1)
        codes = {message["code"] for message in report["messages"]}
        self.assertNotIn("SOCIOECONOMIC_PARTIAL_COVERAGE", codes)
        self.assertIn("CROSSWALK_IBGE_CODE", codes)

    def test_rag_document_contains_traceable_structured_context(self):
        document = json.loads((project_root() / self.config["rag_directory"] / self.snapshot / "2507507.json").read_text(encoding="utf-8"))
        self.assertEqual(document["metadata"]["cod_ibge_municipio"], "2507507")
        self.assertIn("faixas_renda_pct", document["data"])
        self.assertIn("delta_abstencao_vs_recorte_pct", document["data"])
        self.assertIn("pib_mil_reais", document["data"])
        self.assertIn("escolaridade", document["data"])
        self.assertEqual(len(document["sources"]), 2)

    def test_mart_includes_gdp_sex_and_schooling_context(self):
        row = self.connection.execute(
            "SELECT pib_mil_reais, sexo_feminino, sexo_masculino, escolaridade_json, escolaridade_predominante FROM mart_municipio_eleicao WHERE snapshot_id = ? LIMIT 1",
            (self.snapshot,),
        ).fetchone()
        self.assertGreater(row[0], 0)
        self.assertGreater(row[1], 0)
        self.assertGreater(row[2], 0)
        self.assertIn("ANALFABETO", json.loads(row[3]))
        self.assertTrue(row[4])

    def test_repeated_run_is_idempotent_for_snapshot_facts(self):
        self.assertEqual(run(), self.snapshot)
        self.assertEqual(self.count("fact_abstencao_municipio"), 223)
        self.assertEqual(self.count("mart_municipio_eleicao"), 223)

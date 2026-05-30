import unittest

from pipeline.ingest_sidra import classification, normalize_sidra_value


class SidraIngestTest(unittest.TestCase):
    def test_normalizes_absolute_zero_marker(self):
        self.assertEqual(normalize_sidra_value("-"), "0")
        self.assertEqual(normalize_sidra_value("12.30"), "12.30")

    def test_reduces_range_classification_to_public_category(self):
        result = {
            "classificacoes": [
                {"id": "2", "nome": "Sexo", "categoria": {"6794": "Total"}},
                {"id": "86", "nome": "Cor ou raça", "categoria": {"95251": "Total"}},
                {"id": "386", "nome": "Classes de rendimento nominal mensal domiciliar per capita", "categoria": {"9681": "Até 1/4 de salário mínimo"}},
            ]
        }
        self.assertEqual(
            classification(result, "386"),
            ("Classes de rendimento nominal mensal domiciliar per capita", "Até 1/4 de salário mínimo"),
        )

import unittest

from pipeline.core import project_root


class FrontendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (project_root() / "frontend" / "index.html").read_text(encoding="utf-8")
        cls.js = (project_root() / "frontend" / "app.js").read_text(encoding="utf-8")

    def test_uses_public_facing_brand_and_removes_admin_status(self):
        self.assertIn("Vozes Ausentes PB", self.html)
        self.assertNotIn("Status da última carga", self.html)
        self.assertNotIn('"Pearson"', self.js)

    def test_ranking_headers_are_sortable(self):
        self.assertIn('data-sort="municipio"', self.html)
        self.assertIn('data-sort="taxa_abstencao_pct"', self.html)
        self.assertIn('data-sort="renda_pc_mediana"', self.html)
        self.assertIn('data-sort="score_vulnerabilidade"', self.html)

    def test_scatter_starts_y_axis_at_zero_and_map_has_local_fallback(self):
        self.assertIn("index * 5", self.js)
        self.assertIn('fetch("/api/v1/geojson")', self.js)
        self.assertIn("O mapa de calor será exibido", self.js)


import unittest

from pipeline.core import project_root


class FrontendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (project_root() / "frontend" / "index.html").read_text(encoding="utf-8")
        cls.js = (project_root() / "frontend" / "app.js").read_text(encoding="utf-8")
        cls.main = (project_root() / "app" / "main.py").read_text(encoding="utf-8")

    def test_uses_public_facing_brand_and_removes_admin_status(self):
        self.assertIn("Vozes Ausentes PB", self.html)
        self.assertNotIn("Status da última carga", self.html)
        self.assertNotIn('"Pearson"', self.js)
        self.assertIn("abrangencia_eleitores_paraiba_pct", self.js)
        self.assertIn("eleitores_aptos_paraiba", self.js)

    def test_ranking_headers_are_sortable(self):
        self.assertIn('data-sort="municipio"', self.html)
        self.assertIn('data-sort="taxa_abstencao_pct"', self.html)
        self.assertIn('data-sort="renda_pc_mediana"', self.html)
        self.assertIn('data-sort="score_vulnerabilidade"', self.html)

    def test_explains_relationship_between_public_indicators(self):
        self.assertIn("O que os números mostram em conjunto?", self.html)
        self.assertIn("Eleitores ausentes", self.html)
        self.assertIn("renda mediana por pessoa", self.html)
        self.assertIn("índice de atenção", self.html)
        self.assertIn("quanto menor a renda relativa do município, maior tende a ser a contribuição da renda para o índice", self.html)
        self.assertIn("não significa que a renda seja a causa da abstenção", self.html)

    def test_scatter_starts_y_axis_at_zero_and_map_has_local_fallback(self):
        self.assertIn("index * 5", self.js)
        self.assertIn("const minX = 550", self.js)
        self.assertIn('fetch("/api/v1/geojson")', self.js)
        self.assertIn("O mapa de calor será exibido", self.js)

    def test_heat_map_uses_complete_municipality_polygons(self):
        self.assertNotIn('geometry.type === "Point"', self.js)
        self.assertIn('data" / "geo" / "geojs-25-mun.json"', self.main)
        self.assertNotIn('map-background', self.js)

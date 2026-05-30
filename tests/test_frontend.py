import unittest

from pipeline.core import project_root


class FrontendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (project_root() / "frontend" / "index.html").read_text(encoding="utf-8")
        cls.js = (project_root() / "frontend" / "app.js").read_text(encoding="utf-8")
        cls.css = (project_root() / "frontend" / "styles.css").read_text(encoding="utf-8")
        cls.main = (project_root() / "app" / "main.py").read_text(encoding="utf-8")

    def test_uses_public_facing_brand_and_removes_admin_status(self):
        self.assertIn("Vozes Ausentes PB", self.html)
        self.assertNotIn("Status da última carga", self.html)
        self.assertNotIn('"Pearson"', self.js)
        self.assertIn("abrangencia_eleitores_paraiba_pct", self.js)
        self.assertIn("abrangencia_territorial_pct", self.js)
        self.assertIn("eleitores_aptos_paraiba", self.js)

    def test_ranking_headers_are_sortable(self):
        self.assertIn('data-sort="municipio"', self.html)
        self.assertIn('data-sort="total_aptos"', self.html)
        self.assertIn('data-sort="pib_mil_reais"', self.html)
        self.assertIn('data-sort="sexo_feminino"', self.html)
        self.assertIn('data-sort="sexo_masculino"', self.html)
        self.assertIn('data-sort="escolaridade_predominante"', self.html)
        self.assertIn("Aptos registrados no recorte", self.html)
        self.assertIn("não representa uma contagem de pessoas únicas", self.html)
        self.assertIn('data-sort="taxa_abstencao_pct"', self.html)
        self.assertIn('data-sort="renda_pc_mediana"', self.html)
        self.assertIn('data-sort="score_vulnerabilidade"', self.html)

    def test_ranking_is_contained_in_scrollable_box(self):
        self.assertIn('class="municipality-table-scroll"', self.html)
        self.assertIn("max-height:480px", self.css)
        self.assertIn("overflow:auto", self.css)
        self.assertIn("position:sticky", self.css)

    def test_uses_requested_palette_without_background_image(self):
        for color in ("#c95a2c", "#4d382c", "#d7d9d3"):
            self.assertIn(color, self.css + self.js)
        self.assertNotIn("background:url", self.css)
        self.assertNotIn("paraiba-ilustracao.svg", self.css)
        self.assertNotIn("Como interpretar os indicadores", self.html)

    def test_heat_map_uses_sequential_red_scale(self):
        self.assertIn('["#fbe2d8", "#edb29b", "#c95a2c", "#782f1a"]', self.js)
        self.assertIn("linear-gradient(90deg,#fbe2d8,#edb29b,#c95a2c,#782f1a)", self.css)

    def test_scatter_starts_y_axis_at_zero_and_map_has_local_fallback(self):
        self.assertIn("index * 5", self.js)
        self.assertIn("Math.floor(Math.min(...valid.map(item => item.renda_pc_mediana)) / 100) * 100", self.js)
        self.assertIn('fetch("/api/v1/geojson")', self.js)
        self.assertIn("O mapa de calor será exibido", self.js)

    def test_electoral_scatter_compares_gdp_and_abstention_rate(self):
        self.assertIn('id="electoral-scatter"', self.html)
        self.assertIn("renderElectoralScatter(municipalities)", self.js)
        self.assertIn("PIB municipal em R$ mil", self.js)
        self.assertIn("Eleitores ausentes (%)", self.js)
        self.assertIn("item.pib_mil_reais", self.js)
        self.assertIn("item.taxa_abstencao_pct", self.js)
        self.assertIn("Math.log10", self.js)
        self.assertIn("escala log", self.html)

    def test_attributes_local_sources_accurately(self):
        self.assertIn("TSE para os dados eleitorais de 2022", self.html)
        self.assertIn("IBGE para os indicadores municipais", self.html)
        self.assertIn("indicadores censitários de renda usam referência de 2022", self.html)

    def test_heat_map_uses_complete_municipality_polygons(self):
        self.assertNotIn('geometry.type === "Point"', self.js)
        self.assertIn('data" / "geo" / "geojs-25-mun.json"', self.main)
        self.assertNotIn('map-background', self.js)

    def test_removes_socioeconomic_reading_panel(self):
        self.assertNotIn("Leitura socioeconômica", self.html)
        self.assertNotIn('id="income-groups"', self.html)
        self.assertNotIn('fetch("/api/v1/grupos-renda")', self.js)

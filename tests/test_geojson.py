import json
import unittest

from app.repositories.analytics import AnalyticsRepository
from pipeline.core import project_root
from pipeline.run_pipeline import run


class GeoJsonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run()
        cls.data = json.loads((project_root() / "data" / "geo" / "geojs-25-mun.json").read_text(encoding="utf-8-sig"))
        cls.features = cls.data["features"]

    def test_has_complete_pb_municipality_universe(self):
        self.assertEqual(self.data["type"], "FeatureCollection")
        self.assertEqual(len(self.features), 223)
        codes = [feature["properties"]["id"] for feature in self.features]
        self.assertEqual(len(set(codes)), 223)

    def test_uses_supported_polygon_geometries(self):
        self.assertTrue(all(feature["geometry"]["type"] in {"Polygon", "MultiPolygon"} for feature in self.features))

    def test_covers_all_published_mart_codes(self):
        geo_codes = {feature["properties"]["id"] for feature in self.features}
        mart_codes = {item["cod_ibge_municipio"] for item in AnalyticsRepository().export_municipalities({})}
        self.assertEqual(mart_codes - geo_codes, set())


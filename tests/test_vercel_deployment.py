import json
import unittest

from app.repositories.analytics import AnalyticsRepository
from pipeline.core import project_root


class VercelDeploymentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = project_root()
        cls.config = json.loads((cls.root / "vercel.json").read_text(encoding="utf-8"))

    def test_routes_all_requests_to_python_handler(self):
        self.assertEqual(self.config["rewrites"], [{"source": "/:path*", "destination": "/api/index"}])
        self.assertIn("data/deploy/**", self.config["functions"]["api/index.py"]["includeFiles"])

    def test_serverless_handler_reuses_local_application(self):
        source = (self.root / "api" / "index.py").read_text(encoding="utf-8")
        self.assertIn("from app.main import Handler", source)
        self.assertIn("handler = Handler", source)

    def test_repository_falls_back_to_deployment_snapshot(self):
        config = json.loads((self.root / "config" / "settings.json").read_text(encoding="utf-8"))
        config["database_path"] = "data/curated/arquivo-ausente.sqlite3"
        repository = AnalyticsRepository(config)
        self.assertEqual(repository.db_path, self.root / "data" / "deploy" / "vozes_ausentes_pb.sqlite3")
        self.assertEqual(repository.summary({})["municipios_validos"], 223)

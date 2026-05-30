from __future__ import annotations

import csv
import io
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ai.assistant import Assistant
from app.repositories.analytics import AnalyticsRepository
from pipeline.core import load_json, project_root


repository = AnalyticsRepository()
assistant = Assistant(repository)


def params_from(query: str) -> dict:
    return {key: values[-1] for key, values in parse_qs(query).items()}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = params_from(parsed.query)
        try:
            if parsed.path == "/health":
                return self.send_json({"api": "ok", "database": "ok", "pipeline": repository.pipeline_status()})
            if parsed.path == "/api/v1/resumo":
                return self.send_json(repository.summary(params))
            if parsed.path == "/api/v1/municipios":
                return self.send_json(repository.list_municipalities(params))
            if parsed.path.startswith("/api/v1/municipios/"):
                item = repository.municipality(parsed.path.rsplit("/", 1)[-1], params)
                return self.send_json(item, 200) if item else self.send_json({"error": "Municipio nao encontrado no mart local"}, 404)
            if parsed.path == "/api/v1/rankings":
                return self.send_json(repository.ranking(params))
            if parsed.path == "/api/v1/grupos-renda":
                return self.send_json(repository.income_groups(params))
            if parsed.path == "/api/v1/grupos-renda.csv":
                return self.send_groups_export(params)
            if parsed.path == "/api/v1/export.csv":
                return self.send_export(params)
            if parsed.path == "/api/v1/status":
                return self.send_json(repository.pipeline_status())
            if parsed.path == "/api/v1/geojson":
                return self.send_geojson()
            return self.send_static(parsed.path)
        except ValueError as error:
            return self.send_json({"error": str(error)}, 422)
        except RuntimeError as error:
            return self.send_json({"error": str(error)}, 503)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/v1/assistant":
            return self.send_json({"error": "Rota nao encontrada"}, 404)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(size) or b"{}")
            question = str(data.get("question", "")).strip()
            if not question:
                raise ValueError("question e obrigatoria")
            return self.send_json(assistant.answer(question))
        except (ValueError, json.JSONDecodeError) as error:
            return self.send_json({"error": str(error)}, 422)

    def send_export(self, params):
        items = repository.export_municipalities(params)
        output = io.StringIO()
        fields = ["snapshot_id", "cod_ibge_municipio", "cod_tse_municipio", "municipio", "ano_eleicao", "turno", "ano_referencia_renda", "taxa_abstencao_pct", "renda_pc_media", "renda_pc_mediana", "pct_baixa_renda", "score_vulnerabilidade"]
        writer = csv.DictWriter(output, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)
        body = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="vozes_ausentes_pb.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_groups_export(self, params):
        items = repository.income_groups(params)
        output = io.StringIO()
        fields = ["grupo", "regra_aplicada", "municipios", "taxa_abstencao_media", "taxa_abstencao_mediana", "taxa_abstencao_desvio_padrao", "taxa_abstencao_min", "taxa_abstencao_max", "renda_pc_mediana_media"]
        writer = csv.DictWriter(output, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)
        body = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="grupos_renda_abstencionismo.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_geojson(self):
        target = project_root() / "data" / "geo" / "geojs-25-mun.json"
        if not target.is_file():
            return self.send_json({"error": "Malha municipal local indisponivel"}, 404)
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/geo+json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, request_path):
        relative = "index.html" if request_path == "/" else request_path.lstrip("/")
        target = (project_root() / "frontend" / relative).resolve()
        static_root = (project_root() / "frontend").resolve()
        if static_root not in target.parents and target != static_root:
            return self.send_json({"error": "Caminho invalido"}, 404)
        if not target.is_file():
            return self.send_json({"error": "Rota nao encontrada"}, 404)
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    config = load_json("config/settings.json")["api"]
    server = ThreadingHTTPServer((config["host"], config["port"]), Handler)
    print(f"Vozes Ausentes PB em http://{config['host']}:{config['port']}")
    server.serve_forever()


if __name__ == "__main__":
    run()

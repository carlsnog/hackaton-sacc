from __future__ import annotations

import sqlite3

from pipeline.core import load_json, project_root


def publish_snapshot() -> str:
    root = project_root()
    source = root / load_json("config/settings.json")["database_path"]
    target = root / "data" / "deploy" / "vozes_ausentes_pb.sqlite3"
    if not source.is_file():
        raise RuntimeError("Banco local ausente. Execute o pipeline antes de gerar o snapshot de deploy.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
        source_connection.backup(target_connection)
        snapshot_id = source_connection.execute(
            "SELECT snapshot_id FROM pipeline_run WHERE status = 'success' ORDER BY finished_at DESC LIMIT 1"
        ).fetchone()
    if not snapshot_id:
        raise RuntimeError("Nenhum snapshot publicado no banco local.")
    return snapshot_id[0]


if __name__ == "__main__":
    print(publish_snapshot())

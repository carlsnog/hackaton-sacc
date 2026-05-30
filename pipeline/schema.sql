PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pipeline_run (
  run_id TEXT PRIMARY KEY,
  snapshot_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  details_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_manifest (
  snapshot_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  row_count INTEGER NOT NULL,
  PRIMARY KEY (snapshot_id, source_name)
);

CREATE TABLE IF NOT EXISTS dim_municipio (
  snapshot_id TEXT NOT NULL,
  cod_tse_municipio TEXT NOT NULL,
  cod_ibge_municipio TEXT,
  municipio TEXT NOT NULL,
  municipio_normalizado TEXT NOT NULL,
  uf TEXT NOT NULL,
  ativo INTEGER NOT NULL,
  metodo_correspondencia TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, cod_tse_municipio)
);

CREATE TABLE IF NOT EXISTS fact_abstencao_municipio (
  snapshot_id TEXT NOT NULL,
  ano_eleicao INTEGER NOT NULL,
  cod_eleicao TEXT NOT NULL,
  descricao_eleicao TEXT NOT NULL,
  turno INTEGER NOT NULL,
  cod_tse_municipio TEXT NOT NULL,
  total_aptos INTEGER NOT NULL,
  total_comparecimento INTEGER NOT NULL,
  total_abstencoes INTEGER NOT NULL,
  votos_brancos INTEGER NOT NULL,
  votos_nulos INTEGER NOT NULL,
  taxa_abstencao_pct REAL NOT NULL,
  PRIMARY KEY (snapshot_id, ano_eleicao, turno, cod_tse_municipio)
);

CREATE TABLE IF NOT EXISTS fact_renda_municipio (
  snapshot_id TEXT NOT NULL,
  cod_ibge_municipio TEXT NOT NULL,
  municipio TEXT NOT NULL,
  ano_referencia_renda INTEGER NOT NULL,
  ano_referencia_faixas INTEGER NOT NULL,
  renda_pc_media REAL,
  renda_pc_mediana REAL,
  faixas_json TEXT NOT NULL,
  pct_baixa_renda REAL,
  faixa_renda_predominante TEXT,
  faixa_renda_predominante_pct REAL,
  PRIMARY KEY (snapshot_id, cod_ibge_municipio, ano_referencia_renda)
);

CREATE TABLE IF NOT EXISTS mart_municipio_eleicao (
  snapshot_id TEXT NOT NULL,
  cod_ibge_municipio TEXT NOT NULL,
  cod_tse_municipio TEXT NOT NULL,
  municipio TEXT NOT NULL,
  ano_eleicao INTEGER NOT NULL,
  cod_eleicao TEXT NOT NULL,
  descricao_eleicao TEXT NOT NULL,
  turno INTEGER NOT NULL,
  ano_referencia_renda INTEGER NOT NULL,
  ano_referencia_faixas INTEGER NOT NULL,
  total_aptos INTEGER NOT NULL,
  total_comparecimento INTEGER NOT NULL,
  total_abstencoes INTEGER NOT NULL,
  votos_brancos INTEGER NOT NULL,
  votos_nulos INTEGER NOT NULL,
  taxa_abstencao_pct REAL NOT NULL,
  renda_pc_media REAL,
  renda_pc_mediana REAL,
  faixas_json TEXT NOT NULL,
  pct_baixa_renda REAL,
  faixa_renda_predominante TEXT,
  faixa_renda_predominante_pct REAL,
  percentil_abstencao REAL NOT NULL,
  percentil_renda_baixa REAL NOT NULL,
  percentil_baixa_renda REAL NOT NULL,
  score_vulnerabilidade REAL NOT NULL,
  score_version TEXT NOT NULL,
  score_weights_json TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, cod_ibge_municipio, ano_eleicao, turno, ano_referencia_renda)
);

CREATE INDEX IF NOT EXISTS idx_mart_filter
ON mart_municipio_eleicao(snapshot_id, ano_eleicao, turno, ano_referencia_renda);

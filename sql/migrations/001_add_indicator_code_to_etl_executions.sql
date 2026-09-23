BEGIN;

ALTER TABLE execucoes_etl
ADD COLUMN IF NOT EXISTS codigo_indicador INTEGER;

CREATE INDEX IF NOT EXISTS idx_execucoes_etl_codigo_indicador
ON execucoes_etl (codigo_indicador);

COMMIT;
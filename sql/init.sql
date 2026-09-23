CREATE TABLE IF NOT EXISTS indicadores (
    codigo INTEGER PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    unidade VARCHAR(50) NOT NULL,
    periodicidade VARCHAR(20) NOT NULL,
    fonte VARCHAR(100) NOT NULL DEFAULT 'Banco Central do Brasil'
);

CREATE TABLE IF NOT EXISTS valores_indicadores (
    codigo_indicador INTEGER NOT NULL,
    data_referencia DATE NOT NULL,
    valor NUMERIC(18, 6) NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (codigo_indicador, data_referencia),

    CONSTRAINT fk_valores_indicadores_indicador
        FOREIGN KEY (codigo_indicador)
        REFERENCES indicadores (codigo)
);

CREATE TABLE IF NOT EXISTS execucoes_etl (
    id BIGSERIAL PRIMARY KEY,
    codigo_indicador INTEGER NOT NULL,
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_em TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    registros_extraidos INTEGER NOT NULL DEFAULT 0,
    registros_carregados INTEGER NOT NULL DEFAULT 0,
    mensagem_erro TEXT,

    CONSTRAINT ck_execucoes_etl_status
        CHECK (status IN ('em_execucao', 'sucesso', 'falha'))
);

CREATE INDEX IF NOT EXISTS idx_execucoes_etl_codigo_indicador
ON execucoes_etl (codigo_indicador);
-- ============================================================================
-- Migracao inicial do SGT/CNJ - script para psql
-- Execute conectado ao banco postgres como superuser.
--
-- Exemplo no PowerShell, apos carregar DB_PASSWORD do .env:
-- psql -U postgres -d postgres --set=DB_PASSWORD="$env:DB_PASSWORD" -f .\V00000001__DDL_TABELAS_SOAPWSDL_SGT.sql
-- ============================================================================

\if :{?DB_PASSWORD}
\else
\echo 'Erro: informe DB_PASSWORD com --set=DB_PASSWORD ou via variavel do psql.'
\quit
\endif

-- A role e criada uma vez e a senha e sincronizada com o ambiente a cada execucao.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sgt_user') THEN
        CREATE ROLE sgt_user LOGIN;
    END IF;
END
$$;

ALTER ROLE sgt_user WITH LOGIN PASSWORD :'DB_PASSWORD';

SELECT
$$
CREATE DATABASE cnj_sgt_db
OWNER sgt_user
ENCODING 'UTF8'
$$
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'cnj_sgt_db'
)
\gexec

COMMENT ON DATABASE cnj_sgt_db IS 'Banco de dados para sincronizacao do SGT/CNJ via Webservice SOAP';

\connect cnj_sgt_db

-- Schema e permissoes da aplicacao.
CREATE SCHEMA IF NOT EXISTS sgt_cnj;
ALTER SCHEMA sgt_cnj OWNER TO sgt_user;
GRANT USAGE, CREATE ON SCHEMA sgt_cnj TO sgt_user;

SET search_path TO sgt_cnj, public;

-- Tabela de Classes Processuais.
CREATE TABLE IF NOT EXISTS sgt_cnj.classe (
    cod_classe INT PRIMARY KEY,
    cod_classe_pai INT REFERENCES sgt_cnj.classe(cod_classe),
    nome VARCHAR(255) NOT NULL,
    sigla VARCHAR(50),
    descricao TEXT,
    glossario TEXT,
    tipo_situacao CHAR(1) DEFAULT 'A',
    dt_publicacao TIMESTAMP,
    dt_alteracao TIMESTAMP,
    dt_inativacao TIMESTAMP,
    dados_adicionais JSONB
);
ALTER TABLE sgt_cnj.classe ADD COLUMN IF NOT EXISTS dt_inativacao TIMESTAMP;

-- Tabela de Assuntos Processuais.
CREATE TABLE IF NOT EXISTS sgt_cnj.assunto (
    cod_assunto INT PRIMARY KEY,
    cod_assunto_pai INT REFERENCES sgt_cnj.assunto(cod_assunto),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    glossario TEXT,
    dispositivo_legal TEXT,
    artigo VARCHAR(100),
    tipo_situacao CHAR(1) DEFAULT 'A',
    dt_publicacao TIMESTAMP,
    dt_alteracao TIMESTAMP,
    dt_inativacao TIMESTAMP,
    dados_adicionais JSONB
);
ALTER TABLE sgt_cnj.assunto ADD COLUMN IF NOT EXISTS dt_inativacao TIMESTAMP;

-- Tabela de Movimentos Processuais.
CREATE TABLE IF NOT EXISTS sgt_cnj.movimento (
    cod_movimento INT PRIMARY KEY,
    cod_movimento_pai INT REFERENCES sgt_cnj.movimento(cod_movimento),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    glossario TEXT,
    tipo_situacao CHAR(1) DEFAULT 'A',
    dt_publicacao TIMESTAMP,
    dt_alteracao TIMESTAMP,
    dt_inativacao TIMESTAMP,
    dados_adicionais JSONB
);
ALTER TABLE sgt_cnj.movimento ADD COLUMN IF NOT EXISTS dt_inativacao TIMESTAMP;

-- Relacionamento N:N entre Classes e Assuntos.
CREATE TABLE IF NOT EXISTS sgt_cnj.classe_assunto (
    cod_classe INT REFERENCES sgt_cnj.classe(cod_classe) ON DELETE CASCADE,
    cod_assunto INT REFERENCES sgt_cnj.assunto(cod_assunto) ON DELETE CASCADE,
    PRIMARY KEY (cod_classe, cod_assunto)
);

-- Tabela de log de carga/sincronizacao SOAP.
CREATE TABLE IF NOT EXISTS sgt_cnj.log_sincronizacao (
    id SERIAL PRIMARY KEY,
    tipo_tabela VARCHAR(50) NOT NULL,
    data_execucao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    registros_processados INT DEFAULT 0,
    mensagem_erro TEXT
);

-- Indices idempotentes.
CREATE INDEX IF NOT EXISTS idx_classe_pai
    ON sgt_cnj.classe(cod_classe_pai);
CREATE INDEX IF NOT EXISTS idx_assunto_pai
    ON sgt_cnj.assunto(cod_assunto_pai);
CREATE INDEX IF NOT EXISTS idx_movimento_pai
    ON sgt_cnj.movimento(cod_movimento_pai);
CREATE INDEX IF NOT EXISTS idx_classe_jsonb
    ON sgt_cnj.classe USING GIN (dados_adicionais);
CREATE INDEX IF NOT EXISTS idx_assunto_jsonb
    ON sgt_cnj.assunto USING GIN (dados_adicionais);
CREATE INDEX IF NOT EXISTS idx_movimento_jsonb
    ON sgt_cnj.movimento USING GIN (dados_adicionais);

-- Permissoes repetiveis para objetos ja existentes e futuros.
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sgt_cnj TO sgt_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA sgt_cnj TO sgt_user;
ALTER DEFAULT PRIVILEGES FOR ROLE sgt_user IN SCHEMA sgt_cnj
    GRANT ALL PRIVILEGES ON TABLES TO sgt_user;
ALTER DEFAULT PRIVILEGES FOR ROLE sgt_user IN SCHEMA sgt_cnj
    GRANT ALL PRIVILEGES ON SEQUENCES TO sgt_user;
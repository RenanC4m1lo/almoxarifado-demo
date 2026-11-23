-- ============================================================
-- schema.sql - Versão de demonstração (PostgreSQL / Render)
-- Adaptado do schema original em MySQL. Simplificações feitas
-- de propósito pra esta cópia de demo (não afetam o sistema
-- real em produção, que continua em MySQL):
--   - enum(...) virou VARCHAR (a validação já é feita no backend)
--   - tinyint(1) virou SMALLINT (0/1)
--   - "ON UPDATE CURRENT_TIMESTAMP" foi removido (cosmético)
-- ============================================================

DROP TABLE IF EXISTS alertas;
DROP TABLE IF EXISTS movimentacoes;
DROP TABLE IF EXISTS unidades;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS tecnicos;
DROP TABLE IF EXISTS equipamentos;
DROP TABLE IF EXISTS fornecedores;
DROP TABLE IF EXISTS empresas;

CREATE TABLE empresas (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(100) NOT NULL,
    cidade     VARCHAR(100),
    ativo      SMALLINT NOT NULL DEFAULT 1,
    criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fornecedores (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(150) NOT NULL,
    cnpj       VARCHAR(18) UNIQUE,
    contato    VARCHAR(100),
    telefone   VARCHAR(20),
    email      VARCHAR(100),
    ativo      SMALLINT NOT NULL DEFAULT 1,
    id_empresa INT NOT NULL DEFAULT 1,
    criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipamentos (
    id                SERIAL PRIMARY KEY,
    nome              VARCHAR(150) NOT NULL,
    descricao         TEXT,
    numero_patrimonio VARCHAR(50),
    codigo_barras     VARCHAR(100) UNIQUE,
    quantidade        INT NOT NULL DEFAULT 0,
    quantidade_minima INT NOT NULL DEFAULT 5,
    status            VARCHAR(20) NOT NULL DEFAULT 'disponivel',
    categoria         VARCHAR(100),
    localizacao       VARCHAR(100),
    id_fornecedor     INT REFERENCES fornecedores(id) ON DELETE SET NULL,
    id_empresa        INT NOT NULL DEFAULT 1,
    criado_em         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_equipamentos_fornecedor ON equipamentos(id_fornecedor);

CREATE TABLE tecnicos (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(100) NOT NULL,
    telefone   VARCHAR(20),
    ativo      SMALLINT NOT NULL DEFAULT 1,
    id_empresa INT NOT NULL DEFAULT 1,
    criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE usuarios (
    id           SERIAL PRIMARY KEY,
    nome         VARCHAR(100) NOT NULL,
    email        VARCHAR(100) NOT NULL UNIQUE,
    senha        VARCHAR(255) NOT NULL,
    perfil       VARCHAR(20) NOT NULL DEFAULT 'visitante',
    id_empresa   INT,
    acesso_todas SMALLINT DEFAULT 0,
    ativo        SMALLINT NOT NULL DEFAULT 1,
    criado_em    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE unidades (
    id                SERIAL PRIMARY KEY,
    id_equipamento    INT NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    id_empresa        INT NOT NULL DEFAULT 1,
    codigo_barras     VARCHAR(100) NOT NULL UNIQUE,
    numero_serie      VARCHAR(100),
    status            VARCHAR(20) NOT NULL DEFAULT 'disponivel',
    responsavel_atual VARCHAR(100),
    observacao        TEXT,
    criado_em         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_unidades_equipamento ON unidades(id_equipamento);

CREATE TABLE movimentacoes (
    id                      SERIAL PRIMARY KEY,
    tipo                    VARCHAR(20) NOT NULL,
    quantidade              INT NOT NULL DEFAULT 1,
    observacao              TEXT,
    condicao                VARCHAR(20),
    responsavel             VARCHAR(100) NOT NULL,
    data_devolucao_prevista DATE,
    data_devolucao_real     TIMESTAMP,
    id_equipamento          INT NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    id_usuario              INT REFERENCES usuarios(id) ON DELETE SET NULL,
    id_empresa              INT NOT NULL DEFAULT 1,
    criado_em               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_movimentacoes_equipamento ON movimentacoes(id_equipamento);
CREATE INDEX idx_movimentacoes_usuario ON movimentacoes(id_usuario);

CREATE TABLE alertas (
    id             SERIAL PRIMARY KEY,
    mensagem       VARCHAR(255) NOT NULL,
    tipo           VARCHAR(20) NOT NULL DEFAULT 'estoque_baixo',
    lido           SMALLINT NOT NULL DEFAULT 0,
    id_equipamento INT NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    id_empresa     INT NOT NULL DEFAULT 1,
    criado_em      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_alertas_equipamento ON alertas(id_equipamento);

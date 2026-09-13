# Arquitetura de Pastas e Componentes — Projeto SGT-CNJ

## Contexto do Projeto

O **SGT-CNJ** é um microserviço em Python desenvolvido com a arquitetura **FastAPI** para realizar a ingestão, sincronização e disponibilização de dados das **Tabelas Processuais Unificadas (TPU)** do Conselho Nacional de Justiça (CNJ).

O sistema atua como uma camada intermediária (middleware): ele consome o webservice SOAP/WSDL oficial do SGT (`sgt_ws.php?wsdl`), realiza a sanitização de tags/erros HTML no payload XML, persiste e atualiza as estruturas hierárquicas (Classes, Assuntos e Movimentos Processuais) em um banco de dados **PostgreSQL**, e disponibiliza estes dados através de endpoints **API REST** de alta performance.

---

## Estrutura do Projeto

```text
SGT-CNJ/
├── app/
│   ├── config.py                 # Configurações globais e leitura do arquivo .env
│   ├── database.py               # Conexão, gerenciamento de pool e verificação de saúde do PostgreSQL
│   ├── models/
│   │   └── schemas.py            # Schemas Pydantic para validação de entrada/saída e serialização JSON
│   ├── services/
│   │   ├── soap_client.py        # Cliente Zeep, conexão WSDL, sanitização de HTML e extratores
│   │   └── sgt_service.py       # Regras de negócio (sincronização SOAP, ordenação hierárquica e busca no DB)
│   └── controllers/
│       └── itens_controller.py   # Classe Controller contendo os endpoints da API REST
├── main.py                       # Ponto de entrada (Inicialização do FastAPI, Uvicorn e comandos CLI)
└── db/
    └── migration/                # Scripts DDL de criação do banco, esquemas e versionamento de tabelas

```

---

## Descrição dos Módulos

### Módulo Principal (`/app`)

* **`config.py`**: Gerencia as variáveis de ambiente utilizando o `pydantic-settings` ou `python-dotenv`. Concentra parâmetros como credenciais de acesso ao PostgreSQL (`DB_NAME`, `DB_USER`, `DB_PASSWORD`), porta do banco e URL do WSDL do CNJ.
* **`database.py`**: Responsável pela inicialização da conexão com o PostgreSQL (via `psycopg2` ou `asyncpg`). Implementa health checks de conexão e gerenciador de contexto para abertura/fechamento automático de sessões.

### Camada de Modelos (`/app/models`)

* **`schemas.py`**: Define as estruturas de dados usando **Pydantic**. Garante a tipagem forte e validação dos objetos de requisição e resposta para as entidades *Classe*, *Assunto* e *Movimento*, além de formatar o contrato JSON devolvido pela API REST.

### Camada de Serviços (`/app/services`)

* **`soap_client.py`**: Isola o cliente HTTP/SOAP (Zeep/Requests). Inclui tratamento de transporte com `User-Agent` personalizado, sanitização de respostas HTML/PHP com erro emitidas pelo servidor do CNJ e métodos auxiliares para extração dos atributos XML do WSDL.
* **`sgt_service.py`**: Implementa o fluxo principal de sincronização de dados. Faz o parsing dos dados consumidos do SOAP, trata a ordenação de nós pais/filhos na árvore e executa as operações de `UPSERT` (`ON CONFLICT`) no banco. Também provê os métodos de consulta consumidos pelos controllers.

### Camada de Controle (`/app/controllers`)

* **`itens_controller.py`**: Expõe as rotas HTTP da API REST (ex: `/api/v1/classes`, `/api/v1/assuntos`, `/api/v1/movimentos`). Processa os parâmetros da requisição, aciona a camada de serviços e retorna os resultados validados pelos schemas.

### Raiz e Banco de Dados

* **`main.py`**: Ponto de entrada principal da aplicação. Configura as instâncias do FastAPI, middleware de CORS, inclusão dos roteadores de endpoints, servidor ASGI Uvicorn e comandos CLI de execução para rotinas de carga inicial de sincronização.
* **`db/migration/`**: Armazena os scripts SQL de migração e criação das estruturas relacionais no schema `sgt_cnj`, incluindo as tabelas de domínio, tabelas de relacionamento, índices GIN/B-tree e tabela de auditoria `log_sincronizacao`.
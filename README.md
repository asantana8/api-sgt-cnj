# Microserviço SGT/CNJ — Tabelas Processuais Unificadas

Microserviço REST construído em **Python (FastAPI)** e **PostgreSQL** para consumo, higienização, persistência e consulta das Tabelas Processuais Unificadas (Classes, Assuntos e Movimentos) do **Sistema de Gestão de Tabelas (SGT)** do Conselho Nacional de Justiça (CNJ).

---

## 🚀 Arquitetura e Recursos

- **API REST (FastAPI + Uvicorn)**: Endpoints assíncronos e documentação automática Swagger/OpenAPI.

- **Estrutura em Camadas (MVC / Controller-Service)**: Separação clara entre Controllers, Services, Schemas Pydantic e Conexão de Banco.

- **Ingestão SOAP Resiliente (Zeep)**: Consumo de WebService público WSDL do CNJ com cabeçalhos simulados.

- **Higienização de Conteúdo**: Limpeza automática de metadados HTML, tags e desintoxicação de entidades em campos de glossário.

- **Idempotência & Upsert Hierárquico**: Carga topológica ordenada por profundidade de árvore para prevenir violações de Chaves Estrangeiras (FK).

- **Soft-Delete Automatizado**: Inativação lógica (`tipo_situacao = 'I'` e `dt_inativacao`) para registros removidos da origem.

### Estrutura do Projeto

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

### Descrição dos Módulos e Componentes

- **Módulo Principal (`/app`)**:
  - `config.py`: Gerencia as variáveis de ambiente utilizando `python-dotenv`. Concentra parâmetros como credenciais de acesso ao PostgreSQL (`DB_NAME`, `DB_USER`, `DB_PASSWORD`), porta do banco e URL do WSDL do CNJ.
  - `database.py`: Responsável pela inicialização da conexão com o PostgreSQL (via `psycopg2`). Implementa health checks de conexão e gerenciador de contexto para abertura/fechamento automático de sessões.

- **Camada de Modelos (`/app/models`)**:
  - `schemas.py`: Define as estruturas de dados usando **Pydantic**. Garante a tipagem forte e validação dos objetos de requisição e resposta para as entidades *Classe*, *Assunto* e *Movimento*, além de formatar o contrato JSON devolvido pela API REST.

- **Camada de Serviços (`/app/services`)**:
  - `soap_client.py`: Isola o cliente HTTP/SOAP (Zeep/Requests). Inclui tratamento de transporte com `User-Agent` personalizado, sanitização de respostas HTML e métodos auxiliares para extração dos atributos XML do WSDL.
  - `sgt_service.py`: Implementa o fluxo principal de sincronização de dados. Faz o parsing dos dados consumidos do SOAP, trata a ordenação de nós pais/filhos na árvore e executa as operações de `UPSERT` (`ON CONFLICT`) no banco. Também provê os métodos de consulta consumidos pelos controllers.

- **Camada de Controle (`/app/controllers`)**:
  - `itens_controller.py`: Expõe as rotas HTTP da API REST (ex: `/api/v1/consulta_itens`, `/api/v1/sincronizar`). Processa os parâmetros da requisição, aciona a camada de serviços e retorna os resultados validados pelos schemas.

- **Raiz e Banco de Dados**:
  - `main.py`: Ponto de entrada principal da aplicação. Configura a instância do FastAPI, inclusão do roteador do controller, servidor Uvicorn e comando CLI (`--sync`) para rotinas de carga de sincronização.
  - `db/migration/`: Armazena os scripts SQL de migração e criação das estruturas relacionais no schema `sgt_cnj`, incluindo as tabelas de domínio, tabelas de relacionamento, índices GIN/B-tree e tabela de auditoria `log_sincronizacao`.

---

## 📌 Pré-requisitos para Desenvolvimento Local

- **Git**
- **Python 3.10+** (recomendado Python 3.12)
- **Rancher Desktop** (para execução via Containers Docker) OU **PostgreSQL 14+** instalado nativamente.

---

## 🛠️ Passo a Passo: Preparando o Ambiente Localhost

### Opção A: Ambiente com Rancher Desktop (Recomendado via Docker Container)

#### 1. Instalar e Configurar o Rancher Desktop
1. Baixe o instalador no site oficial: [https://rancherdesktop.io/](https://rancherdesktop.io/)
2. Durante a instalação:
   - Escolha o engine de container **`dockerd (moby)`** para compatibilidade total com o comando `docker`.
   - Mantenha habilitada a integração com o WSL2 (no Windows).
3. Abra o Rancher Desktop e aguarde a inicialização completa do motor de containers.

#### 2. Subir um Container do PostgreSQL via Rancher Desktop (Docker)
Abra seu terminal (PowerShell) e execute o comando abaixo para iniciar uma instância do PostgreSQL:

```powershell
docker run --name postgres-sgt -e POSTGRES_PASSWORD=<SUA_SENHA_POSTGRES> -p 5432:5432 -d postgres:16
```

---

### Opção B: Instalação Nativa do PostgreSQL (Windows)

#### 1. Instalar o PostgreSQL
1. Baixe o instalador oficial do PostgreSQL para Windows: [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Siga o assistente de instalação:
   - Defina a senha do superusuário `postgres` (guarde esta senha).
   - Defina a porta do banco (ex: `5432`).
   - Marque a instalação das ferramentas de linha de comando (`psql`).
3. Adicione a pasta `bin` do PostgreSQL (ex: `C:\Program Files\PostgreSQL\16\bin`) ao `PATH` do seu sistema, se necessário.

---

## 🗄️ Executando a Migração do Banco de Dados (DDL)

O projeto contém um script DDL idempotente em `db/migration/V00000001__DDL_TABELAS_SOAPWSDL_SGT.sql` responsável por criar a role `sgt_user`, o banco `cnj_sgt_db`, o schema `sgt_cnj`, as tabelas e os índices.

### 1. Definir a variável de senha no terminal
No PowerShell, no diretório do projeto:

```powershell
$env:DB_PASSWORD = "<SUA_SENHA>"
$env:PGPASSWORD = "<SUA_SENHA_POSTGRES>"  # Senha do superusuario administrador local
```

### 2. Executar a Migração via `psql`
```powershell
psql -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 --set=DB_PASSWORD="$env:DB_PASSWORD" -f .\db\migration\V00000001__DDL_TABELAS_SOAPWSDL_SGT.sql
```

### 3. Validar se o Banco e as Tabelas foram criadas
```powershell
psql -h localhost -p 5432 -U postgres -d cnj_sgt_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'sgt_cnj';"
```

---

## 🐍 Configuração do Projeto Python

### 1. Clonar o repositório e navegar até a pasta
```powershell
git clone <URL_DO_REPOSITORIO>
cd SGT-CNJ
```

### 2. Criar e ativar o Ambiente Virtual (venv)
```powershell
# Criar ambiente virtual
python -m venv venv

# Ativar no PowerShell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

### 3. Instalar as dependências
```powershell
pip install -r requirements.txt
```
*(Caso não possua o `requirements.txt`, instale manualmente os pacotes: `pip install fastapi uvicorn psycopg2-binary zeep requests python-dotenv pydantic`)*

### 4. Configurar as Variáveis de Ambiente (`.env`)
Crie ou edite o arquivo `.env` na raiz do projeto com o seguinte conteúdo:

```env
DB_NAME=cnj_sgt_db
DB_USER=postgres
DB_PASSWORD=<SUA_SENHA>
DB_HOST=localhost
DB_PORT=5432
CNJ_WSDL_URL=https://www.cnj.jus.br/sgt/sgt_ws.php?wsdl
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 🚀 Executando o Microserviço

### Modo 1: Execução da API Web REST (Padrão)
Para iniciar o servidor web Uvicorn com hot-reload habilitado:

```powershell
.\venv\Scripts\python.exe .\main.py
```

- **Página Inicial:** `http://localhost:8000/`
- **Documentação Swagger UI (Interativa):** `http://localhost:8000/docs`
- **Documentação ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/health`

### Modo 2: Execução de Sincronização via CLI (Agendador / Cron)
Caso deseje executar apenas o processo de ingestão e atualização das tabelas sem subir o servidor HTTP:

```powershell
.\venv\Scripts\python.exe .\main.py --sync
```

---

## 🔍 Como Testar os Endpoints

### 1. Pelo Swagger UI (Navegador)
1. Acesse `http://localhost:8000/docs`.
2. Abra a rota **`GET /api/v1/consulta_itens`**.
3. Clique em **Try it out**.
4. Teste com os parâmetros:
   - `tipo_consulta`: `c` (Classes), `a` (Assuntos) ou `m` (Movimentos).
   - `codigo`: `2`
5. Clique em **Execute**.

### 2. Por Requisição GET no Navegador ou cURL

- **Consultar Classe por código**:
  `http://localhost:8000/api/v1/consulta_itens?tipo_consulta=c&codigo=2`

- **Buscar Assuntos por termo de descrição**:
  `http://localhost:8000/api/v1/consulta_itens?tipo_consulta=a&descricao=habeas`

- **Disparar Ingestão Manual via POST**:
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sincronizar" -Method POST
  ```

---

## 📁 Estrutura do Projeto

```text
SGT-CNJ/
├── app/
│   ├── config.py                 # Leitura de variáveis de ambiente (.env)
│   ├── database.py               # Pool/Conexão PostgreSQL e validação DDL
│   ├── models/
│   │   └── schemas.py            # Schemas de request/response Pydantic
│   ├── services/
│   │   ├── soap_client.py        # Cliente SOAP Zeep e sanitização de HTML
│   │   └── sgt_service.py       # Regra de negócio (Upsert, Ordenação e Busca SQL)
│   └── controllers/
│       └── itens_controller.py   # Classe Controller REST e Roteador FastAPI
├── db/
│   └── migration/
│       └── V00000001__DDL_TABELAS_SOAPWSDL_SGT.sql  # Script SQL Idempotente
├── resource/
│   └── sgt_ws.xml                # Definição do WSDL do CNJ
├── .env                          # Variáveis de ambiente locais
├── .gitignore                    # Arquivos ignorados pelo Git
├── main.py                       # Entrypoint (FastAPI Server / CLI Execution)
└── README.md                     # Instruções de setup e uso
```

import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import API_HOST, API_PORT, CORS_ORIGINS
from app.database import conectar_banco, verificar_estrutura_banco
from app.controllers.itens_controller import router as itens_router
from app.models.schemas import HealthResponse
from app.services.sgt_service import SGTService

app = FastAPI(
    title="Microserviço SGT/CNJ",
    description="Microserviço REST para ingestão, consulta e sincronização das Tabelas Processuais Unificadas do CNJ.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Libera o consumo da API pelo front-end Angular (BrasilOpenAPI) rodando em outra origem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra o roteador dos controllers
app.include_router(itens_router)


@app.get("/", summary="Página inicial da API")
def read_root():
    return {
        "servico": "Microserviço SGT/CNJ",
        "versao": "1.0.0",
        "documentacao": "/docs",
        "endpoint_consulta": "/api/v1/consulta_itens?tipo_consulta=c"
    }


@app.get("/health", response_model=HealthResponse, summary="Verificação de saúde do serviço e banco")
def healthcheck():
    conn = conectar_banco()
    if not conn:
        return HealthResponse(status="ERROR", banco_conectado=False)

    banco_ok = verificar_estrutura_banco(conn)
    with conn.cursor() as cursor:
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
    conn.close()

    return HealthResponse(
        status="OK" if banco_ok else "WARNING",
        banco_conectado=True,
        banco_nome=db_name
    )


def run_cli_sync():
    print("=== Executando Ingestão SGT/CNJ via CLI ===")
    service = SGTService()
    try:
        resultado = service.executar_sincronizacao_completa()
        print(f"Sincronização concluída com sucesso: {resultado}")
    except Exception as e:
        print(f"Erro na sincronização: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sync":
        run_cli_sync()
    else:
        print(f"Iniciando Microserviço SGT/CNJ em http://{API_HOST}:{API_PORT}")
        uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
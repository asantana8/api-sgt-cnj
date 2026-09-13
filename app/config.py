import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cnj_sgt_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

CNJ_WSDL_URL = os.getenv("CNJ_WSDL_URL", "https://www.cnj.jus.br/sgt/sgt_ws.php?wsdl")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

TABELAS_OBRIGATORIAS = (
    "classe",
    "assunto",
    "movimento",
    "log_sincronizacao",
)

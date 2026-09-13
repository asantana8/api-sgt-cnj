import psycopg2
from contextlib import contextmanager
from app.config import DB_CONFIG, TABELAS_OBRIGATORIAS


def conectar_banco():
    """Cria e retorna uma conexão com o banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None


@contextmanager
def get_db_connection():
    """Context manager para fornecer conexão com commit/rollback automático."""
    conn = conectar_banco()
    if not conn:
        raise RuntimeError("Não foi possível conectar ao banco de dados.")
    try:
        yield conn
    finally:
        conn.close()


def verificar_estrutura_banco(conn):
    """Confirms that database migration script has been applied."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user;")
            banco, usuario = cursor.fetchone()
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sgt_cnj'
                  AND table_name = ANY(%s);
                """,
                (list(TABELAS_OBRIGATORIAS),)
            )
            tabelas_encontradas = {linha[0] for linha in cursor.fetchall()}

        tabelas_faltantes = [
            tabela
            for tabela in TABELAS_OBRIGATORIAS
            if tabela not in tabelas_encontradas
        ]
        if tabelas_faltantes:
            print(
                f"Banco conectado: {banco} (usuário: {usuario}).\n"
                "A conexão funcionou, mas a migração ainda não foi aplicada.\n"
                f"Tabelas ausentes em sgt_cnj: {', '.join(tabelas_faltantes)}."
            )
            return False

        return True
    except psycopg2.Error as erro:
        print(f"Erro ao verificar a estrutura do banco: {erro}")
        return False

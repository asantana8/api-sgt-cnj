import json
import psycopg2
from psycopg2 import extras
from typing import Optional, List, Dict, Any
from app.database import conectar_banco, verificar_estrutura_banco
from app.services.soap_client import obter_cliente_soap, extrair_atributo, limpar_html


class SGTService:
    """Serviço responsável pela ingestão de dados SOAP e consulta no PostgreSQL."""

    def registrar_log(self, conn, tipo_tabela: str, status: str, registros_processados: int = 0, mensagem_erro: str = None):
        """Registra o resultado da sincronização na tabela de log."""
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sgt_cnj.log_sincronizacao
                        (tipo_tabela, status, registros_processados, mensagem_erro)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (tipo_tabela, status, registros_processados, mensagem_erro)
                )
            conn.commit()
        except psycopg2.Error as erro_log:
            conn.rollback()
            print(f"Aviso: não foi possível registrar o log em sgt_cnj.log_sincronizacao: {erro_log}")

    def sincronizar_tabela(self, client, conn, tipo_tabela: str, tabela_destino: str, coluna_pk: str, coluna_fk_pai: str) -> int:
        """Sincroniza uma tabela específica (C, A, M) com o webservice SOAP do CNJ."""
        print(f"\n--- Sincronizando {tabela_destino.upper()} (Tipo: {tipo_tabela}) ---")
        resposta = client.service.pesquisarItemPublicoWS(
            tipoTabela=tipo_tabela,
            tipoPesquisa='N',
            valorPesquisa='%'
        )

        if not resposta:
            print(f"Nenhum registro retornado para a tabela {tabela_destino}.")
            return 0

        registros = []
        for item in resposta:
            cod_item = extrair_atributo(item, 'cod_item', 'codItem', 'codigo')
            cod_pai = extrair_atributo(item, 'cod_item_pai', 'codItemPai', 'codigoPai', 'cod_pai')
            nome = extrair_atributo(item, 'nome', 'descricaoItem') or ''
            sigla = extrair_atributo(item, 'sigla')
            descricao = extrair_atributo(item, 'descricao')
            glossario_bruto = extrair_atributo(item, 'dscGlossario', 'glossario')
            glossario = limpar_html(glossario_bruto)
            situacao = extrair_atributo(item, 'situacao', 'tipoSituacao') or 'A'
            dados_adicionais = json.dumps({"raw": str(item)}, ensure_ascii=False)

            if cod_item:
                registros.append({
                    coluna_pk: int(cod_item),
                    coluna_fk_pai: int(cod_pai) if cod_pai and str(cod_pai).isdigit() else None,
                    'nome': str(nome),
                    'sigla': str(sigla) if sigla else None,
                    'descricao': str(descricao) if descricao else None,
                    'glossario': str(glossario) if glossario else None,
                    'tipo_situacao': str(situacao)[0].upper() if situacao else 'A',
                    'dados_adicionais': dados_adicionais
                })

        # Mapeia ID -> pai para calcular a profundidade
        pai_map = {r[coluna_pk]: r[coluna_fk_pai] for r in registros}

        def calcular_profundidade(item_id):
            depth = 0
            visitados = set()
            atual = item_id
            while atual in pai_map and pai_map[atual] is not None:
                if atual in visitados:
                    break
                visitados.add(atual)
                atual = pai_map[atual]
                depth += 1
            return depth

        registros.sort(key=lambda x: (calcular_profundidade(x[coluna_pk]), x[coluna_pk]))

        colunas = [
            coluna_pk, coluna_fk_pai, 'nome', 'descricao', 'glossario',
            'tipo_situacao', 'dados_adicionais'
        ]
        if tabela_destino == 'classe':
            colunas.insert(3, 'sigla')

        colunas_sql = ', '.join(colunas)
        valores_sql = ', '.join(['%s'] * len(colunas))
        atualizacoes = [
            f'{coluna} = EXCLUDED.{coluna}'
            for coluna in colunas
            if coluna not in (coluna_pk, coluna_fk_pai)
        ]
        atualizacoes.append('dt_alteracao = CURRENT_TIMESTAMP')
        atualizacoes.append(
            f"dt_inativacao = CASE WHEN EXCLUDED.tipo_situacao = 'I' "
            f"THEN COALESCE(sgt_cnj.{tabela_destino}.dt_inativacao, CURRENT_TIMESTAMP) "
            f"ELSE NULL END"
        )

        query = f"""
            INSERT INTO sgt_cnj.{tabela_destino} (
                {colunas_sql}
            )
            VALUES ({valores_sql})
            ON CONFLICT ({coluna_pk}) DO UPDATE SET
                {', '.join(atualizacoes)};
        """

        valores = [
            tuple(r[coluna] for coluna in colunas)
            for r in registros
        ]

        ids_origem = [r[coluna_pk] for r in registros]

        with conn.cursor() as cursor:
            extras.execute_batch(cursor, query, valores, page_size=500)
            
            if ids_origem:
                cursor.execute(
                    f"""
                    UPDATE sgt_cnj.{tabela_destino}
                    SET tipo_situacao = 'I',
                        dt_inativacao = COALESCE(dt_inativacao, CURRENT_TIMESTAMP),
                        dt_alteracao = CURRENT_TIMESTAMP
                    WHERE NOT ({coluna_pk} = ANY(%s))
                      AND (tipo_situacao IS DISTINCT FROM 'I' OR dt_inativacao IS NULL);
                    """,
                    (ids_origem,)
                )
                qtd_inativados = cursor.rowcount
                if qtd_inativados > 0:
                    print(f"Inativados {qtd_inativados} registros removidos da origem em 'sgt_cnj.{tabela_destino}'.")

            conn.commit()
            self.registrar_log(conn, tabela_destino.upper(), 'SUCESSO', len(registros))
            print(f"Sucesso! Total de {len(registros)} registros sincronizados em 'sgt_cnj.{tabela_destino}'.")
            return len(registros)

    def executar_sincronizacao_completa(self) -> Dict[str, Any]:
        """Executa o processo de sincronização para Classes, Assuntos e Movimentos."""
        conn = conectar_banco()
        if not conn:
            raise RuntimeError("Falha de conexão com o banco de dados PostgreSQL.")

        try:
            if not verificar_estrutura_banco(conn):
                raise RuntimeError("As tabelas necessárias não existem no banco de dados.")

            client = obter_cliente_soap()
            if not client:
                raise RuntimeError("Falha de conexão com o Webservice SOAP do CNJ.")

            qtd_c = self.sincronizar_tabela(client, conn, 'C', 'classe', 'cod_classe', 'cod_classe_pai')
            qtd_a = self.sincronizar_tabela(client, conn, 'A', 'assunto', 'cod_assunto', 'cod_assunto_pai')
            qtd_m = self.sincronizar_tabela(client, conn, 'M', 'movimento', 'cod_movimento', 'cod_movimento_pai')

            return {
                "classe": qtd_c,
                "assunto": qtd_a,
                "movimento": qtd_m,
                "total": qtd_c + qtd_a + qtd_m
            }
        finally:
            conn.close()

    def consultar_itens(
        self,
        tipo_consulta: str,
        codigo: Optional[int] = None,
        descricao: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Consulta itens no PostgreSQL.
        tipo_consulta: 'a' (Assunto), 'c' (Classe), 'm' (Movimento)
        codigo: Código numérico exato do item
        descricao: Termo livre para busca em nome/descrição/glossário
        """
        tipo = tipo_consulta.lower().strip()
        if tipo not in ('a', 'c', 'm'):
            raise ValueError("O parâmetro tipo_consulta deve ser 'a' (Assunto), 'c' (Classe) ou 'm' (Movimento).")

        mapeamento = {
            'c': ('classe', 'cod_classe', 'cod_classe_pai'),
            'a': ('assunto', 'cod_assunto', 'cod_assunto_pai'),
            'm': ('movimento', 'cod_movimento', 'cod_movimento_pai')
        }

        tabela, col_pk, col_fk_pai = mapeamento[tipo]

        conn = conectar_banco()
        if not conn:
            raise RuntimeError("Erro ao conectar ao banco de dados.")

        try:
            where_conditions = []
            params = []

            if codigo is not None:
                where_conditions.append(f"{col_pk} = %s")
                params.append(codigo)

            if descricao is not None and descricao.strip():
                termo = f"%{descricao.strip()}%"
                where_conditions.append("(nome ILIKE %s OR descricao ILIKE %s OR glossario ILIKE %s)")
                params.extend([termo, termo, termo])

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            query = f"""
                SELECT {col_pk}, {col_fk_pai}, nome, 
                       {'sigla' if tipo == 'c' else 'NULL AS sigla'},
                       descricao, glossario, tipo_situacao,
                       {'dispositivo_legal' if tipo == 'a' else 'NULL AS dispositivo_legal'},
                       {'artigo' if tipo == 'a' else 'NULL AS artigo'},
                       dt_publicacao, dt_alteracao, dt_inativacao
                FROM sgt_cnj.{tabela}
                {where_clause}
                ORDER BY {col_pk} ASC
                LIMIT 500;
            """

            with conn.cursor() as cursor:
                cursor.execute(query, params)
                colunas = [desc[0] for desc in cursor.description]
                linhas = cursor.fetchall()

            resultados = []
            for linha in linhas:
                d = dict(zip(colunas, linha))
                resultados.append({
                    "codigo": d[col_pk],
                    "codigo_pai": d[col_fk_pai],
                    "nome": d["nome"],
                    "sigla": d["sigla"],
                    "descricao": d["descricao"],
                    "glossario": d["glossario"],
                    "tipo_situacao": d["tipo_situacao"],
                    "dispositivo_legal": d["dispositivo_legal"],
                    "artigo": d["artigo"],
                    "dt_publicacao": str(d["dt_publicacao"]) if d["dt_publicacao"] else None,
                    "dt_alteracao": str(d["dt_alteracao"]) if d["dt_alteracao"] else None,
                    "dt_inativacao": str(d["dt_inativacao"]) if d["dt_inativacao"] else None,
                })

            return resultados
        finally:
            conn.close()

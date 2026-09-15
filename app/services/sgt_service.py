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

    TERMOS_SINCRONIZACAO = [
        'PROCESSO', 'ACAO', 'RECURSO', 'EXECUCAO', 'MANDADO', 'HABEAS', 'CRIME', 'PENAL', 'CIVIL',
        'TRIBUTARIO', 'PREVIDENCIARIO', 'ADMINISTRATIVO', 'TRABALHO', 'FAZENDA', 'JUIZADO', 'AUTO',
        'PEDIDO', 'SENTENCA', 'DESPACHO', 'DECISAO', 'ATO', 'CERTIDAO', 'INTIMACAO', 'CITACAO',
        'JULGAMENTO', 'BAIXA', 'ARQUIVAMENTO', 'DISTRIBUICAO', 'REDISTRIBUICAO', 'AUDIENCIA',
        'PERICIA', 'LAUDO', 'PENHORA', 'BLOQUEIO', 'LIBERACAO', 'EXPEDICAO', 'OFICIO', 'ALVARA',
        'CARTA', 'PRECATÓRIA', 'ROGATORIA', 'AGRAVO', 'APELACAO', 'EMBARGOS', 'CONFLITO',
        'EXCECAO', 'INCIDENTE', 'RECLAMACAO', 'REPRESENTACAO', 'INQUERITO', 'TERMO', 'NOTIFICACAO',
        'HOMOLOGACAO', 'ACORDO', 'EXTINCAO', 'SUSPENSAO', 'SOBRESTAMENTO', 'REMESSA', 'RECEBIMENTO',
        'JUNTADA', 'CONCLUSAO', 'VISTA', 'DECURSO', 'PUBLICACAO', 'TRANSITO', 'CUMPRIMENTO',
        'DIREITO', 'CONTRATO', 'BENS', 'INDENIZACAO', 'DANO', 'COBRANCA', 'REGISTRO', 'MULTA',
        'SERVICO', 'SERVIDOR', 'IMPOSTO', 'BENEFICIO', 'APOSENTADORIA', 'PENSAO', 'SAUDE',
        'MEDICAMENTO', 'MEIO AMBIENTE', 'DESAPROPRIACAO', 'POSSE', 'PROPRIEDADE', 'FAMILIA',
        'ALIMENTOS', 'DIVORCIO', 'INVENTARIO', 'SUCESSOES', 'FALENCIA', 'RECUPERACAO', 'TITULO',
        'CHEQUE', 'NOTA', 'DUPLICATA', 'ALIENACAO', 'ARRENDAMENTO', 'LOCACAO', 'CONDOMINIO'
    ]

    def _obter_itens_soap(self, client, tipo_tabela: str) -> List[Any]:
        """Obtém os itens do WebService SOAP do CNJ de forma resiliente."""
        # Tenta primeiro a busca universal (caso o webservice suporte no futuro)
        for coringa in ['%']:
            try:
                resposta = client.service.pesquisarItemPublicoWS(
                    tipoTabela=tipo_tabela,
                    tipoPesquisa='N',
                    valorPesquisa=coringa
                )
                if resposta:
                    return list(resposta)
            except Exception:
                pass

        # Fallback resiliente: coleta por lista de termos jurídicos abrangentes (Nome e Glossário)
        print(f"Executando varredura por termos estruturados no WebService SGT/CNJ (Tabela {tipo_tabela})...")
        itens_unicos = {}
        for termo in self.TERMOS_SINCRONIZACAO:
            for tipo_pesquisa in ['N', 'G']:
                try:
                    resposta = client.service.pesquisarItemPublicoWS(
                        tipoTabela=tipo_tabela,
                        tipoPesquisa=tipo_pesquisa,
                        valorPesquisa=termo
                    )
                    if resposta:
                        for item in resposta:
                            cod_item = extrair_atributo(item, 'cod_item', 'codItem', 'codigo')
                            if cod_item and cod_item not in itens_unicos:
                                itens_unicos[cod_item] = item
                except Exception:
                    continue

        return list(itens_unicos.values())

    def sincronizar_tabela(self, client, conn, tipo_tabela: str, tabela_destino: str, coluna_pk: str, coluna_fk_pai: str) -> int:
        """Sincroniza uma tabela específica (C, A, M) com o webservice SOAP do CNJ."""
        print(f"\n--- Sincronizando {tabela_destino.upper()} (Tipo: {tipo_tabela}) ---")
        resposta = self._obter_itens_soap(client, tipo_tabela)

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

        # Insere em duas passagens para respeitar Foreign Keys mesmo com nós órfãos parciais:
        # Passagem 1: Insere todos os registros com coluna_fk_pai = NULL
        colunas_sem_pai = [c for c in colunas if c != coluna_fk_pai]
        colunas_sem_pai_sql = ', '.join(colunas_sem_pai)
        valores_sem_pai_sql = ', '.join(['%s'] * len(colunas_sem_pai))
        atualizacoes_sem_pai = [
            f'{coluna} = EXCLUDED.{coluna}'
            for coluna in colunas_sem_pai
            if coluna != coluna_pk
        ]
        atualizacoes_sem_pai.append('dt_alteracao = CURRENT_TIMESTAMP')

        query_sem_pai = f"""
            INSERT INTO sgt_cnj.{tabela_destino} (
                {colunas_sem_pai_sql}
            )
            VALUES ({valores_sem_pai_sql})
            ON CONFLICT ({coluna_pk}) DO UPDATE SET
                {', '.join(atualizacoes_sem_pai)};
        """

        valores_sem_pai = [
            tuple(r[coluna] for coluna in colunas_sem_pai)
            for r in registros
        ]

        # Passagem 2: Atualiza a coluna do nó pai onde aplicável
        query_atualizar_pai = f"""
            UPDATE sgt_cnj.{tabela_destino}
            SET {coluna_fk_pai} = %s,
                dt_alteracao = CURRENT_TIMESTAMP
            WHERE {coluna_pk} = %s;
        """
        # Apenas atualiza o pai se o registro do pai realmente existir no conjunto inserido
        chaves_existentes = {r[coluna_pk] for r in registros}
        valores_pai = [
            (r[coluna_fk_pai], r[coluna_pk])
            for r in registros
            if r[coluna_fk_pai] and r[coluna_fk_pai] in chaves_existentes
        ]

        ids_origem = [r[coluna_pk] for r in registros]

        with conn.cursor() as cursor:
            extras.execute_batch(cursor, query_sem_pai, valores_sem_pai, page_size=500)
            if valores_pai:
                extras.execute_batch(cursor, query_atualizar_pai, valores_pai, page_size=500)
            
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

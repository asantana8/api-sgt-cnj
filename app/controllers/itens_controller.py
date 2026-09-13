from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, status
from app.models.schemas import ItemResponse, SincronizacaoResponse
from app.services.sgt_service import SGTService


class ItensController:
    """
    Classe Controller para expor e gerenciar as requisições de consulta e sincronização
    do serviço de Tabelas Processuais Unificadas (SGT/CNJ).
    """

    def __init__(self, service: SGTService = None):
        self.service = service or SGTService()

    def consulta_itens(
        self,
        tipo_consulta: str,
        codigo: Optional[int] = None,
        descricao: Optional[str] = None
    ) -> List[ItemResponse]:
        """
        Consulta itens (Classes, Assuntos ou Movimentos) filtrando por código ou descrição.
        tipo_consulta: 'a' (Assunto), 'c' (Classe), 'm' (Movimento)
        """
        try:
            itens = self.service.consultar_itens(
                tipo_consulta=tipo_consulta,
                codigo=codigo,
                descricao=descricao
            )
            return [ItemResponse(**item) for item in itens]
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao consultar itens: {str(e)}"
            )

    def sincronizar(self) -> SincronizacaoResponse:
        """Dispara manualmente a sincronização SOAP de todas as tabelas."""
        try:
            resultado = self.service.executar_sincronizacao_completa()
            return SincronizacaoResponse(
                status="SUCESSO",
                mensagem="Sincronização realizada com sucesso.",
                detalhes=resultado
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro durante a sincronização: {str(e)}"
            )


# Instância única da classe Controller
itens_controller = ItensController()

# Roteador FastAPI
router = APIRouter(prefix="/api/v1", tags=["SGT CNJ"])


@router.get(
    "/consulta_itens",
    response_model=List[ItemResponse],
    summary="Consulta itens das Tabelas Processuais Unificadas (SGT/CNJ)"
)
def consulta_itens_endpoint(
    tipo_consulta: str = Query(
        ...,
        description="Tipo de consulta: 'a' (Assunto), 'c' (Classe) ou 'm' (Movimento)"
    ),
    codigo: Optional[int] = Query(None, description="Código numérico exato do item"),
    descricao: Optional[str] = Query(None, description="Nome ou descrição para busca parcial")
):
    """
    Exposta através da classe Controller `ItensController`.
    Retorna a lista de itens consultados conforme os parâmetros informados.
    """
    return itens_controller.consulta_itens(
        tipo_consulta=tipo_consulta,
        codigo=codigo,
        descricao=descricao
    )


@router.post(
    "/sincronizar",
    response_model=SincronizacaoResponse,
    summary="Dispara a sincronização manual das tabelas com o SOAP do CNJ"
)
def sincronizar_endpoint():
    """
    Exposta através da classe Controller `ItensController`.
    Realiza a leitura do WSDL público e insere/atualiza os dados no PostgreSQL.
    """
    return itens_controller.sincronizar()

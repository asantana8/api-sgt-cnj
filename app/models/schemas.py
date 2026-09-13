from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ItemResponse(BaseModel):
    codigo: int = Field(..., description="Código identificador do item")
    codigo_pai: Optional[int] = Field(None, description="Código do item pai na hierarquia")
    nome: str = Field(..., description="Nome do item")
    sigla: Optional[str] = Field(None, description="Sigla (apenas para Classes)")
    descricao: Optional[str] = Field(None, description="Descrição detalhada do item")
    glossario: Optional[str] = Field(None, description="Glossário limpo (sem HTML)")
    tipo_situacao: str = Field(..., description="Situação: 'A' (Ativo) ou 'I' (Inativo)")
    dispositivo_legal: Optional[str] = Field(None, description="Dispositivo legal (apenas para Assuntos)")
    artigo: Optional[str] = Field(None, description="Artigo da lei (apenas para Assuntos)")
    dt_publicacao: Optional[str] = Field(None, description="Data de publicação")
    dt_alteracao: Optional[str] = Field(None, description="Data da última alteração")
    dt_inativacao: Optional[str] = Field(None, description="Data de inativação (se inativo)")


class SincronizacaoResponse(BaseModel):
    status: str
    mensagem: str
    detalhes: dict


class HealthResponse(BaseModel):
    status: str
    banco_conectado: bool
    banco_nome: Optional[str] = None

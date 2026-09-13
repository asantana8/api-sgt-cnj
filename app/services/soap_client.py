import re
import html
import requests
from zeep import Client
from zeep.transports import Transport
from app.config import CNJ_WSDL_URL


def obter_cliente_soap():
    """Inicializa o cliente Zeep SOAP com User-Agent customizado para contornar bloqueios do CNJ."""
    print("Conectando ao webservice SOAP do CNJ...")
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        transport = Transport(session=session, timeout=30)
        client = Client(wsdl=CNJ_WSDL_URL, transport=transport)
        print("Conexão WSDL estabelecida com sucesso.")
        return client
    except Exception as e:
        print(f"Erro ao conectar no WSDL: {e}")
        return None


def extrair_atributo(objeto, *atributos):
    """Busca dinamicamente atributos retornados no XML do Zeep."""
    for attr in atributos:
        if hasattr(objeto, attr):
            valor = getattr(objeto, attr)
            if valor is not None:
                return valor
    return None


def limpar_html(texto):
    """Remove tags e metadados HTML, converte entidades e normaliza espaços de um texto."""
    if not texto:
        return None
    texto_str = str(texto)
    texto_sem_blocos = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', texto_str, flags=re.DOTALL | re.IGNORECASE)
    texto_decodificado = html.unescape(texto_sem_blocos)
    texto_sem_tags = re.sub(r'<[^>]+>', ' ', texto_decodificado)
    texto_limpo = re.sub(r'\s+', ' ', texto_sem_tags).strip()
    return texto_limpo if texto_limpo else None

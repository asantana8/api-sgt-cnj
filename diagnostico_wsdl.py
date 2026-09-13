import requests

#WSDL_URL = "https://www.cnj.jus.br/sgt/infWebService.php?wsdl"
WSDL_URL = "https://www.cnj.jus.br/sgt/sgt_ws.php?wsdl"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print(f"Fazendo requisição para: {WSDL_URL}\n")

try:
    response = requests.get(WSDL_URL, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}\n")

    linhas = response.text.splitlines()
    print(f"Total de linhas retornadas: {len(linhas)}\n")

    print("--- CONTEÚDO EM TORNO DA LINHA 34 ---")
    inicio = max(0, 34 - 10)
    fim = min(len(linhas), 34 + 10)

    for idx in range(inicio, fim):
        num_linha = idx + 1
        marcador = "===> " if num_linha == 34 else "     "
        print(f"{marcador}Linha {num_linha:02d}: {linhas[idx]}")

except Exception as e:
    print(f"Erro ao acessar o WSDL: {e}")
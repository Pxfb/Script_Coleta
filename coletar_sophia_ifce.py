"""
Coletor de itens digitais (PDF) da Biblioteca Sophia - IFCE
=============================================================

O QUE ESSE SCRIPT FAZ
----------------------
1. Percorre os "códigos" das obras (detalhe.asp?codigo=N) em sequência.
2. Para cada código, verifica se o item tem conteúdo digital (PDF).
3. Verifica se o tipo do material está em TIPOS_DESEJADOS (por padrão,
   só "TCC") - se não estiver, pula sem baixar.
4. Se for do tipo certo, extrai título, tipo e o link de download do
   PDF, e baixa o PDF para a pasta ./pdfs/
5. Salva tudo (metadados + nome do arquivo salvo) em um CSV.
6. É RETOMÁVEL: se você parar e rodar de novo, ele pula os códigos já
   processados (lê o CSV existente).

COMO USAR
---------
1. Instale as dependências:
   pip install requests beautifulsoup4

2. Ajuste as variáveis CODIGO_INICIAL e CODIGO_FINAL lá embaixo.
   - Dica: comece com um intervalo pequeno (ex: 143800 a 143850) só
     pra testar se está funcionando, depois expanda.
   - O maior código visto até agora foi por volta de 143835 (setembro/2026).
     Itens mais antigos têm código menor. Se quiser TODO o acervo digital,
     pode rodar de 1 até o código mais recente.

3. Rode: python coletar_sophia_ifce.py

IMPORTANTE - USO RESPONSÁVEL
-----------------------------
- O script já tem uma pausa (SLEEP_SEGUNDOS) entre requisições para não
  sobrecarregar o servidor da biblioteca. Não recomendo remover isso.
- Como são só PDFs de acesso público (que qualquer pessoa consegue abrir
  pelo site, sem login), isso é equivalente a um usuário navegando e
  baixando manualmente — só que automatizado. Ainda assim, respeite os
  termos de uso da biblioteca e evite rodar isso de forma agressiva.
"""

import csv
import os
import re
import time
import requests
from bs4 import BeautifulSoup

# ============ CONFIGURAÇÃO ============
CODIGO_INICIAL = 143800
CODIGO_FINAL = 143850          # ajuste para o intervalo que você quer
SLEEP_SEGUNDOS = 1.0            # pausa entre requisições (educado com o servidor)
PASTA_PDFS = "pdfs"
ARQUIVO_CSV = "acervo_digital_ifce.csv"

# Só baixa itens cujo "Inf. publicação" contenha um desses textos
# (comparação sem diferenciar maiúsculas/minúsculas).
# No site, os tipos aparecem como "TCC - Português", "TCCE (Especialização) - Português" etc.
# Ajuste essa lista se quiser incluir/excluir algum tipo.
TIPOS_DESEJADOS = ["TCC"]

BASE_URL = "https://biblioteca.ifce.edu.br/mobile"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ColetorAcervoDigital/1.0)"
}
# ========================================


def carregar_codigos_ja_processados():
    """Lê o CSV existente (se houver) e retorna o conjunto de códigos já feitos."""
    if not os.path.exists(ARQUIVO_CSV):
        return set()
    with open(ARQUIVO_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {int(row["codigo"]) for row in reader}


def garantir_csv_com_cabecalho():
    if not os.path.exists(ARQUIVO_CSV):
        with open(ARQUIVO_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["codigo", "titulo", "autor", "tipo", "assuntos", "arquivo_local", "url_pdf"])


def extrair_dados_item(codigo, session):
    """Busca a página de detalhe e retorna um dict com os metadados, ou None se não houver PDF."""
    url = f"{BASE_URL}/detalhe.asp?idioma=ptbr&acesso=web&codigo={codigo}&tipo=1&detalhe=0&busca=3"
    resp = session.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.content, "html.parser")

    # Procura o link de download do PDF
    link_pdf = None
    for a in soup.find_all("a", href=True):
        if "download.asp" in a["href"]:
            link_pdf = a["href"]
            if not link_pdf.startswith("http"):
                link_pdf = f"{BASE_URL}/{link_pdf.lstrip('/')}"
            break

    if not link_pdf:
        return None  # item sem conteúdo digital

    # Tipo de material: vem na tabela "Inf. publicação | TCC - Português"
    tipo = ""
    for tr in soup.find_all("tr"):
        cols = tr.find_all("td")
        if len(cols) >= 2 and "publicaç" in cols[0].get_text(strip=True).lower():
            tipo = cols[1].get_text(strip=True)
            break

    texto_completo = soup.get_text("\n", strip=True)

    # Plano B: se não achou o campo "tipo" pela tabela (ex: layout diferente),
    # procura os TIPOS_DESEJADOS direto no texto da página inteira antes de descartar.
    bateu_filtro = any(desejado.lower() in tipo.lower() for desejado in TIPOS_DESEJADOS)
    if not bateu_filtro and not tipo:
        bateu_filtro = any(desejado.lower() in texto_completo.lower() for desejado in TIPOS_DESEJADOS)

    if not bateu_filtro:
        return "tipo_indesejado"  # item digital, mas não é o tipo que queremos

    # Título (costuma estar num h4/h5 de destaque)
    titulo_tag = soup.find(["h4", "h5", "h3"])
    titulo = titulo_tag.get_text(strip=True) if titulo_tag else f"item_{codigo}"

    return {
        "codigo": codigo,
        "titulo": titulo,
        "tipo": tipo,
        "url_pdf": link_pdf,
        "texto_pagina": texto_completo,  # guardamos tudo cru; refinamos depois se quiser
    }


def baixar_pdf(url_pdf, codigo, session):
    os.makedirs(PASTA_PDFS, exist_ok=True)
    nome_arquivo = os.path.join(PASTA_PDFS, f"{codigo}.pdf")
    if os.path.exists(nome_arquivo):
        return nome_arquivo
    resp = session.get(url_pdf, headers=HEADERS, timeout=60)
    if resp.status_code == 200 and resp.content[:4] == b"%PDF":
        with open(nome_arquivo, "wb") as f:
            f.write(resp.content)
        return nome_arquivo
    return None


def main():
    garantir_csv_com_cabecalho()
    ja_processados = carregar_codigos_ja_processados()
    session = requests.Session()

    with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for codigo in range(CODIGO_INICIAL, CODIGO_FINAL + 1):
            if codigo in ja_processados:
                continue

            try:
                dados = extrair_dados_item(codigo, session)
            except requests.RequestException as e:
                print(f"[{codigo}] erro de rede: {e}")
                time.sleep(SLEEP_SEGUNDOS * 3)
                continue

            if dados is None:
                # sem conteúdo digital, ainda assim marca como visto
                writer.writerow([codigo, "", "", "", "", "", ""])
                f.flush()
                time.sleep(SLEEP_SEGUNDOS)
                continue

            if dados == "tipo_indesejado":
                # tem PDF, mas não é um dos TIPOS_DESEJADOS (ex: é Livro, Dissertação...)
                writer.writerow([codigo, "", "", "(fora do filtro)", "", "", ""])
                f.flush()
                time.sleep(SLEEP_SEGUNDOS)
                continue

            arquivo_local = baixar_pdf(dados["url_pdf"], codigo, session)
            writer.writerow([
                codigo,
                dados["titulo"],
                "",  # autor: refine extraindo do texto_pagina se precisar
                dados["tipo"],
                "",  # assuntos
                arquivo_local or "",
                dados["url_pdf"],
            ])
            f.flush()
            print(f"[{codigo}] OK -> {dados['titulo'][:60]}")
            time.sleep(SLEEP_SEGUNDOS)

    print("Concluído.")


if __name__ == "__main__":
    main()
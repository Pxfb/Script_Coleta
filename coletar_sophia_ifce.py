"""
Coletor de itens digitais (PDF) da Biblioteca Sophia - IFCE
=============================================================
VERSAO "LISTA A PARTIR DO XML"

O QUE ESSE SCRIPT FAZ
----------------------
1. Le o arquivo XML exportado do Sophia (MARC XML) e extrai os codigos
   do campo de controle 001 de cada <record> - esses sao os mesmos
   codigos usados na URL detalhe.asp?codigo=N do site.
2. Para cada codigo da lista (e so eles - nao percorre um intervalo
   sequencial mais), verifica se o item tem conteudo digital (PDF).
3. Verifica se o tipo do material esta em TIPOS_DESEJADOS (por padrao,
   "Tese" e "Dissertação", ja que e esse o acervo do XML) - se nao
   estiver, pula sem baixar.
4. Se for do tipo certo, extrai titulo, tipo e o link de download do
   PDF, e baixa o PDF para a pasta ./pdfs/
5. Salva tudo (metadados + nome do arquivo salvo) em um CSV.
6. E RETOMAVEL: se voce parar e rodar de novo, ele pula os codigos ja
   processados (le o CSV existente).

COMO USAR
---------
1. Instale as dependencias:
   pip install requests beautifulsoup4

2. Ajuste XML_ENTRADA la embaixo pro caminho do seu arquivo MARC XML
   (por padrao ja aponta pro "Arquivo_Marc_Teses_Dissertações.xml").

3. Rode: python coletar_sophia_ifce_lista.py

   Se quiser testar rapido com poucos codigos antes de rodar tudo,
   defina LIMITE_TESTE la embaixo (ex: 5) - ele processa so os N
   primeiros codigos da lista extraida do XML.

IMPORTANTE - USO RESPONSAVEL
-----------------------------
- O script ja tem uma pausa (SLEEP_SEGUNDOS) entre requisicoes para nao
  sobrecarregar o servidor da biblioteca. Nao recomendo remover isso.
- Como sao so PDFs de acesso publico (que qualquer pessoa consegue abrir
  pelo site, sem login), isso e equivalente a um usuario navegando e
  baixando manualmente — so que automatizado. Ainda assim, respeite os
  termos de uso da biblioteca e evite rodar isso de forma agressiva.
"""

import csv
import os
import re
import time
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

# ============ CONFIGURAÇÃO ============
XML_ENTRADA = "Arquivo Marc Teses Dissertações.xml"  # arquivo MARC XML com os registros
LIMITE_TESTE = None           # ex: 5 pra testar so os 5 primeiros codigos; None = todos
SLEEP_SEGUNDOS = 1.0             # pausa entre requisições (educado com o servidor)
PASTA_PDFS = "pdfs"
ARQUIVO_CSV = "acervo_digital_ifce.csv"

# Só baixa itens cujo "Inf. publicação" contenha um desses textos
# (comparação sem diferenciar maiúsculas/minúsculas).
# Ajuste essa lista se quiser incluir/excluir algum tipo (ex: adicionar "TCC").
TIPOS_DESEJADOS = ["Tese", "Dissertação"]

BASE_URL = "https://biblioteca.ifce.edu.br/mobile"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ColetorAcervoDigital/1.0)"
}
# ========================================


def carregar_codigos_do_xml(caminho_xml):
    """Lê o MARC XML e devolve a lista de códigos Sophia (campo 001 de
    cada <record>), na ordem em que aparecem no arquivo, como inteiros
    (removendo zeros à esquerda: '000109304' -> 109304, que é o formato
    usado na URL detalhe.asp?codigo=N)."""
    tree = ET.parse(caminho_xml)
    root = tree.getroot()
    codigos = []
    for record in root.findall("record"):
        cf = record.find("controlfield[@tag='001']")
        if cf is not None and cf.text and cf.text.strip():
            codigos.append(int(cf.text.strip()))
    return codigos


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
    if not os.path.exists(XML_ENTRADA):
        print(f"Não encontrei {XML_ENTRADA}. Ajuste XML_ENTRADA lá em cima.")
        return

    codigos = carregar_codigos_do_xml(XML_ENTRADA)
    print(f"{len(codigos)} códigos lidos do XML.")

    if LIMITE_TESTE is not None:
        codigos = codigos[:LIMITE_TESTE]
        print(f"LIMITE_TESTE ativo: processando só os {len(codigos)} primeiros.")

    garantir_csv_com_cabecalho()
    ja_processados = carregar_codigos_ja_processados()
    session = requests.Session()

    with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for codigo in codigos:
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

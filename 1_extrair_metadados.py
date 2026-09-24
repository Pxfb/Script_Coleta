"""
ETAPA 1 - Extrair metadados completos (Dublin Core do Sophia + resumo do PDF)
================================================================================
 
O QUE FAZ
---------
Para cada item ja baixado (usa o CSV gerado no script anterior,
acervo_digital_ifce.csv), este script:
 
1. Busca os metadados no endpoint "Dublin Core" do proprio Sophia
   (ajxDublinCore.asp?cod=<codigo>) - esse endpoint retorna, de forma
   estruturada e confiavel: titulo, autor(es), ORIENTADOR (contributor),
   assuntos, tipo, ano e a descricao (que ja vem com o CAMPUS escrito,
   ex: "IFCE/ Campus Fortaleza, Fortaleza-CE, 2019").
2. Abre o PDF ja baixado e le o texto das 3 primeiras paginas so pra
   tentar achar o RESUMO (esse campo nao vem no Dublin Core do Sophia).
3. Salva tudo em metadados_completos.csv, ja incluindo uma coluna
   "campus" extraida da descricao.
 
O QUE MUDOU NESSA VERSAO (v2)
------------------------------
Na primeira versao, TODOS os campos do Dublin Core vinham vazios pra
praticamente todo mundo. Os motivos mais provaveis (e as correcoes
feitas aqui):
 
1. O parser so sabia ler dois formatos (tabela com rotulo em ingles,
   ou texto solto). O Sophia provavelmente devolve os rotulos em
   PORTUGUES ("Titulo", "Autor(es)", "Orientador"...) e/ou usa <meta>
   tags DC.* ou uma lista <dl>/<dt>/<dd>. Agora o parser tenta, nessa
   ordem: <meta name="DC.xxx">, tabela <tr><td>, <dl><dt><dd> e por
   ultimo texto solto - com um dicionario de sinonimos em portugues
   pra cada campo.
2. O endpoint AJAX provavelmente depende de o navegador ter "entrado"
   na pagina de detalhe do item antes (pra setar variaveis de sessao
   no servidor). Agora o script visita detalhe.asp do item ANTES de
   chamar o ajxDublinCore.asp, e manda um Referer apontando pra essa
   pagina.
3. Os dois scripts usavam bases de URL diferentes (o coletor usa
   "/mobile", esse script usava a raiz do site). Agora ele tenta as
   duas variantes de URL do endpoint e fica com a que efetivamente
   devolver campos reconheciveis.
4. Quando nada e reconhecido, o script agora SALVA o HTML cru da
   resposta em debug_dublin_core/ (so os 5 primeiros casos, pra nao
   encher a pasta) - manda esse arquivo que da pra ajustar o parser
   certinho pro formato real, em vez de ficar adivinhando.
5. Titulo e tipo agora tem um FALLBACK: se o Dublin Core nao trouxer
   nada, o script reaproveita o que o script anterior (coletor) ja
   tinha extraido da pagina do item e salvou em acervo_digital_ifce.csv.
6. O ano agora tambem tenta ser extraido da descricao (que costuma
   terminar com o ano, tipo "..., Fortaleza-CE, 2019") quando o campo
   "date" do Dublin Core vier vazio.
7. O texto do resumo, quando o PDF tem palavras grudadas sem espaco
   (bug comum de extracao de PDFs academicos em 2 colunas / kerning
   apertado), agora tenta automaticamente: (a) pdfplumber com
   x_tolerance menor e (b) PyMuPDF (fitz) como alternativa, se estiver
   instalado - ficando com a extracao que tiver mais espacos (sinal de
   que separou as palavras direito).
8. NOVO - fallback de OCR: alguns PDFs nao tem NENHUMA camada de texto
   (o texto foi "achatado" em curvas/desenho vetorial na exportacao -
   nem pdfplumber nem fitz acham uma letra sequer, nao importa a
   tentativa). Quando isso acontece, o script agora renderiza as
   paginas como imagem e roda OCR (Tesseract, via pytesseract +
   pdf2image) nelas como ultimo recurso. Tenta OCR em portugues
   ('por') primeiro; se o pacote de idioma nao estiver instalado no
   tesseract, cai pra ingles automaticamente (funciona, mas erra mais
   em acentos - ver secao DEPENDENCIAS). O CSV de saida agora tem uma
   coluna extra "resumo_via_ocr" (sim/vazio) pra você saber quais
   resumos vieram de OCR e merecem uma revisao manual mais cuidadosa.
 
SOBRE A SESSAO
-------------------
O endpoint ajxDublinCore.asp parece depender de cookies de sessao (como
um navegador normal teria). Por isso o script usa requests.Session(),
visita a home no inicio, e agora TAMBEM visita a pagina de detalhe de
cada item antes de pedir o Dublin Core dele.
 
Ainda assim, eu nao consegui testar esse endpoint contra o servidor de
verdade (sem acesso a rede aqui de onde eu escrevi isso). RODE COM UM
INTERVALO PEQUENO PRIMEIRO (uns 5-10 codigos) e me manda o que aparecer
no CSV e, se algum campo continuar vazio, os arquivos que aparecerem em
debug_dublin_core/ - com isso da pra fechar o parser rapidinho.
 
PASSO MANUAL IMPORTANTE
---------------------------
Depois que esse script rodar, ABRA o metadados_completos.csv no Excel
ou LibreOffice Calc e REVISE principalmente as colunas "orientador",
"campus" e "resumo". Onde a extracao automatica falhar (ficar vazia ou
capturar lixo), corrija manualmente. Isso e normal - nem toda fonte e
100% padronizada. Preste atencao especial nas linhas onde
"resumo_via_ocr" = "sim": esse resumo veio de OCR (o PDF nao tinha
camada de texto), entao e mais provavel ter erros de acentuacao ou
palavras trocadas do que os resumos extraidos direto do PDF.
 
So depois de revisado esse CSV e que voce deve rodar o proximo script
(2_gerar_saf.py), que usa esse CSV corrigido para montar o pacote do
DSpace.
 
DEPENDENCIAS
------------
pip install requests beautifulsoup4 pdfplumber
pip install pymupdf                    # opcional, so ajuda na extracao do resumo
pip install pdf2image pytesseract      # opcional, so pro fallback de OCR
 
O fallback de OCR tambem precisa de dois programas instalados no
SISTEMA (nao e so pip install):
  - poppler (fornece o "pdftoppm", usado pra renderizar paginas do PDF
    como imagem). No Ubuntu/Debian: sudo apt-get install poppler-utils
  - tesseract (o motor de OCR em si). No Ubuntu/Debian:
    sudo apt-get install tesseract-ocr tesseract-ocr-por
    (o pacote "tesseract-ocr-por" e o dicionario/modelo de PORTUGUES -
    sem ele o script ainda funciona, mas cai pro modelo de ingles e
    erra bem mais em acentos: "matematica" vira "matemética" etc.)
 
Se pdf2image/pytesseract ou os programas do sistema nao estiverem
instalados, o script simplesmente pula o OCR (avisa no terminal) e
segue funcionando normalmente pros PDFs que TEM camada de texto - o
OCR so entra em acao como ultimo recurso.
"""
 
import csv
import os
import re
import time
import unicodedata
import requests
from bs4 import BeautifulSoup
import pdfplumber
 
# ============ CONFIGURACAO ============
CSV_ENTRADA = "acervo_digital_ifce.csv"       # gerado pelo script anterior
CSV_SAIDA = "metadados_completos.csv"
SLEEP_SEGUNDOS = 1.0
 
BASE_URL = "https://biblioteca.ifce.edu.br"
URL_HOME = f"{BASE_URL}/index.asp"             # so pra pegar cookie de sessao
 
# O coletor (script anterior) usa "/mobile" pra pagina de detalhe, e foi
# confirmado que funciona. O endpoint de Dublin Core pode estar tanto
# dentro de "/mobile" quanto na raiz - por isso tentamos os dois, nessa
# ordem, e ficamos com o que responder primeiro com campos reconheciveis.
CANDIDATOS_URL_DUBLIN_CORE = [
    f"{BASE_URL}/mobile/asp/ajxDublinCore.asp",
    f"{BASE_URL}/asp/ajxDublinCore.asp",
]
 
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ColetorAcervoDigital/1.0)"}
 
PASTA_DEBUG = "debug_dublin_core"
MAX_DEBUG_SALVOS = 5
 
PASTA_DEBUG_RESUMO = "debug_resumo"
MAX_DEBUG_RESUMO_SALVOS = 8
 
LIMIAR_RAZAO_ESPACOS = 0.08  # abaixo disso, o texto provavelmente "grudou" as palavras
# ========================================
 
 
# Dicionario de sinonimos: normaliza o rotulo (sem acento, minusculo,
# sem ":") e mapeia pro nome de campo Dublin Core padrao. Cobre tanto
# os nomes "oficiais" em ingles quanto variantes em portugues que o
# Sophia costuma usar na interface.
MAPA_LABELS = {
    # ingles
    "title": "title", "creator": "creator", "contributor": "contributor",
    "subject": "subject", "description": "description", "date": "date",
    "type": "type", "format": "format", "identifier": "identifier",
    "language": "language", "relation": "relation", "publisher": "publisher",
    "source": "source", "coverage": "coverage", "rights": "rights",
    # portugues
    "titulo": "title",
    "autor": "creator", "autores": "creator", "autor(es)": "creator",
    "orientador": "contributor", "orientador(es)": "contributor",
    "orientadores": "contributor", "co-orientador": "contributor",
    "coorientador": "contributor", "coorientador(es)": "contributor",
    "assunto": "subject", "assuntos": "subject",
    "palavra-chave": "subject", "palavras-chave": "subject",
    "palavra chave": "subject", "palavras chave": "subject",
    "descricao": "description", "notas": "description", "resumo": "description",
    "data": "date", "ano": "date", "data de publicacao": "date",
    "tipo": "type", "tipo de material": "type", "tipo do material": "type",
    "formato": "format",
    "identificador": "identifier",
    "idioma": "language", "lingua": "language",
    "relacao": "relation",
    "editora": "publisher", "editor": "publisher",
    "fonte": "source",
    "cobertura": "coverage",
    "direitos": "rights",
}
 
 
def _normalizar_label(texto):
    """Deixa o rotulo em forma canonica pra comparar com o MAPA_LABELS:
    sem acento, minusculo, sem ':' nem espacos nas pontas."""
    texto = texto.strip().rstrip(":").strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()
 
 
def iniciar_sessao():
    """Cria uma sessao e visita a home pra pegar cookies, como um navegador faria."""
    session = requests.Session()
    try:
        session.get(URL_HOME, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"[aviso] nao consegui abrir a home pra pegar sessao: {e}")
    return session
 
 
def _url_detalhe(codigo):
    return (f"{BASE_URL}/mobile/detalhe.asp?idioma=ptbr&acesso=web"
            f"&codigo={codigo}&tipo=1&detalhe=0&busca=3")
 
 
_debug_salvos = 0
 
 
def _salvar_html_debug(codigo, url, conteudo):
    global _debug_salvos
    if _debug_salvos >= MAX_DEBUG_SALVOS:
        return
    os.makedirs(PASTA_DEBUG, exist_ok=True)
    nome = os.path.join(PASTA_DEBUG, f"{codigo}_{_debug_salvos}.html")
    try:
        with open(nome, "wb") as f:
            f.write(conteudo)
        print(f"  [debug] resposta sem campos reconheciveis salva em {nome}")
    except OSError as e:
        print(f"  [aviso] nao consegui salvar debug HTML: {e}")
    _debug_salvos += 1
 
 
_url_dc_que_funcionou = None  # cache: depois que uma URL funcionar, tenta ela primeiro
 
 
def buscar_dublin_core(codigo, session):
    """Visita a pagina de detalhe do item (pra dar contexto de sessao)
    e so entao busca e interpreta os metadados Dublin Core."""
    global _url_dc_que_funcionou
 
    url_detalhe = _url_detalhe(codigo)
    try:
        session.get(url_detalhe, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"  [aviso] nao consegui abrir a pagina de detalhe antes do Dublin Core: {e}")
 
    params = {
        "cod": codigo,
        "tipo": 1,
        "servidor": 1,
        "iBanner": 0,
        "iEscondeMenu": 0,
        "iSomenteLegislacao": 0,
        "iIdioma": 0,
        "campo1": "palavra_chave",
        "valor1": "",
    }
 
    candidatos = list(CANDIDATOS_URL_DUBLIN_CORE)
    if _url_dc_que_funcionou and _url_dc_que_funcionou in candidatos:
        candidatos.remove(_url_dc_que_funcionou)
        candidatos.insert(0, _url_dc_que_funcionou)
 
    headers_req = dict(HEADERS)
    headers_req["Referer"] = url_detalhe
 
    for url in candidatos:
        try:
            resp = session.get(url, params=params, headers=headers_req, timeout=20)
        except requests.RequestException as e:
            print(f"  [aviso] erro ao chamar {url}: {e}")
            continue
 
        if resp.status_code != 200:
            continue
 
        campos = parse_dublin_core(resp.content)
        if campos:
            _url_dc_que_funcionou = url
            return campos
 
        _salvar_html_debug(codigo, url, resp.content)
 
    return {}
 
 
def _parse_ajx_str_final_dublin_core(html_bytes):
    """Formato REAL do endpoint ajxDublinCore.asp (confirmado a partir de
    respostas salvas de verdade): a pagina e um <script> que, dentro de
    window.onload, monta a tabela de metadados como uma STRING JavaScript
    (var str_final = "<table>...</table>";) e injeta isso via innerHTML no
    elemento #dDublinCore da pagina pai (um iframe/frame escondido).
 
    Isso explica por que os outros parsers (meta / tabela / dl / texto
    solto) nao achavam nada: o BeautifulSoup, ao abrir a resposta direto,
    nao encontra nenhuma <tr>/<td> "de verdade" no HTML - elas existem
    apenas como texto dentro da string JS, nunca chegam a virar DOM.
 
    A solucao: achar essa string com regex, desfazer o escaping de string
    JS (aspas e barras escapadas) e SO ENTAO parsear o resultado como HTML
    de verdade, extraindo os pares rotulo/valor das <tr><td> internas -
    que, nesse formato, ja vem com rotulos em ingles (title, creator,
    contributor, subject, description, date, type, format, identifier,
    language, relation, publisher), batendo direto com o MAPA_LABELS.
    """
    texto = html_bytes.decode("utf-8", errors="replace")
 
    m = re.search(r'var\s+str_final\s*=\s*"(.*?)"\s*;', texto, re.DOTALL)
    if not m:
        return {}
 
    html_str = m.group(1)
    # desfaz o escaping de string JS (a pagina usa aspas simples pros
    # atributos HTML, entao normalmente nao ha nada pra desfazer aqui,
    # mas title/descricao podem conter aspas duplas ou barras escapadas)
    html_str = (
        html_str.replace('\\"', '"')
        .replace("\\'", "'")
        .replace("\\/", "/")
        .replace("\\n", " ")
        .replace("\\\\", "\\")
    )
 
    sub_soup = BeautifulSoup(html_str, "html.parser")
    campos = {}
    for tr in sub_soup.find_all("tr"):
        cols = tr.find_all(["td", "th"])
        if len(cols) >= 2:
            label = cols[0].get_text(strip=True)
            valor = cols[1].get_text(" ", strip=True)
            campo = MAPA_LABELS.get(_normalizar_label(label))
            if campo and valor:
                campos.setdefault(campo, []).append(valor)
    return campos
 
 
def _parse_meta_dublin_core(soup):
    """Formato 1: <meta name="DC.title" content="..."> (ou DCTERMS.*, dc:*)."""
    campos = {}
    for meta in soup.find_all("meta"):
        nome = meta.get("name") or meta.get("property") or ""
        conteudo = meta.get("content")
        if not nome or not conteudo:
            continue
        partes = re.split(r"[.:]", nome)
        chave = partes[-1] if partes else nome
        campo = MAPA_LABELS.get(_normalizar_label(chave))
        if campo:
            campos.setdefault(campo, []).append(conteudo.strip())
    return campos
 
 
def _parse_tabela_dublin_core(soup):
    """Formato 2: tabela HTML, rotulo numa celula e valor na outra."""
    campos = {}
    for tr in soup.find_all("tr"):
        cols = tr.find_all(["td", "th"])
        if len(cols) >= 2:
            label = cols[0].get_text(strip=True)
            valor = cols[1].get_text(strip=True)
            campo = MAPA_LABELS.get(_normalizar_label(label))
            if campo and valor:
                campos.setdefault(campo, []).append(valor)
    return campos
 
 
def _parse_dl_dublin_core(soup):
    """Formato 3: lista de definicao <dl><dt>rotulo</dt><dd>valor</dd></dl>,
    comum em paginas que exibem metadados Dublin Core."""
    campos = {}
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            label = dt.get_text(strip=True)
            valor = dd.get_text(strip=True)
            campo = MAPA_LABELS.get(_normalizar_label(label))
            if campo and valor:
                campos.setdefault(campo, []).append(valor)
    return campos
 
 
def _parse_texto_simples_dublin_core(soup):
    """Formato 4 (fallback): texto solto, rotulo numa linha e valor na(s)
    linha(s) seguinte(s) - como costuma aparecer numa aba "Dublin Core"
    renderizada sem tabela."""
    campos = {}
    texto = soup.get_text("\n", strip=True)
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    campo_atual = None
    for linha in linhas:
        # so tratamos a linha como "cabecalho de campo" se ela for curta -
        # um valor comprido (ex: um resumo) nao deve ser confundido com
        # rotulo so por acaso conter uma palavra do mapa.
        campo_normalizado = MAPA_LABELS.get(_normalizar_label(linha)) if len(linha) <= 40 else None
        if campo_normalizado:
            campo_atual = campo_normalizado
            campos.setdefault(campo_atual, [])
        elif campo_atual:
            campos[campo_atual].append(linha)
    return campos
 
 
def parse_dublin_core(html):
    """Tenta interpretar a resposta do endpoint nos formatos mais comuns,
    nessa ordem de prioridade, e fica com o primeiro que reconhecer algo.
    Retorna um dicionario {campo: [valores]} (listas, porque subject,
    format e relation costumam se repetir).
 
    O formato REAL do Sophia (confirmado em respostas salvas de verdade) e
    o "str_final" - uma tabela embutida numa string JS dentro de um
    <script>, entao ele vai primeiro, antes dos parsers que dependem de
    HTML "de verdade" no corpo da resposta.
    """
    campos = _parse_ajx_str_final_dublin_core(html)
    if campos:
        return campos
 
    soup = BeautifulSoup(html, "html.parser")
    for parser_fn in (
        _parse_meta_dublin_core,
        _parse_tabela_dublin_core,
        _parse_dl_dublin_core,
        _parse_texto_simples_dublin_core,
    ):
        campos = parser_fn(soup)
        if campos:
            return campos
    return {}
 
 
CONECTORES_NOME_PROPRIO = {"de", "do", "da", "dos", "das", "e"}
 
 
def extrair_campus_da_descricao(descricoes):
    """Extrai o nome do campus a partir do campo 'description' do Dublin Core.
    Ex: 'TCC (Bacharelado ...) - IFCE/ Campus Fortaleza, Fortaleza-CE, 2019'
    Ex: '... (IFCE) - Campus Limoeiro do Norte como requisito parcial ...'
 
    A versao anterior cortava so em virgula/ponto/ponto-e-virgula depois
    de "Campus", entao quando a frase continuava sem pontuacao logo em
    seguida (ex: '...Campus Limoeiro do Norte COMO requisito parcial...')
    ela capturava um pedaco enorme de lixo junto do nome do campus.
 
    Agora a gente le palavra por palavra depois de "Campus" e so continua
    enquanto a palavra comecar com maiuscula (parte do nome proprio) ou
    for um conector comum em nomes de lugar (de/do/da/dos/das/e) - parando
    no primeiro ponto de pontuacao ou na primeira palavra minuscula que
    nao seja conector.
    """
    texto = " ".join(descricoes)
    m = re.search(r"Campus\s+(.+)", texto)
    if not m:
        return ""
 
    palavras_campus = []
    for palavra in m.group(1).split():
        limpa = palavra.strip(",.;:()")
        if not limpa:
            break
        eh_conector = limpa.lower() in CONECTORES_NOME_PROPRIO
        eh_propria = limpa[0].isupper()
        if not (eh_conector or eh_propria):
            break
        palavras_campus.append(limpa)
        if palavra[-1:] in ",.;:":
            break
 
    # nao deixa terminar com um conector "pendurado" (ex: "Norte do")
    while palavras_campus and palavras_campus[-1].lower() in CONECTORES_NOME_PROPRIO:
        palavras_campus.pop()
 
    return " ".join(palavras_campus)
 
 
def extrair_ano_da_descricao(descricoes):
    """Fallback pro ano quando o campo 'date' do Dublin Core vem vazio -
    a descricao costuma terminar com o ano (ex: '..., Fortaleza-CE, 2019')."""
    texto = " ".join(descricoes)
    padrao = re.search(r"\b(19|20)\d{2}\b", texto)
    return padrao.group(0) if padrao else ""
 
 
def _razao_espacos(texto):
    """Proporcao de espacos em relacao ao total de caracteres - serve como
    indicador de que a extracao 'colou' as palavras (proporcao muito
    baixa). Texto em portugues normal costuma ficar entre ~14% e ~20%."""
    if not texto:
        return 0.0
    return texto.count(" ") / max(len(texto), 1)
 
 
def _extrair_texto_pdfplumber(caminho_pdf, paginas, x_tolerance=3):
    texto = ""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages[:paginas]:
                texto += (page.extract_text(x_tolerance=x_tolerance) or "") + "\n"
    except Exception as e:
        print(f"  [aviso] pdfplumber falhou em {caminho_pdf}: {e}")
    return texto
 
 
def _extrair_texto_fitz(caminho_pdf, paginas):
    """Extracao alternativa com PyMuPDF - so entra em acao se o
    pdfplumber devolver texto com poucos espacos (sintoma de
    'palavrasgrudadas'). Opcional: pip install pymupdf."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""
    texto = ""
    try:
        with fitz.open(caminho_pdf) as doc:
            for i, page in enumerate(doc):
                if i >= paginas:
                    break
                texto += page.get_text() + "\n"
    except Exception as e:
        print(f"  [aviso] PyMuPDF falhou em {caminho_pdf}: {e}")
    return texto
 
 
LIMIAR_CHARS_OCR = 30  # texto (apos pdfplumber/fitz) mais curto que isso = PDF
                       # provavelmente sem camada de texto -> tenta OCR
 
# Lembra qual idioma de OCR funcionou da ultima vez, pra nao ficar
# tentando 'por' de novo em todo PDF depois de descobrir que o pacote
# de idioma portugues nao esta instalado no tesseract deste sistema.
_idioma_ocr = "por"
_aviso_ocr_indisponivel_mostrado = False
 
 
def _extrair_texto_ocr(caminho_pdf, paginas, dpi=300):
    """Ultimo recurso, usado quando pdfplumber e fitz nao acham NENHUM
    texto no PDF. Isso acontece com PDFs que nao tem camada de texto
    de verdade - o texto foi "achatado" em curvas/desenho vetorial na
    exportacao (comum quando o gerador do PDF converte as fontes em
    outline, por exemplo pra nao depender de fontes licenciadas).
 
    Renderiza cada pagina como imagem (via pdf2image/poppler) e roda
    OCR nela com o Tesseract (via pytesseract). Tenta em portugues
    primeiro; se o pacote de idioma 'por' nao estiver instalado no
    tesseract deste sistema, cai pra ingles automaticamente (funciona,
    mas erra mais em palavras acentuadas - ver DEPENDENCIAS no topo do
    arquivo pra instalar o pacote certo)."""
    global _idioma_ocr, _aviso_ocr_indisponivel_mostrado
 
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        if not _aviso_ocr_indisponivel_mostrado:
            print("  [aviso] OCR indisponivel (falta instalar 'pdf2image' e "
                  "'pytesseract' - pip install pdf2image pytesseract). Pulando "
                  "OCR; PDFs sem camada de texto vao ficar com resumo vazio.")
            _aviso_ocr_indisponivel_mostrado = True
        return ""
 
    try:
        imagens = convert_from_path(caminho_pdf, dpi=dpi, first_page=1, last_page=paginas)
    except Exception as e:
        if not _aviso_ocr_indisponivel_mostrado:
            print(f"  [aviso] nao consegui renderizar PDF pra imagem (falta o "
                  f"poppler/pdftoppm no sistema? sudo apt-get install "
                  f"poppler-utils): {e}")
            _aviso_ocr_indisponivel_mostrado = True
        return ""
 
    texto = ""
    for i, imagem in enumerate(imagens):
        trecho = ""
        try:
            trecho = pytesseract.image_to_string(imagem, lang=_idioma_ocr)
        except pytesseract.TesseractError as e:
            if _idioma_ocr != "eng":
                print(f"  [aviso] idioma de OCR '{_idioma_ocr}' indisponivel no "
                      f"tesseract deste sistema ({e}) - usando 'eng' daqui pra "
                      f"frente (menos preciso em acentos). Pra melhor qualidade, "
                      f"instale: sudo apt-get install tesseract-ocr-por")
                _idioma_ocr = "eng"
                try:
                    trecho = pytesseract.image_to_string(imagem, lang=_idioma_ocr)
                except Exception as e2:
                    print(f"  [aviso] OCR falhou na pagina {i + 1}: {e2}")
            else:
                print(f"  [aviso] OCR falhou na pagina {i + 1}: {e}")
        texto += trecho + "\n"
 
    return texto
 
 
def extrair_texto_pdf(caminho_pdf, paginas=3):
    """Le o texto das primeiras paginas do PDF (so usado pra achar o
    resumo). Se o resultado tiver poucos espacos (palavras grudadas),
    tenta alternativas ate achar uma extracao melhor. Se, mesmo assim,
    nao achar nenhum texto de verdade (PDF sem camada de texto), tenta
    OCR como ultimo recurso.
 
    Devolve uma tupla (texto, via_ocr) - via_ocr indica se o texto
    devolvido veio do OCR (util pra sinalizar no CSV que aquele resumo
    merece uma revisao manual mais cuidadosa, ja que OCR erra mais que
    texto extraido direto do PDF)."""
    texto = _extrair_texto_pdfplumber(caminho_pdf, paginas)
 
    if _razao_espacos(texto) < LIMIAR_RAZAO_ESPACOS:
        texto_alt = _extrair_texto_pdfplumber(caminho_pdf, paginas, x_tolerance=1)
        if _razao_espacos(texto_alt) > _razao_espacos(texto):
            texto = texto_alt
 
    if _razao_espacos(texto) < LIMIAR_RAZAO_ESPACOS:
        texto_fitz = _extrair_texto_fitz(caminho_pdf, paginas)
        if _razao_espacos(texto_fitz) > _razao_espacos(texto):
            texto = texto_fitz
 
    if len(texto.strip()) >= LIMIAR_CHARS_OCR:
        return texto, False
 
    # Nada funcionou ate aqui - PDF provavelmente sem camada de texto.
    print(f"  [info] {os.path.basename(caminho_pdf)}: sem texto extraivel nas "
          f"primeiras {paginas} paginas (PDF sem camada de texto) - tentando OCR...")
    texto_ocr = _extrair_texto_ocr(caminho_pdf, paginas)
    if len(texto_ocr.strip()) > len(texto.strip()):
        return texto_ocr, bool(texto_ocr.strip())
 
    return texto, False
 
 
_debug_resumo_salvos = 0
 
 
def _salvar_debug_resumo(codigo, texto):
    """Quando nao acha resumo, salva o texto cru extraido do PDF pra
    facilitar o ajuste do parser depois (mesma ideia do debug do
    Dublin Core: so os primeiros casos, pra nao encher a pasta)."""
    global _debug_resumo_salvos
    if _debug_resumo_salvos >= MAX_DEBUG_RESUMO_SALVOS:
        return
    os.makedirs(PASTA_DEBUG_RESUMO, exist_ok=True)
    nome = os.path.join(PASTA_DEBUG_RESUMO, f"{codigo}.txt")
    try:
        with open(nome, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"  [debug] resumo nao encontrado - texto do PDF salvo em {nome}")
    except OSError as e:
        print(f"  [aviso] nao consegui salvar debug de resumo: {e}")
    _debug_resumo_salvos += 1
 
 
def obter_resumo_do_pdf(caminho_pdf, codigo):
    """Tenta achar o resumo nas primeiras paginas, alargando a busca em
    etapas (3 -> 8 -> 20 paginas) se nao achar de primeira. Dissertacoes
    e teses costumam ter capa, folha de rosto, ficha catalografica,
    folha de aprovacao, dedicatoria, agradecimentos, epigrafe e as vezes
    ate uma lista de ilustracoes antes do resumo - isso pode empurrar o
    resumo bem alem da pagina 8 (ja vi resumo so na pagina 9-12). Pra
    PDFs sem camada de texto, mais paginas tambem significa mais paginas
    pra OCR tentar. Se mesmo assim nao achar, guarda o texto extraido
    em debug_resumo/ pra dar pra ajustar o parser.
 
    Devolve (resumo, via_ocr)."""
    ultimo_texto, ultimo_via_ocr = "", False
    for paginas in (3, 8, 20):
        texto, via_ocr = extrair_texto_pdf(caminho_pdf, paginas=paginas)
        resumo = extrair_resumo(texto)
        if resumo:
            return resumo, via_ocr
        ultimo_texto, ultimo_via_ocr = texto, via_ocr
 
    _salvar_debug_resumo(codigo, ultimo_texto)
    return "", False
 
 
# Cabecalhos que sinalizam o FIM do resumo (o proximo elemento textual
# da monografia). Cada um e testado como token "solto" (ver
# _stop_pattern_resumo), entao nao precisam bater com a linha inteira.
CABECALHOS_FIM_RESUMO = [
    r"ABSTRACT",
    r"R[EÉ]SUM[EÉ]",              # resumo em frances, aparece as vezes
    r"PALAVRAS[-\s]?CHAVE",
    r"KEY\s*[-\s]?WORDS",
    r"SUM[AÁ]RIO",
    r"LISTA\s+DE\s+FIGURAS",
    r"LISTA\s+DE\s+TABELAS",
    r"LISTA\s+DE\s+QUADROS",
    r"LISTA\s+DE\s+GR[AÁ]FICOS",
    r"LISTA\s+DE\s+ABREVIATURAS",
    r"LISTA\s+DE\s+SIGLAS",
    r"SUMMARY",
    r"1\s*[\.\)]?\s*INTRODU[CÇ][AÃ]O",
    r"INTRODU[CÇ][AÃ]O",
]
 
# Variacoes do proprio rotulo "resumo" que podem aparecer no PDF.
# Inclui a grafia "RESUMO" com espacos entre letras, comum quando o
# layout usa letter-spacing (a extracao de texto insere espaco entre
# cada letra: "R E S U M O").
PADRAO_ROTULO_RESUMO = r"R\s*E\s*S\s*U\s*M\s*O(?!\s*:?\s*EXPANDIDO)"
 
 
def _juntar_hifenizacao(texto):
    """Palavras quebradas no fim da linha por hifenizacao (comum em PDF
    justificado) atrapalham a leitura e podem confundir o filtro de fim
    de secao. Junta "pales-\ntra" -> "palestra"."""
    return re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
 
 
def _candidatos_resumo(texto):
    """Acha TODAS as ocorrencias do rotulo 'resumo' no texto e devolve,
    pra cada uma, o trecho que vem depois (ate o proximo cabecalho
    conhecido ou um limite de tamanho). Pode haver mais de uma
    ocorrencia (ex: a palavra aparece no SUMARIO/indice antes de
    aparecer de verdade como titulo de secao) - por isso escolhemos
    depois, no chamador, a que parecer mais um resumo de verdade."""
    candidatos = []
    fim_regex = "|".join(CABECALHOS_FIM_RESUMO)
 
    for m in re.finditer(PADRAO_ROTULO_RESUMO, texto, re.IGNORECASE):
        inicio = m.end()
        # pula pontuacao/2-pontos/travessao logo apos o rotulo, e
        # tambem uma eventual palavra "expandido"/numero de pagina
        trecho_restante = texto[inicio:inicio + 4000]
 
        # se, colado ao rotulo, vier so um numero (tipico de "RESUMO ... 7"
        # de sumario/indice), pula esse candidato - nao e o resumo de verdade
        colado = trecho_restante[:6].strip()
        if re.match(r"^[.\s]*\d{1,3}\s*$", colado) or re.match(r"^\d{1,3}\b", colado):
            continue
 
        # acha onde comeca o proximo cabecalho dentro do trecho
        m_fim = re.search(r"\b(?:" + fim_regex + r")\b", trecho_restante, re.IGNORECASE)
        bruto = trecho_restante[:m_fim.start()] if m_fim else trecho_restante
 
        bruto = bruto.strip(" \n:.-\t")
        candidatos.append(bruto)
 
    return candidatos
 
 
def extrair_resumo(texto):
    """Tenta achar o texto do resumo no texto extraido do PDF.
 
    A versao anterior so reconhecia o formato "RESUMO\\n<texto>", ou
    seja, exigia uma quebra de linha logo apos a palavra RESUMO. Isso
    falha em varios casos comuns:
      - "RESUMO" e o inicio do paragrafo ficam na MESMA linha depois da
        extracao (ex: "RESUMO Este trabalho apresenta...").
      - Ha um separador tipo ":" ou "-" entre o rotulo e o texto.
      - A palavra "Resumo" aparece antes no SUMARIO/indice do TCC (com
        um numero de pagina do lado), e o regex antigo as vezes batia
        nesse trecho errado (ou nao batia em lugar nenhum, se a linha
        seguinte no indice for outro item de sumario).
      - PDFs com layout de "letter-spacing" no titulo da secao, onde o
        texto extraido vem como "R E S U M O".
      - O corte de fim de secao ("\\n[A-Z]{4,}\\n") cortava resumos que
        continham qualquer palavra em caixa alta isolada (siglas, por
        exemplo YOLO, UFC, IFCE) em uma linha propria.
 
    Agora a funcao: (a) junta palavras hifenizadas quebradas em linha,
    (b) acha TODAS as ocorrencias de "resumo" no texto, nao so a
    primeira, (c) descarta ocorrencias que sao claramente entradas de
    sumario/indice (rotulo colado a um numero de pagina), (d) corta o
    fim usando uma lista de cabecalhos de secao conhecidos (nao
    qualquer linha maiuscula), e (e) fica com o candidato mais longo -
    o resumo de verdade costuma ser bem mais longo que uma linha de
    sumario ou uma citacao incidental da palavra "resumo".
    """
    if not texto:
        return ""
 
    texto = _juntar_hifenizacao(texto)
 
    candidatos = _candidatos_resumo(texto)
    if not candidatos:
        return ""
 
    melhor = max(candidatos, key=len)
    melhor = re.sub(r"\s+", " ", melhor).strip()
 
    # candidato "resumo" com menos de ~80 caracteres quase sempre e
    # ruido (rotulo pego sem o corpo do texto do lado) - nesse caso e
    # melhor devolver vazio (e deixar pra revisao manual) do que
    # devolver lixo curto que parece preenchido mas nao serve.
    if len(melhor) < 80:
        return ""
 
    return melhor[:2500]  # limite de seguranca
 
 
def main():
    if not os.path.exists(CSV_ENTRADA):
        print(f"Nao encontrei {CSV_ENTRADA}. Rode primeiro o script de coleta.")
        return
 
    session = iniciar_sessao()
 
    with open(CSV_ENTRADA, newline="", encoding="utf-8") as f_in:
        linhas = [row for row in csv.DictReader(f_in) if row.get("arquivo_local")]
 
    print(f"{len(linhas)} itens com PDF encontrados para processar.")
 
    with open(CSV_SAIDA, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "codigo", "titulo", "autor", "orientador", "campus", "tipo", "ano",
            "assuntos", "resumo", "resumo_via_ocr", "arquivo_local"
        ])
 
        for row in linhas:
            codigo = row["codigo"]
            arquivo_local = row["arquivo_local"]
            print(f"[{codigo}] processando...")
 
            try:
                dc = buscar_dublin_core(codigo, session)
            except requests.RequestException as e:
                print(f"  erro ao buscar Dublin Core: {e}")
                dc = {}
            except Exception as e:
                print(f"  erro inesperado ao buscar Dublin Core: {e}")
                dc = {}
 
            if not dc:
                print(f"  [aviso] nenhum metadado Dublin Core reconhecido pro codigo {codigo}.")
 
            # titulo/tipo: se o Dublin Core nao trouxer nada, reaproveita o
            # que o script de coleta ja tinha extraido da pagina do item.
            titulo = (dc.get("title", [""])[0] if dc.get("title") else "") or row.get("titulo", "")
            tipo = (dc.get("type", [""])[0] if dc.get("type") else "") or row.get("tipo", "")
 
            autor = "; ".join(dc.get("creator", []))
            orientador = "; ".join(dc.get("contributor", []))
            assuntos = "; ".join(dc.get("subject", []))
            campus = extrair_campus_da_descricao(dc.get("description", []))
            ano = (dc.get("date", [""])[0] if dc.get("date") else "") or \
                extrair_ano_da_descricao(dc.get("description", []))
 
            resumo = ""
            via_ocr = False
            try:
                if os.path.exists(arquivo_local):
                    resumo, via_ocr = obter_resumo_do_pdf(arquivo_local, codigo)
            except Exception as e:
                print(f"  [aviso] falha ao processar o PDF {arquivo_local}: {e}")
 
            writer.writerow([
                codigo, titulo, autor, orientador, campus, tipo, ano,
                assuntos, resumo, ("sim" if via_ocr else ""), arquivo_local,
            ])
            f_out.flush()
            time.sleep(SLEEP_SEGUNDOS)
 
    print(f"\nConcluido! Revise o arquivo: {CSV_SAIDA}")
    print("Abra no Excel/LibreOffice e corrija onde a extracao automatica falhar.")
    if _debug_salvos:
        print(f"Obs: {_debug_salvos} resposta(s) sem metadados reconheciveis foram "
              f"salvas em {PASTA_DEBUG}/ - me manda esses arquivos se ainda sobrar "
              f"campo vazio que nao devia.")
    if _debug_resumo_salvos:
        print(f"Obs: {_debug_resumo_salvos} item(ns) sem resumo reconhecivel tiveram "
              f"o texto extraido do PDF salvo em {PASTA_DEBUG_RESUMO}/ - me manda "
              f"esses arquivos se ainda sobrar resumo vazio que nao devia.")
 
 
if __name__ == "__main__":
    main()

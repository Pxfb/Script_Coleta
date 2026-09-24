Coleta de Teses e Dissertações – Biblioteca Sophia (IFCE)

Dois scripts em Python para coletar os PDFs e extrair os metadados de Teses e Dissertações da Biblioteca Sophia do IFCE.

O fluxo tem duas etapas que rodam em sequência: primeiro baixa os PDFs, depois extrai os metadados e o resumo de cada um.

XML MARC ──► [Etapa 0: coletar] ──► pdfs/ + acervo_digital_ifce.csv
                                            │
                                            ▼
                          [Etapa 1: extrair metadados]
                                            │
                                            ▼
                              metadados_completos.csv
                                            │
                                  (revisão manual)
Estrutura
Arquivo	Função
coletar_sophia_ifce_lista.py	Etapa 0 – lê os códigos do XML MARC, verifica se cada item tem PDF, filtra por tipo e baixa os PDFs
1_extrair_metadados.py	Etapa 1 – busca os metadados Dublin Core no Sophia e extrai o resumo de cada PDF

Ajuste os nomes acima para os nomes reais dos seus arquivos.

Dependências

Obrigatórias:

bash
pip install requests beautifulsoup4 pdfplumber

Opcionais (melhoram a extração do resumo):

bash
pip install pymupdf                 # alternativa quando o pdfplumber "gruda" as palavras
pip install pdf2image pytesseract   # fallback de OCR para PDFs sem camada de texto

O OCR também precisa de programas instalados no sistema (não basta o pip):

bash
sudo apt-get install poppler-utils                    # fornece o pdftoppm
sudo apt-get install tesseract-ocr tesseract-ocr-por  # motor de OCR + modelo em português

Sem o tesseract-ocr-por, o script cai automaticamente para o modelo em inglês, que erra mais em palavras acentuadas. Se pdf2image, pytesseract ou os programas do sistema não estiverem instalados, o OCR é pulado com um aviso e os PDFs que têm camada de texto continuam sendo processados normalmente.

Etapa 0 – Coletar os PDFs

Script: coletar_sophia_ifce_lista.py

O que faz
Lê o arquivo MARC XML exportado do Sophia e extrai o campo de controle 001 de cada <record>. Esse é o mesmo código usado na URL detalhe.asp?codigo=N do site (zeros à esquerda são removidos).
Para cada código, abre a página de detalhe e procura o link de download (download.asp).
Filtra pelo tipo do material (campo "Inf. publicação"), mantendo só o que estiver em TIPOS_DESEJADOS.
Baixa o PDF para pdfs/<codigo>.pdf, validando que o conteúdo começa com %PDF.
Registra tudo em acervo_digital_ifce.csv.
Configuração

Edite o bloco CONFIGURAÇÃO no topo do script:

Variável	Padrão	Descrição
XML_ENTRADA	Arquivo Marc Teses Dissertações.xml	Caminho do MARC XML
LIMITE_TESTE	None	Processa só os N primeiros códigos (ex.: 5). None = todos
SLEEP_SEGUNDOS	1.0	Pausa entre requisições
PASTA_PDFS	pdfs	Pasta de destino dos PDFs
ARQUIVO_CSV	acervo_digital_ifce.csv	CSV de saída
TIPOS_DESEJADOS	["Tese", "Dissertação"]	Tipos que serão baixados (sem diferenciar maiúsculas/minúsculas)
Como rodar
bash
python coletar_sophia_ifce_lista.py

Teste primeiro com LIMITE_TESTE = 5.

Saída: acervo_digital_ifce.csv

Colunas: codigo, titulo, autor, tipo, assuntos, arquivo_local, url_pdf

Itens sem PDF são registrados só com o código (demais colunas vazias).
Itens com PDF mas fora do filtro recebem (fora do filtro) na coluna tipo.
autor e assuntos ficam vazios aqui; são preenchidos na Etapa 1.
Retomável

Se o script for interrompido, é só rodar de novo: ele lê o CSV existente e pula os códigos já processados.

Etapa 1 – Extrair metadados completos

Script: 1_extrair_metadados.py

O que faz

Para cada item de acervo_digital_ifce.csv que tem PDF baixado:

Metadados Dublin Core. Visita a página de detalhe do item (para criar o contexto de sessão no servidor) e chama o endpoint ajxDublinCore.asp, com Referer apontando para essa página. Extrai título, autor(es), orientador (contributor), assuntos, tipo, ano e descrição. O script tenta duas variantes de URL do endpoint (/mobile/asp/... e /asp/...) e guarda em cache a que funcionou.
Campus e ano. O campus é extraído da descrição (ex.: IFCE/ Campus Fortaleza, Fortaleza-CE, 2019 → Fortaleza). O ano usa o campo date e, se ele estiver vazio, cai para o ano encontrado na descrição.
Resumo. Lê o texto das primeiras páginas do PDF e procura o resumo, ampliando a busca em etapas (3 → 8 → 20 páginas).
Fallbacks de título e tipo. Se o Dublin Core não trouxer esses campos, reaproveita os valores do CSV da Etapa 0.
Como o parser lê o Dublin Core

O Sophia devolve os metadados como uma string JavaScript (var str_final = "<table>...</table>";) dentro de um <script>, e não como HTML "de verdade". Por isso o parser primeiro extrai e desfaz o escaping dessa string e só então lê as linhas <tr><td>. Se esse formato não for reconhecido, ele tenta, nesta ordem: tags <meta name="DC.*">, tabela HTML, lista <dl>/<dt>/<dd> e texto solto. Os rótulos em português e em inglês são normalizados por um dicionário de sinônimos (MAPA_LABELS).

Como o resumo é extraído
Extração de texto em cascata: pdfplumber → pdfplumber com x_tolerance=1 → PyMuPDF (fitz). A escolha se baseia na proporção de espaços no texto (LIMIAR_RAZAO_ESPACOS = 0.08); proporção baixa indica palavras coladas.
OCR como último recurso: se o PDF não tiver camada de texto (menos de LIMIAR_CHARS_OCR = 30 caracteres), as páginas são renderizadas como imagem e passam pelo Tesseract (primeiro em português, depois em inglês).
Localização do resumo: junta palavras hifenizadas, encontra todas as ocorrências de "RESUMO" (inclusive R E S U M O), descarta entradas de sumário (rótulo seguido de número de página), corta no próximo cabeçalho conhecido (ABSTRACT, PALAVRAS-CHAVE, SUMÁRIO, INTRODUÇÃO etc.) e escolhe o candidato mais longo.
Resumos com menos de 80 caracteres são descartados (quase sempre ruído), e o resultado é limitado a 2500 caracteres.
Configuração
Variável	Padrão	Descrição
CSV_ENTRADA	acervo_digital_ifce.csv	CSV gerado na Etapa 0
CSV_SAIDA	metadados_completos.csv	CSV de saída
SLEEP_SEGUNDOS	1.0	Pausa entre itens
PASTA_DEBUG / MAX_DEBUG_SALVOS	debug_dublin_core / 5	HTML cru salvo quando nenhum campo é reconhecido
PASTA_DEBUG_RESUMO / MAX_DEBUG_RESUMO_SALVOS	debug_resumo / 8	Texto do PDF salvo quando o resumo não é encontrado
Como rodar
bash
python 1_extrair_metadados.py

O script depende do CSV e da pasta pdfs/ da Etapa 0, no mesmo diretório. Vale testar com poucos itens antes (por exemplo, usando LIMITE_TESTE na Etapa 0).

Saída: metadados_completos.csv

Colunas: codigo, titulo, autor, orientador, campus, tipo, ano, assuntos, resumo, resumo_via_ocr, arquivo_local

Campos com vários valores (autores, orientadores, assuntos) são separados por ; .
resumo_via_ocr recebe sim quando o resumo veio de OCR, o que aumenta a chance de erros de acentuação ou palavras trocadas.
Pastas de debug
debug_dublin_core/: respostas do endpoint sem campos reconhecidos (só as primeiras). Servem para ajustar o parser ao formato real.
debug_resumo/: texto extraído dos PDFs em que nenhum resumo foi encontrado.
Revisão manual (passo obrigatório)

Depois que a Etapa 1 terminar, abra metadados_completos.csv no Excel ou LibreOffice Calc e revise principalmente:

orientador
campus
resumo, com atenção redobrada às linhas com resumo_via_ocr = sim

Corrija o que estiver vazio ou com lixo. Nem toda fonte é 100% padronizada, então isso é esperado.

Uso responsável
As pausas entre requisições (SLEEP_SEGUNDOS) existem para não sobrecarregar o servidor da biblioteca. Evite removê-las.
Os scripts acessam apenas PDFs de acesso público, o equivalente a navegar e baixar manualmente, mas de forma automatizada. Respeite os termos de uso da biblioteca.
Solução de problemas
Sintoma	Provável causa / o que fazer
Não encontrei <arquivo>.xml	Ajuste XML_ENTRADA na Etapa 0
Campos do Dublin Core vazios	Veja os arquivos em debug_dublin_core/ e ajuste o parser
Resumo vazio	Veja os arquivos em debug_resumo/; o resumo pode estar além da página 20 ou fora do padrão
Aviso "OCR indisponível"	Instale pdf2image/pytesseract e os programas poppler-utils e tesseract-ocr
Acentos errados no OCR	Instale tesseract-ocr-por
Interrompeu no meio da Etapa 0	Rode de novo; ele retoma de onde parou
Interrompeu no meio da Etapa 1	O CSV de saída é reescrito a cada execução, então rode de novo do início

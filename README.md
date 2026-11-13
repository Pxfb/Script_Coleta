# SophiaFluxo

Atualizador incremental de acervos Sophia, com coleta de PDFs, extração de metadados e geração opcional de SAF em lotes.

**Três etapas independentes. Um comando. Histórico persistente.**

## Instalação e primeiro uso

Requer Python 3.12 e internet para instalar as dependências e consultar o catálogo. Extraia a distribuição ou clone o repositório.

1. Copie `config.exemplo.json` para `config.json`.
2. Troque `url_base` pelo endereço real do catálogo e configure `base` com seu CSV histórico, se houver.
3. Escolha uma pasta `saida` persistente e execute, no Windows:

```bat
executar.bat --saf --lote-mb 95 --lote-itens 100
```

O comando prepara `.venv` quando necessário e executa todas as etapas. Linux/macOS:

```sh
sh executar.sh --saf --lote-mb 95 --lote-itens 100
```

Sem base histórica, todos os itens elegíveis serão candidatos na primeira execução. A URL de exemplo é fictícia. Nenhum dado do IFCE é distribuído neste repositório.

## Como funciona

| Arquivo | Responsabilidade |
|---|---|
| `01_verificar.py` | Compara o catálogo com a base e o controle; produz a lista de pendentes. |
| `02_coletar.py` | Lê códigos MARC 001, consulta detalhes e baixa PDFs válidos. |
| `03_extrair.py` | Extrai Dublin Core e resumo; opcionalmente gera SAF. |
| `executar.py` | Coordena as etapas, relatórios e controle incremental. |
| `instalar.py` | Instala as bibliotecas de todas as etapas em `.venv`. |
| `sophia/` | Implementação compartilhada, incluindo controle, parsers e lotes. |
| `config.exemplo.json` | Modelo de configuração; a cópia pessoal `config.json` não vai para o Git. |

Repita o mesmo comando para atualizar. O controle em `saida/controle.json` evita repetir itens concluídos. Falhas continuam pendentes; PDFs válidos e metadados concluídos são reaproveitados. Preserve toda a pasta de saída, inclusive ao mudar de máquina.

O programa distingue **metadados concluídos**, **SAF gerado** e **cadastro confirmado**. Não importa arquivos no DSpace automaticamente. Após uma importação confirmada, um CSV com coluna `codigo` pode atualizar o estado:

```bat
executar.bat --confirmar-cadastro "C:\Dados\importados.csv"
```

## Configuração e opções

Todas as opções estão em `config.exemplo.json`. Caminhos do JSON são relativos à pasta desse JSON; caminhos da linha de comando são relativos ao terminal. Use aspas em caminhos com espaços. `tipos` relaciona os códigos de material aos nomes usados pelo catálogo.

```bat
executar.bat --help
executar.bat --xml "C:\Dados\lista.xml" --saf
executar.bat --base "C:\Dados\base.csv" --no-saf
executar.bat --selecao recentes --desde 2026-11-01 --saf
executar.bat --limite 5 --saf
```

O padrão é buscar todos os pendentes, sem corte por data. `--xml` substitui a consulta inicial por uma lista própria, com ou sem namespace MARC. `--refazer` reprocessa a seleção; use uma lista restrita se necessário. Alterações em itens já concluídos não são descobertas automaticamente.

Para executar separadamente, após instalar:

```bat
.venv\Scripts\python.exe 01_verificar.py
.venv\Scripts\python.exe 02_coletar.py --xml "lista.xml"
.venv\Scripts\python.exe 03_extrair.py --csv "coleta.csv" --saf
```

No Linux/macOS, use `.venv/bin/python`. Os caminhos dos arquivos produzidos aparecem no terminal.

## SAF e lotes

O motor padrão é Python. Cada item inclui PDF, `contents` e XML de metadados. O mapeamento entre colunas e campos é configurável em `saf_mapeamento`.

- `--lote-mb 95`: até 95 MiB por ZIP comprimido, conferidos no arquivo final.
- `--lote-itens 100`: até 100 itens por lote.
- Ambos podem ser combinados; nenhum deles divide um item entre dois ZIPs.
- Sem limites, gera um único ZIP. Um item que sozinho exceda o teto provoca erro explícito.
- `saf/lotes.json` informa tamanhos e conteúdo dos lotes.

Para usar metadados revisados sem nova consulta ao catálogo:

```bat
.venv\Scripts\python.exe 03_extrair.py --csv "metadados_revisados.csv" --somente-saf --lote-mb 95
```

O CSV precisa de `codigo`, `arquivo_local` e das colunas mapeadas. Caminhos dos PDFs são relativos ao CSV ou absolutos. Valores múltiplos usam `||` por padrão. Campos obrigatórios padrão: título, autor e ano. O repositório de destino pode exigir outros campos.

O motor Java é opcional: configure `safbuilder_jar` com um JAR obtido separadamente, instale Java e use `--motor-saf java`. O código Java não é redistribuído nesta edição pública. O gerador Python não depende dele.

## OCR, relatórios e falhas

`instalar.bat --ocr` prepara o Tesseract nos sistemas suportados; `--ocr` habilita seu uso. A instalação de programas do sistema pode exigir privilégios. OCR não precisa de Poppler. O idioma configurado deve estar instalado.

Cada execução produz `relatorio.html`, JSON e log. Código `0`: concluído/sem novidades; `1`: falha; `2`: resultado parcial/revisão; `130`: interrupção. `--permitir-incompletos` permite continuar com itens elegíveis; não admite PDF inválido ou título vazio.

Não há perguntas intermediárias na coleta. Há bloqueio contra execuções concorrentes na mesma saída. Não apague um bloqueio enquanto outro processo estiver ativo.

## Limites conhecidos

- Compatível com a estrutura Sophia dos scripts de origem; outros layouts podem exigir adaptação.
- Baixa o primeiro link digital do item; múltiplos links geram aviso.
- Extração automática não substitui revisão catalográfica.
- SAF gerado não comprova cadastro no destino.
- O núcleo Python foi validado em Linux; o workflow foi preparado para validar os três sistemas quando executado no GitHub. O motor Java e a importação DSpace não foram testados nesta entrega.

## Desenvolvimento e publicação

A suíte pública usa dados sintéticos e HTTP local, sem depender de um catálogo externo:

```sh
python -m unittest discover -s tests -v
```

Use o Python de `.venv` após instalar. A suíte pública tem 47 testes; duas verificações dependentes das capturas institucionais foram retiradas da distribuição pública.

- [Publicar e distribuir](docs/PUBLICAR.md)
- [Próximas funcionalidades](docs/ROADMAP.md)
- [Contribuir](CONTRIBUTING.md)
- [Autoria e licença](AVISOS_DE_AUTORIA.md)

Não há licença open source atribuída automaticamente. O responsável deve definir a licença e registrar os créditos antes de anunciar o projeto como open source.


### Itens sem link para PDF

Quando a coleta reconhece a página do item, mas não encontra o link de download esperado no Sophia, ela guarda o estado `sem_pdf` em `saida/coleta/`. Nas próximas execuções com a mesma saída, esses registros ficam fora da fila antes de aplicar `--limite`. A busca geral ainda pode listá-los no catálogo. Os relatórios mostram quantos itens foram ignorados por esse motivo. Registros `sem_pdf` de versões anteriores são reaproveitados.

Falhas de rede, páginas de detalhe não reconhecidas e PDFs inválidos continuam pendentes. Se um PDF for disponibilizado depois ou se mudar o formato dos links do catálogo, rode `executar.bat --xml "lista.xml" --refazer --saf` com uma lista MARC restrita aos códigos que deseja rever. Use a mesma pasta de saída.

## Interface gráfica renovada

Abra abrir_interface.bat no Windows. Use Configurar projeto para escolher a URL do catálogo, o CSV de base e a pasta persistente de saída. A edição pública cria config.json a partir do modelo ao salvar pela primeira vez.

Os cartões contam registros da lista carregada, ausentes da base, itens ainda a processar para SAF e casos já registrados sem PDF. Esses números não comprovam que cada candidato tem PDF. A coleta faz essa validação. Um registro pode estar ausente da base e já ter SAF gerado no histórico.

Há pesquisa por código, título ou situação, ordenação crescente pelos cabeçalhos, detalhes por duplo clique, barra de atividade, acesso ao relatório e recuperação dos ZIPs anteriores. A data inicial se aplica à aba Novas aquisições. Acervo geral consulta os ausentes da base, com o mesmo controle incremental.

A identidade do aplicativo fica em assets/marca.json. Altere nome e o nome do arquivo de logo para adaptar a instituição. Coloque a imagem em assets. A edição de pesquisa inclui as mesmas funções, sem os dados e a marca do IFCE.

A validação automatizada cobre as contagens e a ordenação, além do núcleo de processamento. O teste visual foi bloqueado por falta de foco no ambiente gráfico disponível. As janelas e a instalação devem ser verificadas em Windows.

# beam_calculator

Programa desktop para o dimensionamento de vigas de concreto armado de um
pavimento tipo segundo a ABNT NBR 6118. Você desenha a planta do pavimento
(pilares, vigas contínuas e lajes maciças) e o programa:

- distribui as cargas das lajes para as vigas (cargas da ABNT NBR 6120);
- pré-dimensiona lajes e vigas e verifica as flechas de lajes e vigas;
- analisa cada viga contínua e dimensiona as armaduras longitudinais, os
  estribos e, nas vigas com mais de 60 cm de altura, a armadura de pele, com
  ancoragem, emendas por traspasse e barras de apoio;
- detalha as barras e calcula os quantitativos de aço, concreto e fôrma;
- orça o aço (SINAPI, 10/2026) e o concreto (preço informado pelo usuário) das
  vigas, em valores líquidos, com exportação em PDF;
- exporta os desenhos das vigas (PDF e DXF) e o relatório de cálculo (PDF), e
  grava um memorial de cálculo a cada execução.

Também há uma calculadora de viga contínua isolada, fora da planta. As vigas
dela podem ser salvas e abertas em arquivos `.beam.yaml`, junto com as
configurações do projeto.

**Idioma:** por enquanto, a interface, os relatórios e os desenhos estão
disponíveis **somente em português (pt-BR)**.

> [!WARNING]
> **Aviso de responsabilidade técnica.** O beam_calculator é um trabalho
> acadêmico (Trabalho de Conclusão de Curso, UFRGS). Seus resultados não
> substituem a análise, o julgamento e a responsabilidade de um engenheiro
> habilitado, que deve conferir cada resultado antes de usá-lo num projeto real.

## Capturas de tela

<!-- TODO captura: janela principal com uma planta → resources/screenshots/main-window.png -->
<!-- TODO captura: janela de resultados da viga → resources/screenshots/beam-results.png -->
<!-- TODO captura: desenho de detalhamento da viga → resources/screenshots/beam-drawing.png -->

*Capturas de tela em breve.*

## Instalação

Os instaladores prontos para Windows e Linux são publicados na página
[Releases](https://github.com/arturkcorr3a/beam_calculator/releases); não é
preciso instalar Python. O passo a passo está em [INSTALACAO.md](INSTALACAO.md).

## Pavimentos de exemplo

O programa vem com pavimentos de exemplo e um modelo comentado, na pasta
`exemplos`, ao lado do programa (`resources/examples/` neste repositório). Abra
um deles em **Arquivo → Abrir exemplo…**: ele abre como projeto sem título, então
**Salvar** pergunta onde gravar a sua cópia e o exemplo não é alterado.

- `residencial.pavement.yaml`: pavimento residencial com 21 pilares e 8 lajes;
- `laje_rebaixada.pavement.yaml`: 8 pilares e 3 lajes, uma delas rebaixada;
- `template.pavement.yaml`: um pavimento pequeno com cada campo explicado (significado,
  unidade e valores aceitos), para começar um projeto editando o arquivo à mão;
- `template.beam.yaml`: o mesmo para a calculadora de viga isolada, uma viga de
  dois vãos com cada campo explicado. Abra-o pelo botão **Abrir…** da
  calculadora (ele substitui as configurações do projeto pelas do arquivo).

Os arquivos de projeto são texto YAML e podem ser editados em qualquer editor
de texto.

## Executar a partir do código-fonte

Requisitos: **Python 3.14**, no Windows ou no Linux.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pavement_ui
```

## Limitações conhecidas

<!-- TODO atualizar as limitações conhecidas antes da versão final -->

- **Só pavimento tipo.** Um pavimento por vez; os pilares são apoios das vigas
  e não são dimensionados.
- **Só lajes maciças.** As lajes são pré-dimensionadas, carregadas e
  verificadas quanto à flecha; a armadura delas não é dimensionada.
- **Vigas retangulares.** A contribuição da laje como mesa (viga T) não é
  considerada, e os momentos fletores não são redistribuídos.
- **Estado-limite último na flexão e no cisalhamento**, só com combinações
  normais (ABNT NBR 6118, Tabela 11.1). Torção e abertura de fissuras (ELS-W)
  não são verificadas.
- **Armadura de pele até a face dos pilares.** Vigas com mais de 60 cm de
  altura recebem a armadura de pele mínima de cada vão (ABNT NBR 6118,
  17.3.5.2.3), detalhada, desenhada e contada nos quantitativos, com a marca
  "(PELE)". As barras de cada vão ficam só no vão livre, de face a face dos
  pilares, sem comprimento de ancoragem nos apoios.
- **A flecha (ELS-DEF)** é verificada só contra o limite de aceitabilidade
  sensorial visual, l/250.
- **Um aço e uma classe de concreto por projeto**, só armadura passiva (sem
  protensão).
- **Só cargas de edificações**: sem cargas de veículos.

## Desenvolvimento

O motor de cálculo fica em `src/` e a interface PySide6 em `pavement_ui/`. As
convenções de código e documentação estão no [AGENTS.md](AGENTS.md) (em
inglês); leia o [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir uma issue ou
um pull request. Como as versões são numeradas e publicadas está na seção
[Releases](CONTRIBUTING.md#releases) dele.

### Verificações de código

```bash
ruff check .
ruff format --check <arquivos alterados>
pyright                      # estrito, pavement_ui (configurado no pyproject.toml)
pyright src tests            # o motor e os testes
PYTHONPATH=. lint-imports    # contratos de camadas da GUI no pyproject.toml
```

### Testes

```bash
pytest
```

Roda a suíte inteira e mostra o resumo de cobertura com as linhas não
cobertas; a configuração da cobertura está no `.coveragerc`. Um relatório HTML
é gravado em `htmlcov/` (`xdg-open htmlcov/index.html`).

## Como citar

Se usar o beam_calculator num trabalho acadêmico, cite-o como descrito no
[CITATION.cff](CITATION.cff) (o GitHub mostra em "Cite this repository").

## Licença

Copyright (C) 2026 Artur Kalil Corrêa

O beam_calculator é software livre: você pode redistribuí-lo e/ou modificá-lo
sob os termos da GNU General Public License, publicada pela Free Software
Foundation, na versão 3 ou (a seu critério) em qualquer versão posterior. Ele é
distribuído SEM QUALQUER GARANTIA; veja o [LICENSE](LICENSE).

O programa empacotado inclui bibliotecas de terceiros sob suas próprias
licenças (PySide6/Qt sob LGPL-3.0, anastruct sob GPL-3.0, as demais sob BSD,
MIT, PSF ou Apache-2.0); os textos delas acompanham o programa, na pasta
`_internal/licenses/`.

As tabelas reproduzidas da ABNT NBR 6120:2019 e de Carvalho & Figueiredo Filho
(2014), em `src/data/`, têm a fonte citada em cada módulo.

---

Read in English: [README.md](README.md)

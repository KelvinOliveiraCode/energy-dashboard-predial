<div align="center">

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-70%2B-brightgreen?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Windows">
</p>

# energy-dashboard-predial

**Painel local de consumo de energia predial: linha de base, custo estimado, desvios e graficos por horario.**

</div>

---

## PT-BR

### O que e

Ferramenta (CLI + painel HTML) que le uma serie local de leituras de consumo
predial (CSV, 90 dias, 3 andares, intervalos de 15 min), compara cada leitura
com a linha de base historica do proprio predio, estima o custo por bandas de
tarifa (ponta / fora de ponta) e gera um relatorio HTML offline com graficos
por horario. O que ela resolve: a pergunta "a conta subiu, o que mudou no
predio esta semana?" sem nuvem, sem API externa e sem instalar framework.

O arquivo `docs/como-ler-o-relatorio-de-consumo.md` explica o vocabulario do
relatorio (kWh, kW, demanda, fator de carga) para quem nao trabalha com
energia.

### Por que foi feito

Em automacao de edificacao, o consumo quase sempre vive dentro de sistema de
telemetria fechado, e a pergunta pratica em predio novo ou em transferencia
e "o que e diferente desta semana em relacao ao padrao normal deste predio?".
Este projeto endereca essa dor do lado da automacao e da infraestrutura
local: o CSV nunca sai da maquina, o servidor so escuta em 127.0.0.1 e o
relatorio HTML abre no navegador sem internet. O valor nao esta no grafico:
esta na conta aberta (o `docs/` traz a linha de base a mao) e em declarar
com clareza o que o modelo **nao** cobre.

### Como rodar

```powershell
# 1. Instalar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# 2. Validar (testes + CLI)
python -m pytest tests/ -v

# 3. Executar
python -m energydash resumo
```

Sem instalar nada, `python -m energydash` tambem roda a partir da raiz do
repositorio: o arquivo `energydash.py` da raiz e um shim que coloca `src/`
no caminho e delega para o pacote (e um arquivo e nao um diretorio por uma
razao de cobertura; ver "O que aprendi").

Saida esperada (real, de `exemplos/saida-resumo.txt`):

```
RELATORIO DE CONSUMO - energy-dashboard-predial
================================================
Periodo: 2026-06-01 a 2026-08-29 (90 dias)
Andares: 3 (andar-1, andar-2, andar-3)
Total: 14630.8 kWh
Custo estimado: BRL 10479.69 (ponta: BRL 3067.15 | fora de ponta: BRL 7412.54)
Demanda: 15.60 kW | Fator de carga: 0.43
Metodo: mesmo horario da semana anterior + mesmo mes anterior | Limiar: 50% acima | margem minima 0.15 kWh

Consumo por andar:
  andar-1: 9286.7 kWh | custo BRL 6648.60 | media 103.2 kWh/dia
  andar-2: 2082.5 kWh | custo BRL 1509.97 | media 23.1 kWh/dia
  andar-3: 3261.6 kWh | custo BRL 2321.11 | media 36.2 kWh/dia

Desvios detectados: 3
  1. andar-2 | 2026-06-26T20:00 a 2026-06-26T22:45 (2.8 h, 12 intervalos) | pico 3.90 kWh (+1058% da linha de base)
  2. andar-3 | 2026-07-26T22:00 a 2026-08-03T05:45 (175.8 h, 256 intervalos) | pico 2.41 kWh (+1328% da linha de base)
  3. andar-1 | 2026-08-17T00:00 a 2026-08-29T23:45 (311.8 h, 1246 intervalos) | pico 3.52 kWh (+279% da linha de base)
```

Testes (74; fim da saida real, `exemplos/saida-testes.txt`):

```
tests\test_servidor.py ....                                              [100%]

============================= 74 passed in 8.95s ==============================
```

Outros comandos:

```powershell
python -m energydash exportar --saida exemplos\dashboard.html   # nao bloqueia; gera o artefato
python -m energydash servir --porta 8000                        # bloqueante; Ctrl+C encerra
tools\abrir-dashboard.bat                                       # duplo clique: serve em http://127.0.0.1:8000
```

`servir` fica em primeiro plano ate o Ctrl+C; e a forma de ver o painel ao
vivo (rotas `/`, `/api/resumo` e `/saude`). Sem terminal, de duplo clique em
`exemplos\dashboard.html` (offline, sem CDN). Saida real do `exportar`:

```
Relatorio em exemplos\dashboard.html / Report at exemplos\dashboard.html
Abra o arquivo no navegador (funciona offline, sem CDN) / Open the file in a browser (works offline, no CDN)
```

### O que aprendi

- **A linha de base absorve regime persistente em ~2 semanas.** O componente
  A olha 7 dias atras e o B olha 1 mes atras; uma mudanca que comeca no dia D
  entra na "semana anterior" em D+7 e no "mes anterior" em D+30, e o L sobe
  junto com o consumo ate o alerta parar. Por isso o desvio 3 foi plantado
  somente em 17/08-29/08: em serie mais longa, parte dele desapareceria do
  relatorio. Ver `docs/metodo-de-linha-base.md` (item 5).
- **Bug: linha de base incluindo o proprio dia.** Na primeira versao, o
  componente A incluia o dia `t` junto com "7 dias atras" (janela de 8 dias
  por engano). Consequencia medida: o pico do desvio 3 caia de ~436% para
  ~180% no andar-1 e os finais de semana paravam de acusar. Uma linha de base
  que inclui o proprio ponto e auto-referente e nunca acusaria pico isolado.
- **Janela de mesclagem de 24h entre leituras.** O desvio recorrente (ar-
  condicionado toda noite no andar-3) geraria 256 linhas separadas com a
  mesma causa raiz; juntar alertas separados por menos de 24h em um unico
  episodio resolve. Trade-off documentado: dois eventos a 20h um do outro
  viram o mesmo episodio.
- **Limiar percentual sem margem minima absoluta gera ruido.** Em horarios
  com linha de base ~0.04 kWh, 50% de desvio sao 0.02 kWh de flutuacao. O
  `max(0.50*L, 0.15 kWh)` derruba alerta em horario vazio sem esconder pico
  real.
- **Shim de raiz como arquivo, nao diretorio.** O `python -m energydash` a
  partir da raiz precisa do `energydash.py`; se fosse um diretorio, o
  pytest-cov trataria `--cov=energydash` como diretorio de fonte, mediria o
  shim (0%) e reportaria "No data was collected".

### Limitacoes

O que este projeto **nao** faz, honestamente:

- **Nao quebra o consumo por setor.** Ha um "medidor" por andar
  (`andar-1..3`); nao ha dividao por ambiente, circuito ou equipamento, e um
  pico nao pode ser atribuido a um ponto especifico.
- **Tarifa ficticia.** Os valores de `dados/tarifa.yaml` nao correspondem a
  concessionaria real; o custo estimado e para demonstracao do modelo
  ponta/fora de ponta, nao para previsao de fatura.
- **Nao cobra demanda nem fator de potencia.** O modelo de custo e
  kwh x preco da banda; demanda (kW) e fator de carga aparecem no relatorio
  como indicadores, mas nao entram na conta.
- **Janela de ~2 semanas para capturar regime persistente.** Depois disso a
  linha de base absorve a mudanca (ver "O que aprendi"); vigilancia de longo
  prazo exigiria linha de base de referencia fixa.

### Licenca

MIT. Ver [LICENSE](LICENSE).

---

## EN

### What it is

A tool (CLI + HTML dashboard) that reads a local building energy series
(CSV, 90 days, 3 floors, 15-minute intervals), compares each reading against
the building's own historical baseline, estimates cost through on-peak /
off-peak tariff bands, and produces an offline HTML report with hourly
charts. What it solves: the question "the bill went up, what changed in this
building this week?" with no cloud, no external API and no framework to
install.

The file `docs/como-ler-o-relatorio-de-consumo.md` explains the report's
vocabulary (kWh, kW, demand, load factor) for people who do not work with
energy.

### Why it was built

In building automation, consumption almost always lives inside a closed
telemetry system, and the practical question in a new or handed-over
building is "what is different this week compared to this building's normal
pattern?". This project addresses that pain from the local automation and
infrastructure side: the CSV never leaves the machine, the server listens
only on 127.0.0.1, and the HTML report opens in a browser without internet.
The value is not the charts: it is the open arithmetic (`docs/` carries the
baseline by hand) and stating plainly what the model does **not** cover.

### How to run

```powershell
# 1. Install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# 2. Validate (tests + CLI)
python -m pytest tests/ -v

# 3. Run
python -m energydash resumo
```

Without installing anything, `python -m energydash` also runs from the repo
root: the `energydash.py` file at the root is a shim that puts `src/` on the
path and delegates to the package (and it is a file, not a directory, for a
coverage reason; see "What I learned").

Expected output (real, from `exemplos/saida-resumo.txt`):

```
RELATORIO DE CONSUMO - energy-dashboard-predial
================================================
Periodo: 2026-06-01 a 2026-08-29 (90 dias)
Andares: 3 (andar-1, andar-2, andar-3)
Total: 14630.8 kWh
Custo estimado: BRL 10479.69 (ponta: BRL 3067.15 | fora de ponta: BRL 7412.54)
Demanda: 15.60 kW | Fator de carga: 0.43
Metodo: mesmo horario da semana anterior + mesmo mes anterior | Limiar: 50% acima | margem minima 0.15 kWh

Consumo por andar:
  andar-1: 9286.7 kWh | custo BRL 6648.60 | media 103.2 kWh/dia
  andar-2: 2082.5 kWh | custo BRL 1509.97 | media 23.1 kWh/dia
  andar-3: 3261.6 kWh | custo BRL 2321.11 | media 36.2 kWh/dia

Desvios detectados: 3
  1. andar-2 | 2026-06-26T20:00 a 2026-06-26T22:45 (2.8 h, 12 intervalos) | pico 3.90 kWh (+1058% da linha de base)
  2. andar-3 | 2026-07-26T22:00 a 2026-08-03T05:45 (175.8 h, 256 intervalos) | pico 2.41 kWh (+1328% da linha de base)
  3. andar-1 | 2026-08-17T00:00 a 2026-08-29T23:45 (311.8 h, 1246 intervalos) | pico 3.52 kWh (+279% da linha de base)
```

Tests (74; tail of the real output, `exemplos/saida-testes.txt`):

```
tests\test_servidor.py ....                                              [100%]

============================= 74 passed in 8.95s ==============================
```

Other commands:

```powershell
python -m energydash exportar --saida exemplos\dashboard.html   # non-blocking; writes the artifact
python -m energydash servir --porta 8000                        # blocking; Ctrl+C stops
tools\abrir-dashboard.bat                                       # double-click: serves http://127.0.0.1:8000
```

`servir` runs in the foreground until Ctrl+C; that is the way to see the
live panel (routes `/`, `/api/resumo` and `/saude`). Without a terminal,
double-click `exemplos\dashboard.html` (offline, no CDN). Real output of
`exportar`:

```
Relatorio em exemplos\dashboard.html / Report at exemplos\dashboard.html
Abra o arquivo no navegador (funciona offline, sem CDN) / Open the file in a browser (works offline, no CDN)
```

### What I learned

- **The baseline absorbs a persistent regime in about two weeks.**
  Component A looks 7 days back and B one month back; a change that starts
  on day D enters "previous week" at D+7 and "previous month" at D+30, and
  L rises with the consumption until the alert stops. That is why deviation
  3 was planted only on Aug 17-29: in a longer series, part of it would
  vanish from the report. See `docs/metodo-de-linha-base.md` (item 5).
- **Bug: a baseline that included its own day.** The first version of
  component A included day `t` together with "7 days back" (an 8-day window
  by mistake). Measured consequence: the peak of deviation 3 dropped from
  about 436% to about 180% on floor 1, and weekends stopped triggering. A
  baseline that includes its own point is self-referential and could never
  flag an isolated spike.
- **A 24h merge window between readings.** The recurring deviation (AC on
  floor 3 every night) would produce 256 separate rows with the same root
  cause; merging alerts spaced less than 24h into one episode fixes it.
  Documented trade-off: two events 20h apart become the same episode.
- **A percentage threshold without a minimum absolute margin creates
  noise.** On slots where the baseline is about 0.04 kWh, a 50% deviation
  is a 0.02 kWh fluctuation. `max(0.50*L, 0.15 kWh)` kills alerts on empty
  hours without hiding a real spike.
- **The root shim as a file, not a directory.** `python -m energydash` from
  the root needs `energydash.py`; as a directory, pytest-cov would treat
  `--cov=energydash` as a source dir, measure the shim (0%) and report "No
  data was collected".

### Limitations

What this project does **not** do, honestly:

- **No per-section breakdown.** There is one "meter" per floor
  (`andar-1..3`); there is no split by room, circuit or equipment, and a
  spike cannot be attributed to a specific point.
- **Fictitious tariff.** The values in `dados/tarifa.yaml` do not match any
  real utility; the estimated cost demonstrates the on-peak/off-peak model,
  it does not forecast a real bill.
- **No demand charge or power factor.** The cost model is kwh x band price;
  demand (kW) and load factor appear in the report as indicators, not as
  billed items.
- **About a two-week window to catch a persistent regime.** After that the
  baseline absorbs the change (see "What I learned"); long-term monitoring
  would need a fixed reference baseline.

### License

MIT. See [LICENSE](LICENSE).

---

## Estrutura / Structure

```
src/energydash/
  serie.py            leitura do CSV e agrupamentos (dia, horario, andar)
  consulta.py         banco SQLite em memoria: tabela leitura(ts, andar, kwh)
  linha_base.py       linha de base: semana anterior + mes anterior
  desvio.py           regra de alerta, margem minima e episodios (janela 24h)
  custo.py            tarifa ponta/fora de ponta, demanda e fator de carga
  relatorio.py        resumo em texto e HTML offline (canvas puro, sem CDN)
  api.py              payload JSON agregado (saida deterministica)
  servidor.py         http.server local em 127.0.0.1: /, /api/resumo, /saude
  cli.py              comandos servir, exportar e resumo
  templates/dash.html template unico do painel (placeholder __DADOS__)
energydash.py         shim de raiz para python -m energydash (arquivo, nao dir)
dados/                serie-consumo.csv (25920 leituras) e tarifa.yaml
docs/                 metodo da linha base e como ler o relatorio de consumo
exemplos/             saidas reais + dashboard.html gerado
tests/                74 testes
tools/                gerar_dados.py (deterministico) e abrir-dashboard.bat
```

## Licenca / License

MIT &mdash; [LICENSE](LICENSE)

---

<div align="center">
  <sub>Por <a href="https://github.com/KelvinOliveiraCode">Kelvin Oliveira</a> &middot;
  <a href="https://kelvinoliveiracode.github.io/portfolio/">portfolio</a></sub>
</div>

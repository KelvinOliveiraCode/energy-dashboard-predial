# energy-dashboard-predial

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![Licenca](https://img.shields.io/badge/Licenca-MIT-yellow?style=flat-square)

Um painel local de consumo de energia predial que le uma serie de 90 dias em intervalos de 15 minutos, compara cada leitura com a linha de base do proprio predio, estima o custo em duas bandas de tarifa e gera um relatorio HTML com graficos por horario, sem nuvem, sem API externa e sem framework para instalar.

## Problema / Por que existe

Em automacao de predios, o consumo quase sempre vive dentro de um sistema de telemetria fechado. Em um predio novo ou apos uma transferencia, a pergunta pratica e "o que mudou nesta semana em relacao ao padrao normal deste predio?". Responder isso costuma exigir exportar dados, aprender a ferramenta de telemetria ou depender de nuvem.

Este projeto atende esse lado da automacao local porque o CSV nunca sai da maquina, o servidor escuta apenas em 127.0.0.1 e o relatorio HTML abre no navegador sem internet. O valor esta na conta aberta do metodo (docs/ mostra o calculo da linha de base a mao) e em declarar com clareza o que o modelo nao cobre.

## O que faz

- Leitura e validacao do CSV (cabecalho ts,andar,kwh; valores finitos e nao negativos; sem duplicados de timestamp e andar)
- Linha de base por horario com componente A (media das 4 leituras do mesmo horario, mesmo dia da semana, 7 dias atras) e componente B (media de todas as leituras do mesmo horario no mes calendario anterior); L e a media dos componentes que existem
- Detecao de desvio com limiar de 50 por cento acima da linha de base e margem minima absoluta de 0.15 kWh; alertas de um mesmo andar separados por menos de 24 horas formam um unico episodio
- Estimativa de custo com tarifa de duas bandas (ponta e fora de ponta) por dia da semana e horario, mais demanda em kW e fator de carga como indicadores
- Relatorio HTML de um unico arquivo, offline e sem CDN (graficos em canvas puro), mais resumo de texto no terminal
- Servidor local em http://127.0.0.1:8000 com rotas /, /api/resumo e /saude, em modo de primeiro plano ate Ctrl+C

## Stack

- Python 3.10+; apenas biblioteca padrao mais PyYAML (leitura do YAML de tarifa)
- sqlite3 (banco em memoria para a serie de leituras)
- http.server (servidor local, bloqueante ate Ctrl+C)
- HTML de um unico arquivo com CSS e JS inline e graficos em canvas puro (sem CDN, sem framework frontend)
- pytest e pytest-cov (ambiente de desenvolvimento)
- Empacotamento com src/ layout, pyproject.toml e entry point energydash (pip install -e .)

## Como funciona

O pipeline e ler_csv -> SQLite em memoria -> linha de base -> deteccao de desvios -> custo -> payload JSON deterministico -> texto ou HTML.

1. serie.ler_csv valida cabecalho, tipos, valores finitos e nao negativos e impede duplicados de (timestamp, andar).
2. linha_base constroi dois indices (por dia da semana e horario; por mes e horario) e responde em O(1) para cada instante - componente A (4 leituras do mesmo horario, mesmo dia da semana, 7 dias atras) e componente B (todas as leituras do mesmo horario no mes anterior); L e a media dos componentes existentes.
3. desvio alerta quando kwh - L > max(0.50 * L, 0.15 kWh); alertas de um mesmo andar separados por menos de 24 horas se fundem em um episodio da primeira ate a ultima leitura alertada.
4. custo classifica cada leitura na banda ponta ou fora de ponta da tarifa de dados/tarifa.yaml e soma kwh vezes preco da banda; demanda e o maior kwh de um intervalo convertido para kW e o fator de carga e a media de kW dividido pela demanda.
5. api.montar_resumo arredonda todos os numeros, o que deixa a saida determinista (mesma serie, mesmo JSON). relatorio escreve o HTML de um arquivo (template com placeholder __DADOS__) ou imprime o resumo de texto.

## Como rodar

Voce precisa do Python 3.10+.

```powershell
# 1. Instalar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

# 2. Validar (testes)
python -m pytest tests/ -q
```

O repositorio reporta 74 testes aprovados.

# 3. Executar
python -m energydash resumo
```

Saida real de exemplo com dados/serie-consumo.csv e dados/tarifa.yaml (tarifa ficticia, somente ilustrativa).

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

Sem instalar o pacote, `python -m energydash` funciona da raiz do repositorio porque energydash.py e um shim que insere src/ no sys.path e delega a src/energydash. O shim e um arquivo, não um diretorio, para que o coverage meça o pacote de src/.

Outros comandos

```powershell
python -m energydash exportar --saida exemplos\dashboard.html   # nao bloqueia; gera o artefato HTML
python -m energydash servir --porta 8000                        # bloqueante; Ctrl+C encerra
tools\abrir-dashboard.bat                                       # duplo clique: serve em http://127.0.0.1:8000
```

`servir` fica em primeiro plano ate Ctrl+C e expõe /, /api/resumo e /saude. `exemplos/dashboard.html` abre com duplo clique e funciona offline sem CDN.

## Estrutura do projeto

```
src/energydash/
  serie.py            leitura e validacao do CSV; agrupacoes por dia, horario, andar
  consulta.py         banco SQLite em memoria com tabela leitura(ts, andar, kwh)
  linha_base.py       calcula linha de base - semana anterior mais mes anterior
  desvio.py           regra de alerta, margem minima e episodios (janela de 24h)
  custo.py            tarifa ponta/fora de ponta, demanda e fator de carga
  relatorio.py        resumo em texto e HTML offline (canvas puro, sem CDN)
  api.py              payload JSON agregado com saida determinista
  servidor.py         http.server em 127.0.0.1 com rotas /, /api/resumo e /saude
  cli.py              comandos resumo, exportar e servir
  templates/dash.html unico template do painel (placeholder __DADOS__)
energydash.py         shim de raiz para python -m energydash (arquivo, nao diretorio)
dados/                serie-consumo.csv (25920 leituras) e tarifa.yaml (ficticia)
docs/                 metodo da linha de base e como ler o relatorio de consumo
exemplos/             saidas reais de terminal e dashboard.html gerado
tests/                74 testes
tools/                gerar_dados.py (deterministico, seed fixa) e abrir-dashboard.bat
```

## Trade-offs e decisões

- Linha base deslizante (semana anterior + mes anterior) em vez de referencia fixa. E simples, sem parametros de configuracao, mas absorve mudancas persistentes depois de cerca de duas semanas. Um regime alto que comece no dia D entra na "semana anterior" em D+7 e no "mes anterior" em D+30; L sobe com o consumo e o alerta cessa. Por isso o desvio persistente (andar-1) foi plantado apenas nos ultimos 13 dias do periodo (docs/metodo-de-linha-base.md).
- Janela de mesclagem de 24 horas entre alertas. Um desvio recorrente (por exemplo, ar-condicionado toda noite) nao vira centenas de linhas; dois alertas a 20 horas de distancia viram o mesmo episodio.
- Margem absoluta de 0.15 kWh junto ao limiar de 50 por cento. Impede alerta por ruido em horarios quase vazios (linha de base cerca de 0.04 kWh, onde 50 por cento sao 0.02 kWh) sem esconder picos reais.
- Bug corrigido - a primeira versao do componente A incluía o proprio dia t (janela de 8 dias por engano). O pico do desvio 3 caiu de cerca de 436 por cento para 180 por cento no andar-1 e finais de semana pararam de acusar. A correcao excluiu o dia atual da janela A. Uma linha de base que inclui o ponto atual e auto-referente e nunca acusaria um pico isolado.
- Shim de raiz como arquivo, não diretorio. Com diretorio, o pytest-cov trataria --cov=energydash como pasta de fonte, mediria o shim (0 por cento) e reportaria "No data was collected".
- Saida deterministica. gerar_dados.py usa random.Random(20260601) e apenas biblioteca padrao; nada usa datetime.now() no caminho de saida. O mesmo CSV produz sempre os mesmos desvios e o mesmo custo.

## Limitações conhecidas

- Sem quebra por setor. Ha um medidor por andar (andar-1, andar-2, andar-3); nao ha divisao por ambiente, circuito ou equipamento, entao um pico nao pode ser atribuído a um ponto específico.
- Tarifa ficticia. dados/tarifa.yaml usa valores inventados (preço ponta BRL 0.9874, fora de ponta BRL 0.6432, ponta em dias uteis das 17h às 23h); o custo estimado demonstra o modelo de duas bandas e não prevê fatura real.
- Sem cobranca de demanda nem fator de potencia. O modelo de custo e kwh vezes preço da banda; demanda (kW) e fator de carga aparecem como indicadores, não como itens cobrados.
- Janela de cerca de duas semanas. Mudança de regime persistente some do relatorio depois que a linha de base a absorve; vigilância de longo prazo exigiria referencia fixa.
- Servidor apenas local. Escuta em 127.0.0.1; não e para exposição em rede.
- Sem autenticacao. Painel local sem controle de acesso.

## Licenca

MIT. Veja [LICENSE](LICENSE).

## Autor

Kelvin Oliveira
https://github.com/KelvinOliveiraCode
https://kelvinoliveiracode.github.io/portfolio/

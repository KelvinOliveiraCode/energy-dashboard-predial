# Metodo da linha de base e da deteccao de desvio

Este documento descreve, com contas abertas, como a ferramenta calcula a
linha de base e decide o que e desvio. O objetivo e que qualquer pessoa
consiga conferir o numero no relatorio sem confiar na caixa preta.

## 1. O que e a linha de base

Para cada leitura do andar `A` no instante `t`, a linha de base `L(t)` e a
media de dois componentes:

- **Componente A (semana anterior):** media das 4 leituras de 15 em 15
  min do **mesmo horario**, no **mesmo dia da semana**, **7 dias antes**.
  Ex.: terca 14h usa as 4 leituras de 14:00, 14:15, 14:30 e 14:45 da
  terca anterior.
- **Componente B (mes anterior):** media de **todas** as leituras do
  **mesmo horario** no **mes calendario anterior** (todo dia, cerca de
  120 leituras por horario).

```
L(t) = ( A(t) + B(t) ) / 2        quando existe A e B
L(t) = A(t)                        quando existe so A
L(t) = B(t)                        quando existe so B
L(t) = nao existe                 quando nao ha historia suficiente
```

Por que dois componentes e nao um so? O componente A captura o padrao
exato do dia da semana (uma quinta de escritorio nao se compara com um
sabado). O componente B e mais estavel (media de ~120 pontos) e ancora a
escala quando a semana anterior teve atipos. Media dos dois suaviza sem
perder o padrao semanal.

## 2. Contas a mao (serie sintetica, teste `test_linha_base.py`)

Serie `a`, sempre as 10h, 4 leituras por dia:

| periodo                | valor por leitura |
|------------------------|-------------------|
| 01/06 a 07/06 (7 dias) | 1.0               |
| 08/06 a 14/06 (7 dias) | 2.0               |
| 15/06 a 30/06 (16 dias)| 4.0               |
| 01/07 a 31/07 (31 dias)| 3.0               |

Consultando a linha de base em **15/07, 10:00**:

- A(15/07) = media das 4 leituras de 10h em **08/07** = 3.0
- B(15/07) = media de todas as 10h de **junho** =
  (7*4*1.0 + 7*4*2.0 + 16*4*4.0) / 120 = (28 + 56 + 256) / 120 = 340/120 = 2.8333...
- L(15/07) = (3.0 + 2.8333) / 2 = **2.9167**

Esse valor exato e o que o teste compara (nao e uma media "aproximada").

## 3. Casos de borda (documentados e testados)

- **Primeiros 7 dias do periodo** (01/06-07/06): A nao existe (25/05-31/05
  nao estao na serie) e B nao existe (maio inteiro fora da serie).
  Resultado: `L = nao existe`, e o detector **nao** acusa nada. E o
  esperado: sem historia, nao se tem contra o que comparar.
- **Junho inteiro** (primeiro mes da serie): B (maio) nao existe, A existe
  a partir de 08/06. Resultado: `L = A`.
- **Inicio de ano** (ex.: janeiro): o "mes anterior" cai no ano anterior.
  O codigo trata esse turno explicitamente (`mes > 1 ? (ano, mes-1) :
  (ano-1, 12)`). Teste `test_valor_turno_de_anos`.

## 4. Regra de alerta

Uma leitura `k` alerta quando:

```
k - L  >  max( limiar * L , margem_minima )
```

com `limiar = 0.50` (50% acima da linha de base) e `margem_minima = 0.15
kWh`. Os desvios plantados no CSV superam a linha de base de 279% a
1328% (ver `exemplos/saida-resumo.txt`), muito acima do limiar, entao a
detecao nao depende de afina-la.

### Por que a margem minima de 0.15 kWh

Sem ela, um horario de madrugada com linha de base ~0.04 kWh alertaria a
cada flutuario de 0.02 kWh (ruido de 50%). O piso absoluto evita alerta
em consumo quase nulo. Decisao: `excede_limiar` exige simultaneamente o
excesso percentual **e** que `k - L` supere 0.15 kWh.

### Por que a janela de mesclagem de 24h

O desvio 2 (ar-condicionado do andar-3) recorre **toda noite** com pausa
de 16h15min durante o dia. Se o episodio terminasse a cada pausa de mais
de 15 min, o relatorio mostraria 8 linhas para a mesma causa raiz. A
regra adotada: dentro de um andar, leituras alertadas separadas por menos
de 24h pertencem ao mesmo episodio (a janela vai da primeira a ultima
leitura alertada). Pausa de 24h ou mais encerra o episodio. Consequencia
documentada: o campo `intervalos` conta leituras que alertaram, entao um
episodio de janela longa pode ter `intervalos` menor que a duracao em
intervalos (ex.: andar-1 tem 1246 de 1248; 2 escapam no final por causa
do item 5).

## 5. Limitacao real: a linha de base absorve mudancas persistentes

Este e o ponto que mais custou para entender e o motivo de o desvio 3
(regime alto do andar-1) estar plantado **somente** em 17/08-29/08 e nao
no periodo todo:

- A linha de base olha 7 dias atras (A) e 1 mes atras (B).
- Uma mudanca que comeca no dia D fica, a partir de D+7, dentro da
  "semana anterior" das leituras seguintes. O componente A comeca a
  incluir o consumo ja alto.
- A partir de D+30, o "mes anterior" tambem include a mudanca (B).
- Como L sobe junto com o consumo, o excesso `k - L` cai e, em algum
  ponto, fica abaixo de 50%: o detector para de alertar.

Com o desvio 3 comecando em 17/08: ate ~24/08, A e B ainda sao baixos e o
excesso e gigante. A partir de ~24/08, A (semana 17/08-23/08) ja esta
alto; L sobe; o excesso cai. No final do periodo (28-29/08) o detector
ainda acusa a maioria dos intervalos, mas 2 escapam por estarem no
limite. O episodio permanece **um unico** (janela de 24h) do inicio ao
fim. Se o regime tivesse comecado em 01/08, parte dele teria desaparecido
do relatorio - exatamente o tipo de erro silencioso que uma linha de base
escorregada produz.

**Consequencia pratica:** para vigilancia de mudanca de regime, uma linha
de base de "semana/mes anterior" e boa no curto prazo (dias a ~2 semanas)
e perde forca depois. Um projeto real que precisar acompanhar regime
perdura deveria ter uma linha de base de referencia fixa (ex.: media do
periodo anterior fechado) alem da de semana/mes.

## 6. Bug que descobri e corrigi

Na primeira versao, o componente A incluia o **proprio dia** `t` junto com
"7 dias antes" (um `range` de 8 dias por engano). Consequencia medida: o
desvio 3 se diluia na propria linha de base (o pico caia de ~436% para
~180% no andar-1, e os finais de semana paravam de acusar porque a media
com 8 dias achatava a oscilacao). A correcao foi excluir o dia atual do
janela de A: `L` usa somente dias **anteriores** a `t`. Isso e importante
porque uma linha de base que inclui o proprio ponto seria auto-referente e
nunca acusaria um pico isolado.

## 7. Determinismo

Tudo e deterministico: `tools/gerar_dados.py` usa `random.Random(20260601)`
e apenas biblioteca padrao; rodar de novo devolve byte a byte os mesmos
arquivos. O mesmo CSV gera sempre os mesmos 3 desvios e o mesmo custo.
Nada usa `datetime.now()` no caminho de saida.

# Como ler o relatorio de consumo

Este guia ensina a ler o painel gerado por este projeto
(`exemplos/dashboard.html` ou o comando `resumo`), sem precisar entender o
codigo. Os numeros usados aqui sao os do exemplo real do projeto (dados
ficticios), para que voce consiga conferir em cima do proprio relatorio.

## 1. O que mede: kWh vs kW (a confusao mais comum)

- **kWh (quilowatt-hora) = energia.** E a quantidade de eletricidade que
  passou pelo medidor no periodo. E o que a conta de luz cobra. Analogia:
  quantos litros de agua passaram pelo cano.
- **kW (quilowatt) = potencia.** E a velocidade com que a energia esta
  sendo consumida num instante. Analogia: a vazao do cano.

Neste projeto cada leitura e um **intervalo de 15 minutos** com a energia
consumida naquele intervalo (kWh). Para converter em potencia media do
intervalo: `kW = kWh / 0,25 h = kWh * 4`. Ex.: uma leitura de 2,0 kWh nos
15 min significa potencia media de 8 kW naquele quarto de hora.

## 2. Demanda

**Demanda** e a maior potencia (kW) observada no periodo. No exemplo,
`Demanda: 15.60 kW`. Ela vem do maior intervalo de 15 min
(3,90 kWh * 4). A demanda importa porque, em contratos comerciais, a
conta tem uma **tarifa de demanda**: voce paga pela maior potencia que
precisou suportar, independente de ter usado pouco no resto do dia.

## 3. Fator de carga

**Fator de carga** = media de potencia / demanda. No exemplo, `0.43`.
Ele diz que, em media, o predio usou 43% da sua potencia maxima.

- Perto de 1.0: o consumo e "chato", sempre perto do maximo (tipico de
  equipamento que nao desliga).
- Baixo (ex.: 0.2-0.4): o predio tem picos curtos e longos vales
  (tipico de escritorio, que desliga a noite).

Fator de carga baixo, sozinho, nao e mau - mas ajuda a entender de onde
vem a demanda.

## 4. As duas bandas de horario (ponta / fora de ponta)

A tarifa tem preco diferente por horario. Neste projeto (ficticio):

- **Ponta:** seg a sex, 17h-22h. Preco maior (0,9874 BRL/kWh no exemplo).
- **Fora de ponta:** todo o resto. Preco menor (0,6432 BRL/kWh).

O relatorio separa o custo em `custo_ponta` e `custo_fora_ponta`. Se o
`custo_ponta` estiver grande, o caminho natural de economia e **mover
carga** para fora da banda (ex.: nao ligar o chuveiro industrial / maquina
de lavar industrial / recarga de baterias no horario das 17h-22h). No
exemplo, `ponta: BRL 3067.15` contra `fora de ponta: BRL 7412.54` - a
conta e dominada pelo fora de ponta, entao a alavanca de horario e menor
aqui; a alavanca principal sao os desvios (item 6).

> Nota: `hora_ponta_fim` e **exclusivo**. Banda `17:00-23:00` significa
> 17h, 18h, ..., 22h. As 23h ja sao fora de ponta.

## 5. Os graficos por andar

- **Consumo diario por andar (90 dias):** uma linha por andar, eixo X =
  dia, eixo Y = kWh daquele dia. Serve para ver a tendencia (subiu?
  caiu?) e localizar na data onde algo mudou. As **bandas vermelhas**
  marcam os desvios detectados (item 6).
- **Perfil horario (media por hora):** eixo X = hora do dia (0h-23h),
  eixo Y = media de kWh por intervalo. Serve para ver **quando** o predio
  consome. No exemplo, o andar-1 (area tecnica) e quase plano o dia todo
  (equipamento que nao desliga); os andares 2 e 3 tem pico em horario de
  expediente e caem a noite - ate o periodo do desvio do ar-condicionado.

## 6. Desvios detectados (o coracao do relatorio)

O detector compara cada leitura com a **linha de base** (o que se esperava
para aquele horario/dia, ver `metodo-de-linha-base.md`) e acusa quando o
consumo real passa de **50% acima** da linha de base (com piso de 0,15
kWh). No exemplo, 3 desvios:

| # | Andar | Janela | O que significa |
|---|-------|--------|-----------------|
| 1 | andar-2 | 26/06 20:00-22:45 | Halogenios ligados fora do horario (uma noite) |
| 2 | andar-3 | 26/07 22:00 - 03/08 05:45 | Ar-condicionado em consumo elevado a noite, 8 noites seguidas |
| 3 | andar-1 | 17/08 - 29/08 | Equipamento tecnico ficou em regime alto ate o fim do periodo |

Como ler cada campo da tabela do painel:

- **Janela (inicio a fim):** de quando a quando o consumo ficou anormal.
- **Duracao:** quantas horas essa janela abrange.
- **Intervalos:** quantas leituras de 15 min alertaram dentro da janela
  (um desvio recorrente, tipo o do ar-condicionado, tem pausas de dia; o
  numero conta so as leituras que alertaram).
- **Pico:** a maior leitura do episodio (kWh) e quantos % acima da linha
  de base ficou (`+1328%` = o pico foi 13x a linha de base).
- **Media:** a media do excesso ao longo do episodio.

**Como agir:** cada desvio aponta um **quando** e um **onde** (andar). O
proximo passo e olhar o que acontece naquele andar/aquele horario. Um
desvio isolado de uma noite (andar-2) e quase sempre algo que foi
esquecido ligado. Um desvio recorrente a noite (andar-3) e quase sempre
um equipamento ou configuracao. Um desvio que comeca num dia e fica ate o
fim (andar-1) e um equipamento que mudou de regime - ou um consumo
continuo inesperado (ex.: aquecedor que nao desliga).

## 7. O que o relatorio **nao** diz

- **Nao e a conta oficial da concessionaria.** O custo aqui e uma
  estimativa com tarifa ficticia; a conta real tem outros termos
  (fator de potencia, bandeira de tarifa, taxa fixa etc.).
- **Nao separa setores dentro do andar.** A leitura e por andar; para
  saber se e o ar-condicionado da sala 302 ou o elevador, precisa de
  submediador.
- **Nao diagnostica causa.** Ele localiza o **onde/quando** do excesso; a
  causa vai no campo.
- **Nao pega mudanca de regime dura-dura depois de ~2 semanas** por causa
  da linha de base (ver `metodo-de-linha-base.md`, item 5).

## 8. Glossario rapido

| Termo | Significado |
|-------|-------------|
| kWh | energia consumida no periodo (o que a conta cobra) |
| kW | potencia num instante (velocidade do consumo) |
| Demanda | maior kW do periodo |
| Fator de carga | media de kW / demanda |
| Ponta / fora de ponta | bandas de horario com preco diferente |
| Linha de base | consumo esperado p/ aquele horario/dia (historico) |
| Desvio | episodio em que o real passou do limiar acima da linha de base |

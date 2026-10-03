"""Detecao de desvio em relacao a linha de base.
Detection of deviations from the baseline.

Regra (documentada em docs/metodo-de-linha-base.md):
Rule (documented in docs/metodo-de-linha-base.md):

- Alerta quando o consumo real excede a linha de base em mais de um limiar
  percentual (padrao 50%), respeitando uma margem minima absoluta (padrao
  0.15 kWh) para nao alertar em horarios de consumo quase nulo.
  Alert when real consumption exceeds the baseline by more than a
  percentage threshold (default 50%), honoring a minimum absolute margin
  (default 0.15 kWh) so near-zero slots do not trigger alerts.
- Leituras alertadas viram um episodio por andar. Se o desvio recorre
  (ex.: toda noite) e a pausa entre duas leituras alertadas e menor que
  24h, as duas pertencem ao mesmo episodio: a janela vai da primeira
  leitura alertada a ultima. Pausas de 24h ou mais encerram o episodio.
  Alerted readings become one episode per floor. When the deviation recurs
  (e.g., every night) and the pause between two alerted readings is less
  than 24h, both belong to the same episode: the window runs from the first
  alerted reading to the last. Pauses of 24h or more end the episode.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

LIMIAR_PADRAO = 0.50
MARGEM_MINIMA_PADRAO = 0.15
_JANELA_MERGEO_SEGUNDOS = 86400  # pausas de menos de 24h nao encerram o episodio


@dataclass(frozen=True)
class Desvio:
    """Episodio de desvio em um andar.
    A deviation episode on one floor.

    ``pico_percentual`` e ``media_percentual`` medem quantos porcentos acima
    da linha de base o consumo ficou.
    ``pico_percentual`` and ``media_percentual`` measure how many percent
    above the baseline the consumption reached.
    """

    andar: str
    inicio: datetime
    fim: datetime
    # Quantas leituras alertaram dentro da janela (a janela pode ter pausas
    # de menos de 24h, mescladas por _JANELA_MERGEO_SEGUNDOS).
    # How many readings alerted inside the window (the window may hold pauses
    # of less than 24h, merged by _JANELA_MERGEO_SEGUNDOS).
    intervalos: int
    pico_kwh: float
    pico_percentual: float
    media_percentual: float

    @property
    def duracao_horas(self) -> float:
        """Duracao do episodio em horas (do inicio ao fim da ultima leitura).
        Episode duration in hours (from start to the last reading).
        """
        return (self.fim - self.inicio).total_seconds() / 3600.0


def excede_limiar(
    kwh: float,
    linha_base: float,
    limiar: float = LIMIAR_PADRAO,
    margem_minima: float = MARGEM_MINIMA_PADRAO,
) -> bool:
    """Verificar se ``kwh`` excede ``linha_base`` alem do limiar.
    Check whether ``kwh`` exceeds ``linha_base`` beyond the threshold.

    Sem linha de base ou com linha de base zero, nunca alerta.
    Without a baseline, or with a zero baseline, never alert.
    """
    if linha_base <= 0:
        return False
    return kwh - linha_base > max(limiar * linha_base, margem_minima)


def detectar_desvios(
    leituras: Iterable,
    linha_base,
    limiar: float = LIMIAR_PADRAO,
    margem_minima: float = MARGEM_MINIMA_PADRAO,
) -> list[Desvio]:
    """Rodar a deteccao em toda a serie e devolver os episodios.
    Run detection over the whole series and return the episodes.

    Os episodios saem ordenados por (inicio, andar).
    Episodes are returned ordered by (start, floor).
    """
    por_andar: dict[str, list[tuple[datetime, float, float]]] = {}
    for leitura in leituras:
        ponto = linha_base.valor(leitura.andar, leitura.timestamp)
        if ponto is None:
            continue
        if excede_limiar(leitura.kwh, ponto.valor, limiar, margem_minima):
            por_andar.setdefault(leitura.andar, []).append(
                (leitura.timestamp, leitura.kwh, ponto.valor)
            )

    episodios: list[Desvio] = []
    for andar in sorted(por_andar):
        itens = sorted(por_andar[andar], key=lambda t: t[0])
        inicio = itens[0][0]
        fim = itens[0][0]
        intervalos = 1
        pico_kwh = itens[0][1]
        pico_percentual = (itens[0][1] - itens[0][2]) / itens[0][2] * 100.0
        soma_percentual = pico_percentual
        for ts, kwh, base in itens[1:]:
            if (ts - fim).total_seconds() < _JANELA_MERGEO_SEGUNDOS:
                # Janela mesclada: desvio recorrente (ex.: toda noite) ou
                # intervalo isolado perdido dentro do episodio.
                # Merged window: recurring deviation (e.g., every night) or a
                # single missed interval inside the episode.
                fim = ts
                intervalos += 1
                percentual = (kwh - base) / base * 100.0
                if kwh > pico_kwh:
                    pico_kwh = kwh
                    pico_percentual = percentual
                soma_percentual += percentual
            else:
                episodios.append(
                    Desvio(
                        andar=andar,
                        inicio=inicio,
                        fim=fim,
                        intervalos=intervalos,
                        pico_kwh=pico_kwh,
                        pico_percentual=pico_percentual,
                        media_percentual=soma_percentual / intervalos,
                    )
                )
                inicio = ts
                fim = ts
                intervalos = 1
                pico_kwh = kwh
                pico_percentual = (kwh - base) / base * 100.0
                soma_percentual = pico_percentual
        episodios.append(
            Desvio(
                andar=andar,
                inicio=inicio,
                fim=fim,
                intervalos=intervalos,
                pico_kwh=pico_kwh,
                pico_percentual=pico_percentual,
                media_percentual=soma_percentual / intervalos,
            )
        )
    episodios.sort(key=lambda d: (d.inicio, d.andar))
    return episodios

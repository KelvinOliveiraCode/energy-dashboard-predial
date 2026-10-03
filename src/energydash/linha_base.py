"""Linha de base de consumo por horario e dia da semana.
Energy consumption baseline per hour and weekday.

Metodo (documentado em docs/metodo-de-linha-base.md):
Method (documented in docs/metodo-de-linha-base.md):

- Componente A (semana anterior / previous week): media das 4 leituras do
  mesmo horario, no mesmo dia da semana, 7 dias antes.
  Average of the 4 readings of the same hour, on the same weekday, 7 days
  before.
- Componente B (mes anterior / previous month): media de todas as leituras
  do mesmo horario no mes calendario anterior.
  Average of all readings of the same hour in the previous calendar month.
- Linha de base L = media(A, B) quando existem os dois; se existe apenas um,
  usa-se ele; se nenhum existe, nao ha linha de base.
  Baseline L = average(A, B) when both exist; if only one exists, use it;
  if none exists, there is no baseline.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

ORIGEM_SEMANA = "semana"
ORIGEM_MES = "mes"
ORIGEM_SEMANA_MES = "semana+mes"


@dataclass(frozen=True)
class PontoLinhaBase:
    """Valor esperado em um instante, com a origem dos componentes.
    Expected value at an instant, with the origin of its components.
    """

    valor: float
    origem: str


class LinhaBase:
    """Indexa leituras para calcular a linha de base em qualquer instante.
    Indexes readings to compute the baseline at any instant.

    A construcao dos indices e O(n); a consulta individual e O(1).
    Building the indexes is O(n); individual queries are O(1).
    """

    def __init__(self, leituras: Iterable) -> None:
        # (andar, weekday, hora, data) -> leituras daquele horario naquele dia
        self._por_dia: dict[tuple[str, int, int, object], list[float]] = defaultdict(list)
        # (andar, ano, mes, hora) -> leituras daquele horario naquele mes
        self._por_mes: dict[tuple[str, int, int, int], list[float]] = defaultdict(list)
        for leitura in leituras:
            ts: datetime = leitura.timestamp
            self._por_dia[
                (leitura.andar, ts.weekday(), ts.hour, ts.date())
            ].append(leitura.kwh)
            self._por_mes[
                (leitura.andar, ts.year, ts.month, ts.hour)
            ].append(leitura.kwh)

    def valor(self, andar: str, ts: datetime) -> Optional[PontoLinhaBase]:
        """Linha de base de ``andar`` no instante ``ts``.
        Baseline of ``andar`` at instant ``ts``.

        Devolve ``None`` quando nem a semana nem o mes anteriores tem dados.
        Returns ``None`` when neither the previous week nor the previous
        month has data.
        """
        partes: list[float] = []
        origem = ""
        dia_7 = ts.date() - timedelta(days=7)
        valores_semana = self._por_dia.get(
            (andar, ts.weekday(), ts.hour, dia_7), []
        )
        if valores_semana:
            partes.append(sum(valores_semana) / len(valores_semana))
            origem = ORIGEM_SEMANA
        if ts.month > 1:
            ano_anterior, mes_anterior = ts.year, ts.month - 1
        else:
            ano_anterior, mes_anterior = ts.year - 1, 12
        valores_mes = self._por_mes.get(
            (andar, ano_anterior, mes_anterior, ts.hour), []
        )
        if valores_mes:
            partes.append(sum(valores_mes) / len(valores_mes))
            origem = (origem + "+" if origem else "") + ORIGEM_MES
        if not partes:
            return None
        return PontoLinhaBase(
            valor=sum(partes) / len(partes), origem=origem
        )

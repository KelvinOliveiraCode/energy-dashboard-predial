"""Series temporais de consumo de energia em intervalos fixos de 15 minutos.
Energy consumption time series in fixed 15-minute intervals.

Leita em CSV local e expone agrupa basicas (por dia, por horario,
por andar) usadas pelo resto do pacote.
Reads a local CSV file and exposes basic groupings (per day, per hour,
per floor) used by the rest of the package.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

MINUTOS_POR_INTERVALO = 15
INTERVALOS_POR_DIA = 96


class SerieError(Exception):
    """Dados invalidos na serie de consumo.
    Invalid data in the consumption series.
    """


@dataclass(frozen=True)
class Leitura:
    """Uma leitura de energia em um instante para um andar.
    A single energy reading at an instant for one floor.

    kwh: energia consumida no intervalo que termina em ``timestamp``.
    kwh: energy consumed in the interval ending at ``timestamp``.
    """

    timestamp: datetime
    andar: str
    kwh: float


def ler_csv(caminho: str | Path) -> list[Leitura]:
    """Ler um CSV no formato ``ts,andar,kwh`` e devolver leituras ordenadas.
    Read a ``ts,andar,kwh`` CSV and return sorted readings.

    Valida cabecalho, tipo das celulas, valores finitos e nao negativos,
    e impede duplicados de (timestamp, andar).
    Validates the header, cell types, finite and non-negative values,
    and prevents duplicate (timestamp, floor) pairs.
    """
    path = Path(caminho)
    if not path.is_file():
        raise SerieError(
            f"arquivo nao encontrado / file not found: {path.name}"
        )
    leituras: list[Leitura] = []
    vistos: set[tuple[datetime, str]] = set()
    with path.open("r", encoding="utf-8", newline="") as arq:
        leitor = csv.reader(arq)
        cabecalho = next(leitor, None)
        if cabecalho is None or [c.strip().lower() for c in cabecalho] != [
            "ts",
            "andar",
            "kwh",
        ]:
            raise SerieError(
                "cabecalho esperado: ts,andar,kwh / expected header ts,andar,kwh"
            )
        for linha_num, linha in enumerate(leitor, start=2):
            if not linha or all(cel.strip() == "" for cel in linha):
                raise SerieError(
                    f"linha vazia na linha {linha_num} / empty row at line {linha_num}"
                )
            if len(linha) != 3:
                raise SerieError(
                    f"linha com {len(linha)} colunas (esperado 3) na linha {linha_num} "
                    f"/ wrong column count at line {linha_num}"
                )
            try:
                ts = datetime.fromisoformat(linha[0].strip())
            except ValueError as exc:
                raise SerieError(
                    f"timestamp invalido '{linha[0]}' na linha {linha_num} / "
                    f"bad timestamp at line {linha_num}"
                ) from exc
            andar = linha[1].strip()
            if not andar:
                raise SerieError(
                    f"andar vazio na linha {linha_num} / empty floor at line {linha_num}"
                )
            try:
                kwh = float(linha[2].strip())
            except ValueError as exc:
                raise SerieError(
                    f"kwh invalido '{linha[2]}' na linha {linha_num} / bad kwh at line {linha_num}"
                ) from exc
            if not math.isfinite(kwh):
                raise SerieError(
                    f"kwh nao finito na linha {linha_num} / non-finite kwh at line {linha_num}"
                )
            if kwh < 0:
                raise SerieError(
                    f"kwh negativo na linha {linha_num} / negative kwh at line {linha_num}"
                )
            chave = (ts, andar)
            if chave in vistos:
                raise SerieError(
                    f"leitura duplicada {ts.isoformat()} {andar} na linha {linha_num} "
                    f"/ duplicate reading at line {linha_num}"
                )
            vistos.add(chave)
            leituras.append(Leitura(timestamp=ts, andar=andar, kwh=kwh))
    if not leituras:
        raise SerieError("serie vazia / empty series")
    leituras.sort(key=lambda r: (r.timestamp, r.andar))
    return leituras


def andares(leituras: list[Leitura]) -> list[str]:
    """Devolver a lista ordenada e unica de andares presentes.
    Return the sorted, unique list of floors present.
    """
    return sorted({r.andar for r in leituras})


def periodo(leituras: list[Leitura]) -> tuple[datetime, datetime]:
    """Devolver (primeiro, ultimo) timestamp da serie.
    Return the (first, last) timestamp of the series.
    """
    if not leituras:
        raise SerieError("serie vazia / empty series")
    ts = [r.timestamp for r in leituras]
    return min(ts), max(ts)


def filtrar_por_andar(leituras: list[Leitura], andar: str) -> list[Leitura]:
    """Devolver as leituras de um andar, preservando a ordem temporal.
    Return the readings of one floor, preserving time order.
    """
    return [r for r in leituras if r.andar == andar]


def total_kwh(leituras: list[Leitura], andar: str | None = None) -> float:
    """Somar kwh; com ``andar``, somar so esse andar.
    Sum kwh; when ``andar`` is given, sum only that floor.
    """
    base = filtrar_por_andar(leituras, andar) if andar else leituras
    return sum(r.kwh for r in base)


def por_dia(leituras: list[Leitura], andar: str | None = None) -> dict[date, float]:
    """Somar kwh por dia do calendario.
    Sum kwh per calendar day.
    """
    base = filtrar_por_andar(leituras, andar) if andar else leituras
    total: dict[date, float] = {}
    for r in base:
        d = r.timestamp.date()
        total[d] = total.get(d, 0.0) + r.kwh
    return total


def media_por_horario(
    leituras: list[Leitura], andar: str | None = None
) -> list[float]:
    """Media de kwh por hora do dia (24 valores, indice 0..23).
    Average kwh per hour of day (24 values, index 0..23).

    Horas sem leitura aparecem como 0.0.
    Hours without readings show up as 0.0.
    """
    base = filtrar_por_andar(leituras, andar) if andar else leituras
    soma = [0.0] * 24
    qtd = [0] * 24
    for r in base:
        h = r.timestamp.hour
        soma[h] += r.kwh
        qtd[h] += 1
    return [(soma[h] / qtd[h]) if qtd[h] else 0.0 for h in range(24)]


def horas_cobertas(leituras: list[Leitura], andar: str | None = None) -> int:
    """Numero de intervalos distintos no periodo (dias x 96).
    Number of distinct intervals in the period (days x 96).
    """
    base = filtrar_por_andar(leituras, andar) if andar else leituras
    if not base:
        return 0
    ini, fim = periodo(base)
    return round((fim - ini).total_seconds() / (MINUTOS_POR_INTERVALO * 60)) + 1

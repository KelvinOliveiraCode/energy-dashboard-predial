"""Custo estimado a partir de tarifa por horario (ponta / fora de ponta).
Estimated cost from an hourly tariff (on-peak / off-peak).

A tarifa vem de um YAML local (dados/tarifa.yaml) com valores ficticios.
O modelo separa cada leitura em uma das duas bandas pelo dia da semana e
pelo horario, e soma kwh x preco da banda.
The tariff comes from a local YAML file (dados/tarifa.yaml) with
fictitious values. The model assigns each reading to one of the two bands
by weekday and hour, and sums kwh x band price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import yaml

DIAS_POR_SEMANA = 7


class TarifaError(Exception):
    """Tarifa ausente ou invalida.
    Missing or invalid tariff.
    """


@dataclass(frozen=True)
class Tarifa:
    """Tarifa de duas bandas. / Two-band tariff.

    ``hora_ponta_fim`` e exclusivo: a banda de ponta cobre
    ``inicio <= hora < fim`` nos dias listados.
    ``hora_ponta_fim`` is exclusive: the on-peak band covers
    ``inicio <= hour < fim`` on the listed weekdays.
    """

    moeda: str
    preco_ponta: float
    preco_fora_ponta: float
    hora_ponta_inicio: int
    hora_ponta_fim: int
    dias_ponta: tuple[int, ...]
    taxa_fixa_mensal: float


def _horario_para_hora(texto: str, campo: str) -> int:
    """Converter ``"HH:MM"`` em hora; valida 0..23.
    Convert ``"HH:MM"`` to an hour; validates 0..23.
    """
    try:
        horas, minutos = texto.strip().split(":")
        h, m = int(horas), int(minutos)
    except (ValueError, AttributeError) as exc:
        raise TarifaError(
            f"campo '{campo}' deve ser 'HH:MM' / field '{campo}' must be 'HH:MM'"
        ) from exc
    if not (0 <= h <= 23) or not (0 <= m <= 59):
        raise TarifaError(
            f"campo '{campo}' fora de faixa / field '{campo}' out of range: {texto}"
        )
    return h


def carregar_tarifa(caminho: str | Path) -> Tarifa:
    """Ler e validar a tarifa do YAML.
    Read and validate the YAML tariff.
    """
    path = Path(caminho)
    if not path.is_file():
        raise TarifaError(f"arquivo nao encontrado / file not found: {path.name}")
    try:
        with path.open("r", encoding="utf-8") as arq:
            bruto = yaml.safe_load(arq)
    except yaml.YAMLError as exc:
        raise TarifaError(
            f"YAML invalido / invalid YAML: {path.name}"
        ) from exc
    if not isinstance(bruto, dict):
        raise TarifaError("raiz do YAML deve ser um mapa / YAML root must be a map")

    def _num(valor, campo: str) -> float:
        if not isinstance(valor, (int, float)) or isinstance(valor, bool):
            raise TarifaError(f"campo '{campo}' deve ser numero / field '{campo}' must be a number")
        v = float(valor)
        if not math.isfinite(v):
            raise TarifaError(f"campo '{campo}' nao e finito / field '{campo}' is not finite")
        return v

    preco_ponta = _num(bruto.get("preco_ponta"), "preco_ponta")
    preco_fora = _num(bruto.get("preco_fora_ponta"), "preco_fora_ponta")
    if preco_ponta <= 0:
        raise TarifaError("preco_ponta deve ser positivo / preco_ponta must be positive")
    if preco_fora <= 0:
        raise TarifaError("preco_fora_ponta deve ser positivo / preco_fora_ponta must be positive")
    inicio = _horario_para_hora(str(bruto.get("hora_ponta_inicio", "")), "hora_ponta_inicio")
    fim = _horario_para_hora(str(bruto.get("hora_ponta_fim", "")), "hora_ponta_fim")
    if inicio >= fim:
        raise TarifaError("hora_ponta_inicio deve ser menor que hora_ponta_fim / inicio must be < fim")
    bruto_dias = bruto.get("dias_ponta")
    if not isinstance(bruto_dias, (list, tuple)) or not bruto_dias:
        raise TarifaError("dias_ponta deve ser uma lista nao vazia / dias_ponta must be a non-empty list")
    dias: list[int] = []
    for d in bruto_dias:
        if not isinstance(d, int) or isinstance(d, bool) or not (0 <= d <= 6):
            raise TarifaError("dias_ponta deve conter numeros 0..6 (0=segunda) / dias_ponta must hold 0..6 ints")
        dias.append(d)
    moeda = str(bruto.get("moeda", "BRL")).strip() or "BRL"
    taxa_fixa = _num(bruto.get("taxa_fixa_mensal", 0.0), "taxa_fixa_mensal")
    if taxa_fixa < 0:
        raise TarifaError("taxa_fixa_mensal nao pode ser negativa / taxa_fixa_mensal must be >= 0")
    return Tarifa(
        moeda=moeda,
        preco_ponta=preco_ponta,
        preco_fora_ponta=preco_fora,
        hora_ponta_inicio=inicio,
        hora_ponta_fim=fim,
        dias_ponta=tuple(sorted(set(dias))),
        taxa_fixa_mensal=taxa_fixa,
    )


def banda(tarifa: Tarifa, ts: datetime) -> str:
    """Devolver 'ponta' ou 'fora_ponta' para um instante.
    Return 'ponta' or 'fora_ponta' for an instant.
    """
    if ts.weekday() in tarifa.dias_ponta and tarifa.hora_ponta_inicio <= ts.hour < tarifa.hora_ponta_fim:
        return "ponta"
    return "fora_ponta"


def custo_periodo(leituras: Iterable, tarifa: Tarifa) -> float:
    """Somar kwh x preco da banda em todas as leituras.
    Sum kwh x band price over all readings.
    """
    total = 0.0
    for r in leituras:
        preco = tarifa.preco_ponta if banda(tarifa, r.timestamp) == "ponta" else tarifa.preco_fora_ponta
        total += r.kwh * preco
    return total


def consumo_por_banda(leituras: Iterable, tarifa: Tarifa) -> tuple[float, float]:
    """Devolver (kwh_ponta, kwh_fora_ponta).
    Return (on-peak kwh, off-peak kwh).
    """
    ponta = 0.0
    fora = 0.0
    for r in leituras:
        if banda(tarifa, r.timestamp) == "ponta":
            ponta += r.kwh
        else:
            fora += r.kwh
    return ponta, fora


def demanda_kw(leituras: Iterable, minutos_intervalo: int = 15) -> float:
    """Demanda estimada: maior kwh de um intervalo convertido para kW.
    Estimated demand: largest interval kwh converted to kW.

    Com intervalo de 15 min, 1 kWh no intervalo equivale a 4 kW.
    With a 15 min interval, 1 kWh in the interval equals 4 kW.
    """
    fator = 60.0 / minutos_intervalo
    maior = 0.0
    for r in leituras:
        if r.kwh > maior:
            maior = r.kwh
    return maior * fator


def fator_de_carga(leituras: Iterable, minutos_intervalo: int = 15) -> Optional[float]:
    """Fator de carga: media de kW dividida pela demanda de kW.
    Load factor: average kW divided by demand in kW.

    Media de kW = energia total / duracao do periodo (em horas).
    Average kW = total energy / period duration (in hours).
    Devolve ``None`` quando ha menos de duas leituras.
    Returns ``None`` when there are fewer than two readings.
    """
    lista = list(leituras)
    if len(lista) < 2:
        return None
    ts = [r.timestamp for r in lista]
    duracao_h = (max(ts) - min(ts)).total_seconds() / 3600.0
    duracao_h += minutos_intervalo / 60.0
    if duracao_h <= 0:
        return None
    total = sum(r.kwh for r in lista)
    media_kw = total / duracao_h
    demanda = demanda_kw(lista, minutos_intervalo)
    if demanda <= 0:
        return None
    return media_kw / demanda

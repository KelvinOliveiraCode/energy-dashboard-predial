"""Testes da linha de base com series sinteticas de conta a mao.
Baseline tests with hand-computed synthetic series.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from energydash import linha_base, serie


def _leituras_hora10(pares: list[tuple[date, float]]) -> list[serie.Leitura]:
    """4 leituras das 10:00-10:45 por data, valor constante.
    4 readings at 10:00-10:45 per date, constant value.
    """
    saida: list[serie.Leitura] = []
    for data, valor in pares:
        for quarto in range(4):
            ts = datetime(data.year, data.month, data.day, 10, 15 * quarto)
            saida.append(serie.Leitura(ts, "a", float(valor)))
    return saida


def _faixa(inicio: date, dias: int, valor: float) -> list[tuple[date, float]]:
    return [(inicio + timedelta(days=i), valor) for i in range(dias)]


# Serie "a": junho de 2026 em 3 trechos e julho todo, sempre as 10h.
# Series "a": June 2026 in 3 stretches plus all of July, always at 10h.
PARES_A = (
    _faixa(date(2026, 6, 1), 7, 1.0)
    + _faixa(date(2026, 6, 8), 7, 2.0)
    + _faixa(date(2026, 6, 15), 16, 4.0)
    + _faixa(date(2026, 7, 1), 31, 3.0)
)


def test_valor_sem_historico_devolve_none():
    base = linha_base.LinhaBase(_leituras_hora10(PARES_A))
    # 5 de junho: nem 7 dias antes (29/05) nem maio existem.
    assert base.valor("a", datetime(2026, 6, 5, 10, 0)) is None
    # andar ausente do indice.
    assert base.valor("b", datetime(2026, 7, 15, 10, 0)) is None


def test_valor_somente_componente_semana():
    base = linha_base.LinhaBase(_leituras_hora10(PARES_A))
    ponto = base.valor("a", datetime(2026, 6, 15, 10, 0))
    assert ponto is not None
    assert ponto.valor == pytest.approx(2.0)
    assert ponto.origem == linha_base.ORIGEM_SEMANA


def test_valor_semana_e_mes_conta_mao():
    base = linha_base.LinhaBase(_leituras_hora10(PARES_A))
    ponto = base.valor("a", datetime(2026, 7, 15, 10, 0))
    assert ponto is not None
    # A = 8 de julho (4 leituras de 3.0) -> 3.0
    # B = junho todo, hora 10: (7*4*1.0 + 7*4*2.0 + 16*4*4.0) / 120 = 17/6
    esperado_mes = 340.0 / 120.0
    assert ponto.valor == pytest.approx((3.0 + esperado_mes) / 2.0)
    assert ponto.origem == linha_base.ORIGEM_SEMANA_MES


def test_valor_turno_de_mes_dentro_do_ano():
    pares_b = _faixa(date(2026, 1, 1), 31, 1.0) + _faixa(date(2026, 2, 1), 28, 5.0)
    base = linha_base.LinhaBase(_leituras_hora10(pares_b))
    ponto = base.valor("a", datetime(2026, 2, 8, 10, 0))
    assert ponto is not None
    assert ponto.valor == pytest.approx(3.0)  # media(5.0, 1.0)
    assert ponto.origem == linha_base.ORIGEM_SEMANA_MES


def test_valor_turno_de_anos():
    pares_c = (
        _faixa(date(2026, 12, 1), 31, 2.0) + _faixa(date(2027, 1, 1), 31, 4.0)
    )
    base = linha_base.LinhaBase(_leituras_hora10(pares_c))
    ponto = base.valor("a", datetime(2027, 1, 8, 10, 0))
    assert ponto is not None
    assert ponto.valor == pytest.approx(3.0)  # media(4.0, 2.0)


def test_valor_nao_usa_dia_atual_nem_mes_atual():
    # No mesmo dia da consulta o valor sobe: nao pode entrar na linha de base.
    pares = _faixa(date(2026, 7, 1), 7, 1.0) + _faixa(date(2026, 7, 8), 7, 99.0)
    base = linha_base.LinhaBase(_leituras_hora10(pares))
    ponto = base.valor("a", datetime(2026, 7, 10, 10, 0))
    assert ponto is not None
    # A = 3 de julho (1.0); B = junho (inexistente) -> so o componente semana.
    assert ponto.valor == pytest.approx(1.0)

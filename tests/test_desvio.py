"""Testes da deteccao de desvio, incluindo os 3 desvios plantados.
Deviation detection tests, including the 3 planted deviations.

As series sinteticas comecam em 2026-05-25 (segunda-feira) para que as
leituras de junho tenham semana anterior dentro da serie; em junho todos
os dias tem 96 leituras de 15 min.
Synthetic series start on 2026-05-25 (a Monday) so that June readings
have a previous week inside the series; every day has 96 readings.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from energydash import desvio, linha_base, serie

_INICIO = date(2026, 5, 25)
_DIAS = 28  # 2026-05-25 a 2026-06-21


def _leituras_dias(dias: list[tuple[date, float]]) -> list[serie.Leitura]:
    """Leituras a cada 15 min, 24h por dia, valor constante por dia.
    Readings every 15 min, 24h per day, constant value per day.
    """
    saida: list[serie.Leitura] = []
    for data, valor in dias:
        for minuto in range(96):
            ts = datetime(data.year, data.month, data.day) + timedelta(
                minutes=15 * minuto
            )
            saida.append(serie.Leitura(ts, "a", float(valor)))
    return saida


def _dias_constantes(valor: float = 1.0) -> list[tuple[date, float]]:
    return [(_INICIO + timedelta(days=i), float(valor)) for i in range(_DIAS)]


def test_excede_limiar_acima():
    assert desvio.excede_limiar(1.6, 1.0) is True  # 60% > 50%


def test_excede_limiar_abaixo():
    assert desvio.excede_limiar(1.4, 1.0) is False  # 40% < 50%


def test_excede_limiar_limiar_personalizado():
    assert desvio.excede_limiar(1.3, 1.0, limiar=0.2, margem_minima=0.0) is True
    assert desvio.excede_limiar(1.1, 1.0, limiar=0.2, margem_minima=0.0) is False


def test_excede_limiar_margem_minima():
    # Baseline quase zero: o piso de 0.15 kWh evita falso positivo de ruido.
    assert desvio.excede_limiar(0.10, 0.02) is False
    assert desvio.excede_limiar(0.21, 0.05) is True


def test_excede_limiar_com_zero_ou_negativo():
    assert desvio.excede_limiar(10.0, 0.0) is False
    assert desvio.excede_limiar(10.0, -1.0) is False


def test_sem_desvio_quando_constante():
    leituras = _leituras_dias(_dias_constantes())
    base = linha_base.LinhaBase(leituras)
    assert desvio.detectar_desvios(leituras, base) == []


def test_sem_base_nao_gera_desvio():
    # So 7 dias: A e B nao existem em lugar nenhum -> sem alerta.
    leituras = _leituras_dias(_dias_constantes(50.0)[:7])
    base = linha_base.LinhaBase(leituras)
    assert desvio.detectar_desvios(leituras, base) == []


def test_um_episodio_contiguo():
    dias = _dias_constantes()
    dias[11] = (date(2026, 6, 5), 3.0)
    dias[12] = (date(2026, 6, 6), 3.0)
    leituras = _leituras_dias(dias)
    base = linha_base.LinhaBase(leituras)
    [ep] = desvio.detectar_desvios(leituras, base)
    assert ep.andar == "a"
    assert ep.inicio == datetime(2026, 6, 5, 0, 0)
    assert ep.fim == datetime(2026, 6, 6, 23, 45)
    assert ep.intervalos == 192
    assert ep.pico_kwh == pytest.approx(3.0)
    assert ep.pico_percentual == pytest.approx(200.0)
    assert ep.media_percentual == pytest.approx(200.0)
    assert ep.duracao_horas == pytest.approx(47.75)


def test_episodio_termina_no_intervalo_limpo():
    # Desvio so nas duas primeiras leituras do dia 5: episodio de 2 intervalos.
    leituras = _leituras_dias(_dias_constantes())
    alvos = {
        datetime(2026, 6, 5, 0, 0),
        datetime(2026, 6, 5, 0, 15),
    }
    leituras = [
        serie.Leitura(r.timestamp, r.andar, 3.0) if r.timestamp in alvos else r
        for r in leituras
    ]
    base = linha_base.LinhaBase(leituras)
    [ep] = desvio.detectar_desvios(leituras, base)
    assert ep.inicio == datetime(2026, 6, 5, 0, 0)
    assert ep.fim == datetime(2026, 6, 5, 0, 15)
    assert ep.intervalos == 2


def test_dois_episodios_separados_por_intervalo_limpo():
    leituras = _leituras_dias(_dias_constantes())
    alvos = {
        datetime(2026, 6, 5, 0, 0),
        datetime(2026, 6, 7, 0, 0),
    }
    leituras = [
        serie.Leitura(r.timestamp, r.andar, 3.0) if r.timestamp in alvos else r
        for r in leituras
    ]
    base = linha_base.LinhaBase(leituras)
    eps = desvio.detectar_desvios(leituras, base)
    assert len(eps) == 2
    assert [e.inicio for e in eps] == [
        datetime(2026, 6, 5, 0, 0),
        datetime(2026, 6, 7, 0, 0),
    ]


def test_desvio_em_um_andar_nao_contamina_os_outros():
    leituras = _leituras_dias(_dias_constantes())
    # andar "b": igual a "a" exceto 2026-06-05, dia inteiro a 3.0
    base_b = _leituras_dias(_dias_constantes())
    base_b = [
        serie.Leitura(r.timestamp, "b", 3.0)
        if r.timestamp.date() == date(2026, 6, 5)
        else serie.Leitura(r.timestamp, "b", 1.0)
        for r in base_b
    ]
    tudo = leituras + base_b
    base = linha_base.LinhaBase(tudo)
    eps = desvio.detectar_desvios(tudo, base)
    assert len(eps) == 1
    assert eps[0].andar == "b"
    assert eps[0].inicio == datetime(2026, 6, 5, 0, 0)
    assert eps[0].fim == datetime(2026, 6, 5, 23, 45)
    assert eps[0].intervalos == 96


def test_tres_desvios_plantados_no_dado_gerado(dados_gerado):
    """O detector deve bater com os 3 desvios plantados pelo gerador.
    The detector must match the 3 deviations planted by the generator.
    """
    desvios = dados_gerado["desvios"]
    assert len(desvios) == 3
    por_andar = {d.andar: d for d in desvios}
    assert set(por_andar) == {"andar-1", "andar-2", "andar-3"}

    # 1) andar-2: halogenios fora do horario, sexta 2026-06-26, 20h-23h.
    d2 = por_andar["andar-2"]
    assert d2.inicio == datetime(2026, 6, 26, 20, 0)
    assert d2.fim == datetime(2026, 6, 26, 22, 45)
    assert d2.intervalos == 12

    # 2) andar-3: ar-condicionado elevado a noite, oito noites seguidas,
    #    de 2026-07-26 22h ate 2026-08-03 05h45 (janela mesclada < 24h).
    d3 = por_andar["andar-3"]
    assert d3.inicio == datetime(2026, 7, 26, 22, 0)
    assert d3.fim == datetime(2026, 8, 3, 5, 45)
    assert d3.intervalos == 8 + 7 * 32 + 24  # 256 intervalos

    # 3) andar-1: equipamento em regime alto, 2026-08-17 ate o fim.
    # Na ultima semana a linha de base ja absorve parte do regime (o
    # componente "semana anterior" fica alto): dois intervalos escapam do
    # limiar; a janela mesclada mantem um unico episodio do inicio ao fim.
    d1 = por_andar["andar-1"]
    assert d1.inicio == datetime(2026, 8, 17, 0, 0)
    assert d1.fim == datetime(2026, 8, 29, 23, 45)
    assert 1200 <= d1.intervalos <= 13 * 96

    # O pico de cada desvio ficou bem acima da linha de base.
    for d in desvios:
        assert d.pico_percentual > 100.0
        assert d.media_percentual > 50.0

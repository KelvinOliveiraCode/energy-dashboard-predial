"""Testes de serie.ler_csv e das agregacoes.
Tests for serie.ler_csv and the aggregations.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from energydash import serie


def _escreve_csv(tmp_path, texto: str):
    p = tmp_path / "s.csv"
    p.write_text(texto, encoding="utf-8")
    return p


def test_ler_csv_gerado_25920_linhas(csv_gerado):
    leituras = serie.ler_csv(csv_gerado)
    assert len(leituras) == 25920
    assert serie.andares(leituras) == ["andar-1", "andar-2", "andar-3"]
    ini, fim = serie.periodo(leituras)
    assert ini == datetime(2026, 6, 1, 0, 0)
    assert fim == datetime(2026, 8, 29, 23, 45)
    # ordem cronologica estavel: (timestamp, andar)
    chaves = [(r.timestamp, r.andar) for r in leituras]
    assert chaves == sorted(chaves)


def test_ler_csv_arquivo_inexistente_levanta_erro(tmp_path):
    with pytest.raises(serie.SerieError, match="nao encontrado"):
        serie.ler_csv(tmp_path / "sem-arquivo.csv")


def test_ler_csv_cabecalho_invalido(tmp_path):
    p = _escreve_csv(tmp_path, "timestamp,andar,energia\n2026-06-01T00:00,a1,1.0\n")
    with pytest.raises(serie.SerieError, match="cabecalho"):
        serie.ler_csv(p)


def test_ler_csv_timestamp_malformado(tmp_path):
    p = _escreve_csv(tmp_path, "ts,andar,kwh\n01/06/2026 00:00,a1,1.0\n")
    with pytest.raises(serie.SerieError, match="timestamp invalido"):
        serie.ler_csv(p)


def test_ler_csv_kwh_malformado(tmp_path):
    p = _escreve_csv(tmp_path, "ts,andar,kwh\n2026-06-01T00:00,a1,abc\n")
    with pytest.raises(serie.SerieError, match="kwh invalido"):
        serie.ler_csv(p)


def test_ler_csv_kwh_nao_finito(tmp_path):
    p = _escreve_csv(tmp_path, "ts,andar,kwh\n2026-06-01T00:00,a1,nan\n")
    with pytest.raises(serie.SerieError, match="nao finito"):
        serie.ler_csv(p)


def test_ler_csv_kwh_negativo(tmp_path):
    p = _escreve_csv(tmp_path, "ts,andar,kwh\n2026-06-01T00:00,a1,-0.5\n")
    with pytest.raises(serie.SerieError, match="negativo"):
        serie.ler_csv(p)


def test_ler_csv_andar_vazio(tmp_path):
    p = _escreve_csv(tmp_path, "ts,andar,kwh\n2026-06-01T00:00, ,1.0\n")
    with pytest.raises(serie.SerieError, match="andar vazio"):
        serie.ler_csv(p)


def test_ler_csv_duplicado(tmp_path):
    p = _escreve_csv(
        tmp_path,
        "ts,andar,kwh\n2026-06-01T00:00,a1,1.0\n2026-06-01T00:00,a1,2.0\n",
    )
    with pytest.raises(serie.SerieError, match="duplicada"):
        serie.ler_csv(p)


def test_ler_csv_serie_vazia(tmp_path):
    p = _escreve_csv(tmp_path, "ts,andar,kwh\n")
    with pytest.raises(serie.SerieError, match="vazia"):
        serie.ler_csv(p)


def test_total_e_filtrar_por_andar():
    a = serie.Leitura(datetime(2026, 6, 1, 10, 0), "a1", 1.0)
    b = serie.Leitura(datetime(2026, 6, 1, 10, 15), "a2", 2.0)
    c = serie.Leitura(datetime(2026, 6, 1, 10, 30), "a1", 0.5)
    assert serie.total_kwh([a, b, c]) == 3.5
    assert serie.total_kwh([a, b, c], andar="a1") == 1.5
    assert [r.kwh for r in serie.filtrar_por_andar([a, b, c], "a2")] == [2.0]


def test_por_dia():
    leituras = [
        serie.Leitura(datetime(2026, 6, 1, 0, 0), "a1", 1.0),
        serie.Leitura(datetime(2026, 6, 1, 23, 45), "a1", 2.0),
        serie.Leitura(datetime(2026, 6, 2, 0, 0), "a1", 4.0),
    ]
    assert serie.por_dia(leituras) == {
        date(2026, 6, 1): 3.0,
        date(2026, 6, 2): 4.0,
    }


def test_media_por_horario_24_vals():
    leituras = [
        serie.Leitura(datetime(2026, 6, 1, 10, 0), "a1", 1.0),
        serie.Leitura(datetime(2026, 6, 1, 10, 15), "a1", 3.0),
    ]
    media = serie.media_por_horario(leituras)
    assert len(media) == 24
    assert media[10] == 2.0
    assert media[11] == 0.0


def test_horas_cobertas():
    leituras = [
        serie.Leitura(datetime(2026, 6, 1, 0, 0), "a1", 1.0),
        serie.Leitura(datetime(2026, 6, 3, 23, 45), "a1", 1.0),
    ]
    assert serie.horas_cobertas(leituras) == 96 * 3


def test_periodo_serie_vazia_levanta_erro():
    with pytest.raises(serie.SerieError):
        serie.periodo([])

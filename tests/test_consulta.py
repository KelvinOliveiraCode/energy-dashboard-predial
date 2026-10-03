"""Testes das consultas SQLite.
SQLite query tests.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pytest

from energydash import consulta, serie


def _leituras_demo() -> list[serie.Leitura]:
    return [
        serie.Leitura(datetime(2026, 6, 1, 0, 0), "a1", 1.0),
        serie.Leitura(datetime(2026, 6, 1, 0, 15), "a1", 2.0),
        serie.Leitura(datetime(2026, 6, 1, 1, 0), "a2", 4.0),
        serie.Leitura(datetime(2026, 6, 2, 0, 0), "a1", 8.0),
    ]


def test_conexao_cria_schema():
    con = consulta.conexao(":memory:")
    nomes = {
        linha[0]
        for linha in con.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
        )
    }
    assert "leitura" in nomes
    assert "idx_leitura_andar_ts" in nomes
    assert "idx_leitura_ts" in nomes
    con.close()


def test_banco_vazio():
    con = consulta.conexao(":memory:")
    assert consulta.total_linhas(con) == 0
    assert consulta.andares(con) == []
    assert consulta.min_max(con) is None
    assert consulta.leituras_periodo(con) == []
    assert consulta.consumo_por_dia(con) == {}
    assert consulta.consumo_por_andar(con) == {}
    con.close()


def test_carregar_e_total():
    con = consulta.conexao(":memory:")
    n = consulta.carregar(con, _leituras_demo())
    assert n == 4
    assert consulta.total_linhas(con) == 4
    assert consulta.andares(con) == ["a1", "a2"]
    con.close()


def test_min_max():
    con = consulta.conexao(":memory:")
    consulta.carregar(con, _leituras_demo())
    assert consulta.min_max(con) == (
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
    )
    con.close()


def test_consumo_por_dia_e_andar():
    con = consulta.conexao(":memory:")
    consulta.carregar(con, _leituras_demo())
    assert consulta.consumo_por_dia(con) == {
        date(2026, 6, 1): 7.0,
        date(2026, 6, 2): 8.0,
    }
    assert consulta.consumo_por_dia(con, andar="a1") == {
        date(2026, 6, 1): 3.0,
        date(2026, 6, 2): 8.0,
    }
    assert consulta.consumo_por_andar(con) == {"a1": 11.0, "a2": 4.0}
    con.close()


def test_leituras_periodo_filtros():
    con = consulta.conexao(":memory:")
    consulta.carregar(con, _leituras_demo())
    # todo o periodo
    assert len(consulta.leituras_periodo(con)) == 4
    # so o dia 1
    so_dia_1 = consulta.leituras_periodo(
        con, inicio=datetime(2026, 6, 1, 0, 0), fim=datetime(2026, 6, 1, 23, 59)
    )
    assert len(so_dia_1) == 3
    # so um andar no periodo completo
    so_a1 = consulta.leituras_periodo(con, andar="a1")
    assert [r.kwh for r in so_a1] == [1.0, 2.0, 8.0]
    # janela vazia
    assert (
        consulta.leituras_periodo(
            con,
            inicio=datetime(2026, 7, 1),
            fim=datetime(2026, 7, 2),
        )
        == []
    )
    con.close()


def test_duplicado_viola_restricao_unica():
    con = consulta.conexao(":memory:")
    consulta.carregar(con, _leituras_demo())
    with pytest.raises(sqlite3.IntegrityError):
        consulta.carregar(
            con,
            [serie.Leitura(datetime(2026, 6, 1, 0, 0), "a1", 99.0)],
        )
    con.close()


def test_carregar_csv(tmp_path):
    csv = tmp_path / "s.csv"
    csv.write_text(
        "ts,andar,kwh\n2026-06-01T00:00,a1,1.5\n2026-06-01T00:15,a1,2.5\n",
        encoding="utf-8",
    )
    con = consulta.conexao(":memory:")
    assert consulta.carregar_csv(con, csv) == 2
    assert consulta.total_linhas(con) == 2
    assert consulta.consumo_por_andar(con) == {"a1": 4.0}
    con.close()

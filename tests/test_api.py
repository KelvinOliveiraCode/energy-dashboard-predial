"""Testes do payload agregado do painel.
Tests for the aggregated dashboard payload.
"""

from __future__ import annotations

import json

import pytest

from energydash import api, consulta, custo


@pytest.fixture()
def resumo(csv_gerado, tarifa_gerada):
    con = consulta.conexao(":memory:")
    consulta.carregar_csv(con, csv_gerado)
    out = api.montar_resumo(con, custo.carregar_tarifa(tarifa_gerada))
    con.close()
    return out


def test_estrutura_do_payload(resumo):
    assert resumo["app"] == "energy-dashboard-predial"
    assert resumo["andares"] == ["andar-1", "andar-2", "andar-3"]
    assert resumo["periodo"]["dias"] == 90
    assert resumo["periodo"]["inicio"] == "2026-06-01T00:00"
    assert resumo["periodo"]["fim"] == "2026-08-29T23:45"
    for chave in ("geral", "metodo", "custo", "por_andar", "perfil_horario", "desvios"):
        assert chave in resumo
    # 90 dias por andar no serie_diaria e 24 valores no perfil horario
    for andar in resumo["andares"]:
        assert len(resumo["por_andar"][andar]["serie_diaria"]) == 90
        assert len(resumo["perfil_horario"][andar]) == 24
    # soma por andar bate com o total
    soma = sum(p["kwh"] for p in resumo["por_andar"].values())
    assert soma == pytest.approx(resumo["geral"]["total_kwh"], abs=0.05)


def test_desvios_do_payload(resumo):
    assert resumo["geral"]["desvios"] == 3
    andares = {d["andar"] for d in resumo["desvios"]}
    assert andares == {"andar-1", "andar-2", "andar-3"}
    for d in resumo["desvios"]:
        assert d["intervalos"] > 0
        assert d["pico_percentual"] > 100.0
        assert d["inicio"] < d["fim"]


def test_resumo_json_valido_e_seguro(resumo):
    texto = api.resumo_json(resumo)
    dados = json.loads(texto)
    assert dados == resumo
    # deterministico: mesma serializacao duas vezes
    assert texto == api.resumo_json(resumo)
    # seguro para embutir em <script>
    assert "</" not in texto

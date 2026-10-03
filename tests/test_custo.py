"""Testes da tarifa, bandas e custo estimado.
Tests for the tariff, bands and estimated cost.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from energydash import custo, serie

TARIFA_OK = {
    "moeda": "BRL",
    "preco_ponta": 1.0,
    "preco_fora_ponta": 0.5,
    "hora_ponta_inicio": "17:00",
    "hora_ponta_fim": "23:00",
    "dias_ponta": [0, 1, 2, 3, 4],
    "taxa_fixa_mensal": 10.0,
}


def _escreve_yaml(tmp_path: Path, texto: str) -> Path:
    p = tmp_path / "tarifa.yaml"
    p.write_text(texto, encoding="utf-8")
    return p


def _tarifa_yaml(ajustes: dict) -> str:
    dados = dict(TARIFA_OK)
    dados.update(ajustes)
    linhas = [
        f"moeda: {dados['moeda']}",
        f"preco_ponta: {dados['preco_ponta']}",
        f"preco_fora_ponta: {dados['preco_fora_ponta']}",
        f'hora_ponta_inicio: "{dados["hora_ponta_inicio"]}"',
        f'hora_ponta_fim: "{dados["hora_ponta_fim"]}"',
        f"dias_ponta: [{', '.join(str(d) for d in dados['dias_ponta'])}]",
        f"taxa_fixa_mensal: {dados['taxa_fixa_mensal']}",
    ]
    return "\n".join(linhas) + "\n"


def test_carregar_tarifa_gerada(tarifa_gerada: Path):
    tarifa = custo.carregar_tarifa(tarifa_gerada)
    assert tarifa.moeda == "BRL"
    assert tarifa.preco_ponta == pytest.approx(0.9874)
    assert tarifa.preco_fora_ponta == pytest.approx(0.6432)
    assert (tarifa.hora_ponta_inicio, tarifa.hora_ponta_fim) == (17, 23)
    assert tarifa.dias_ponta == (0, 1, 2, 3, 4)
    assert tarifa.taxa_fixa_mensal == pytest.approx(78.45)


def test_banda_ponta_e_fora_ponta(tmp_path):
    tarifa = custo.carregar_tarifa(_escreve_yaml(tmp_path, _tarifa_yaml({})))
    # Segunda 2026-06-01: 17h e 22h sao ponta; 16h e 23h nao sao.
    assert custo.banda(tarifa, datetime(2026, 6, 1, 17, 0)) == "ponta"
    assert custo.banda(tarifa, datetime(2026, 6, 1, 22, 30)) == "ponta"
    assert custo.banda(tarifa, datetime(2026, 6, 1, 16, 59)) == "fora_ponta"
    assert custo.banda(tarifa, datetime(2026, 6, 1, 23, 0)) == "fora_ponta"
    # Sabado 2026-06-06: fora de ponta o dia todo.
    assert custo.banda(tarifa, datetime(2026, 6, 6, 18, 0)) == "fora_ponta"


def test_custo_periodo_conta_mao(tmp_path):
    tarifa = custo.carregar_tarifa(_escreve_yaml(tmp_path, _tarifa_yaml({})))
    leituras = [
        # segunda na banda de ponta: 2.0 kWh x 1.0 = 2.0
        serie.Leitura(datetime(2026, 6, 1, 17, 0), "a", 2.0),
        # segunda fora da banda: 2.0 kWh x 0.5 = 1.0
        serie.Leitura(datetime(2026, 6, 1, 16, 0), "a", 2.0),
        # sabado fora da banda: 1.0 kWh x 0.5 = 0.5
        serie.Leitura(datetime(2026, 6, 6, 17, 0), "a", 1.0),
    ]
    assert custo.custo_periodo(leituras, tarifa) == pytest.approx(3.5)
    assert custo.consumo_por_banda(leituras, tarifa) == (
        pytest.approx(2.0),
        pytest.approx(3.0),
    )


def test_demanda_kw(tmp_path):
    tarifa = custo.carregar_tarifa(_escreve_yaml(tmp_path, _tarifa_yaml({})))
    leituras = [
        serie.Leitura(datetime(2026, 6, 1, 17, 0), "a", 0.5),
        serie.Leitura(datetime(2026, 6, 1, 17, 15), "a", 2.0),
    ]
    assert custo.demanda_kw(leituras) == pytest.approx(8.0)  # 2.0 kWh x 4
    assert custo.demanda_kw(leituras, minutos_intervalo=60) == pytest.approx(2.0)
    assert custo.demanda_kw([]) == 0.0


def test_fator_de_carga_conta_mao(tmp_path):
    tarifa = custo.carregar_tarifa(_escreve_yaml(tmp_path, _tarifa_yaml({})))
    leituras = [
        serie.Leitura(datetime(2026, 6, 1, 17, 0), "a", 2.0),
        serie.Leitura(datetime(2026, 6, 1, 17, 15), "a", 2.0),
    ]
    # energia 4.0 kWh em 0.5 h -> media 8 kW; demanda 8 kW -> fator 1.0
    assert custo.fator_de_carga(leituras) == pytest.approx(1.0)


def test_fator_de_carga_sem_historico():
    assert custo.fator_de_carga([]) is None
    assert custo.fator_de_carga(
        [serie.Leitura(datetime(2026, 6, 1, 17, 0), "a", 1.0)]
    ) is None


@pytest.mark.parametrize(
    "ajustes",
    [
        {"preco_ponta": -1.0},
        {"preco_fora_ponta": 0.0},
        {"hora_ponta_inicio": "23:00", "hora_ponta_fim": "17:00"},
        {"hora_ponta_inicio": "25:00"},
        {"dias_ponta": []},
        {"dias_ponta": [0, 9]},
        {"taxa_fixa_mensal": -5.0},
        {"moeda": "BRL", "preco_ponta": "abc"},
    ],
)
def test_tarifa_invalida_levanta_erro(tmp_path, ajustes):
    p = _escreve_yaml(tmp_path, _tarifa_yaml(ajustes))
    with pytest.raises(custo.TarifaError):
        custo.carregar_tarifa(p)


def test_tarifa_yaml_malformado_levanta_erro(tmp_path):
    p = _escreve_yaml(tmp_path, "moeda: [incompleto\n")
    with pytest.raises(custo.TarifaError, match="YAML"):
        custo.carregar_tarifa(p)


def test_tarifa_arquivo_inexistente(tmp_path):
    with pytest.raises(custo.TarifaError, match="nao encontrado"):
        custo.carregar_tarifa(tmp_path / "sem-tarifa.yaml")

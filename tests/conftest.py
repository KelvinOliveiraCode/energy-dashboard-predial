"""Fixtures compartilhadas: pipeline sobre o dado gerado em dados/.
Shared fixtures: the pipeline over the generated data in dados/.

O pipeline (ler CSV -> linha de base -> desvios) e pesado; a sessao o
calcula uma vez e reutiliza.
The pipeline (read CSV -> baseline -> deviations) is heavy; the session
computes it once and reuses it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from energydash import desvio, linha_base, serie

ROOT = Path(__file__).resolve().parents[1]
CSV_GERADO = ROOT / "dados" / "serie-consumo.csv"
TARIFA_GERADA = ROOT / "dados" / "tarifa.yaml"

_CACHE: dict = {}


def _pipeline() -> dict:
    if "leituras" not in _CACHE:
        leituras = serie.ler_csv(CSV_GERADO)
        base = linha_base.LinhaBase(leituras)
        _CACHE["leituras"] = leituras
        _CACHE["linha_base"] = base
        _CACHE["desvios"] = desvio.detectar_desvios(leituras, base)
    return _CACHE


@pytest.fixture(scope="session")
def dados_gerado() -> dict:
    """Leituras, linha de base e desvios da serie gerada.
    Readings, baseline and deviations of the generated series.
    """
    return _pipeline()


@pytest.fixture(scope="session")
def csv_gerado() -> Path:
    """Caminho do CSV gerado. / Path of the generated CSV."""
    return CSV_GERADO


@pytest.fixture(scope="session")
def tarifa_gerada() -> Path:
    """Caminho do YAML de tarifa gerado. / Path of the generated tariff."""
    return TARIFA_GERADA

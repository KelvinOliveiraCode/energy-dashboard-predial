"""Testes do servidor HTTP local.
Tests for the local HTTP server.

Estrategia: sobe um ThreadingHTTPServer em porta 0 (o sistema escolhe uma
porta livre) dentro de thread daemon, e responde as requisicoes com
urllib.request; o fixture fecha o servidor no finally (shutdown + close),
para que o pytest nunca fique bloqueado.
Strategy: start a ThreadingHTTPServer on port 0 (the OS picks a free
port) inside a daemon thread, and answer requests with urllib.request; the
fixture shuts the server down (shutdown + close) so pytest never hangs.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from energydash import api, consulta, custo, relatorio, servidor

ROTA_INEXISTENTE = "/nao-existe"


@pytest.fixture(scope="module")
def porta_livre():
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1]
    con = consulta.conexao(":memory:")
    consulta.carregar_csv(con, str(raiz / "dados" / "serie-consumo.csv"))
    tarifa = custo.carregar_tarifa(str(raiz / "dados" / "tarifa.yaml"))
    resumo = api.montar_resumo(con, tarifa)
    con.close()
    httpd, thread = servidor.iniciar_em_thread(
        api.resumo_json(resumo), relatorio.carregar_template(), porta=0
    )
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get(porta: int, rota: str):
    url = f"http://127.0.0.1:{porta}{rota}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_raiz_devolve_painel_200(porta_livre):
    status, corpo = _get(porta_livre, "/")
    assert status == 200
    assert "ENERGYDASH" in corpo
    assert "energy-dashboard-predial" in corpo
    # os dados foram embutidos no HTML (placeholder substituido)
    assert "total_kwh" in corpo
    assert "__DADOS__" not in corpo


def test_api_resumo_devolve_json_200(porta_livre):
    status, corpo = _get(porta_livre, "/api/resumo")
    assert status == 200
    dados = json.loads(corpo)
    assert dados["andares"] == ["andar-1", "andar-2", "andar-3"]
    assert dados["periodo"]["dias"] == 90


def test_saude(porta_livre):
    status, corpo = _get(porta_livre, "/saude")
    assert status == 200
    assert json.loads(corpo) == {"status": "ok"}


def test_rota_inexistente_devolve_404(porta_livre):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(porta_livre, ROTA_INEXISTENTE)
    assert excinfo.value.code == 404
    corpo = excinfo.value.read().decode("utf-8")
    assert "route not found" in corpo

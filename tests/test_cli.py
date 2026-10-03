"""Testes da linha de comando.
Command line interface tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from energydash import cli

RAIZ = Path(__file__).resolve().parents[1]
CSV_GERADO = RAIZ / "dados" / "serie-consumo.csv"
TARIFA_GERADA = RAIZ / "dados" / "tarifa.yaml"


def _comando(comando: str, *args: str) -> list[str]:
    return [comando, "--dados", str(CSV_GERADO), "--tarifa", str(TARIFA_GERADA), *args]


def test_help_do_nivel_raiz(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])
    assert excinfo.value.code == 0
    saida = capsys.readouterr().out
    assert "servir" in saida
    assert "exportar" in saida
    assert "resumo" in saida


def test_versao(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--versao"])
    assert excinfo.value.code == 0
    assert "energydash 1.0.0" in capsys.readouterr().out


def test_sem_comando_erro_de_argparse():
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code == 2


def test_resumo_imprime_relatorio_com_3_desvios(capsys):
    codigo = cli.main(_comando("resumo"))
    assert codigo == 0
    saida = capsys.readouterr().out
    assert "RELATORIO DE CONSUMO" in saida
    assert "Desvios detectados: 3" in saida
    assert "andar-1" in saida and "andar-2" in saida and "andar-3" in saida


def test_resumo_saida_deterministica(capsys):
    cli.main(_comando("resumo"))
    primeira = capsys.readouterr().out
    cli.main(_comando("resumo"))
    segunda = capsys.readouterr().out
    assert primeira == segunda


def test_exportar_cria_html_offline(tmp_path, capsys):
    saida = tmp_path / "sub" / "painel.html"
    codigo = cli.main(_comando("exportar", "--saida", str(saida)))
    assert codigo == 0
    html = saida.read_text(encoding="utf-8")
    assert "ENERGYDASH" in html
    assert "total_kwh" in html
    assert "__DADOS__" not in html
    # offline: nenhuma referencia a http(s) para assets
    assert "http://cdn" not in html.lower() and "https://cdn" not in html.lower()
    assert "Relatorio em" in capsys.readouterr().out


def test_exportar_sai_determinista(tmp_path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    cli.main(_comando("exportar", "--saida", str(a)))
    cli.main(_comando("exportar", "--saida", str(b)))
    assert a.read_bytes() == b.read_bytes()


def test_dados_inexistentes_devolve_1(capsys):
    codigo = cli.main(
        ["resumo", "--dados", str(Path("nao-existe.csv")), "--tarifa", str(TARIFA_GERADA)]
    )
    assert codigo == 1
    assert "ERRO" in capsys.readouterr().err


def test_tarifa_inexistente_devolve_1(capsys):
    codigo = cli.main(
        ["resumo", "--dados", str(CSV_GERADO), "--tarifa", str(Path("sem.yaml"))]
    )
    assert codigo == 1
    assert "ERRO" in capsys.readouterr().err


def test_servir_porta_fora_de_faixa_devolve_1(capsys):
    codigo = cli.main(_comando("servir", "--porta", "70000"))
    assert codigo == 1
    assert "porta" in capsys.readouterr().err

"""Linha de comando do energydash.
energydash command line interface.

Comandos:
Commands:

- ``servir``   sobe o painel em http://127.0.0.1:<porta> (bloqueante;
  Ctrl+C encerra)
- ``exportar`` gera o relatorio HTML estatico, offline, sem CDN
- ``resumo``   imprime o resumo do periodo em texto
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from energydash import api, consulta, custo, relatorio, serie, servidor

DADOS_PADRAO = "dados/serie-consumo.csv"
TARIFA_PADRAO = "dados/tarifa.yaml"
_SAIDA_PADRAO = "exemplos/dashboard.html"


def montar_parser() -> argparse.ArgumentParser:
    """Montar o parser com os subcomandos.
    Build the parser with the subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="energydash",
        description=(
            "Painel local de consumo de energia predial: linha de base, "
            "custo estimado, desvios e graficos por horario. "
            "Local building energy dashboard: baseline, estimated cost, "
            "deviations and hourly charts."
        ),
    )
    parser.add_argument(
        "--versao", action="version", version="energydash 1.0.0"
    )
    sub = parser.add_subparsers(dest="comando", metavar="comando", required=True)

    def _fonte(grupo: argparse.ArgumentParser) -> None:
        grupo.add_argument(
            "--dados",
            default=DADOS_PADRAO,
            help=f"CSV de consumo / consumption CSV (padrao: {DADOS_PADRAO})",
        )
        grupo.add_argument(
            "--tarifa",
            default=TARIFA_PADRAO,
            help=f"YAML da tarifa / tariff YAML (padrao: {TARIFA_PADRAO})",
        )

    p_servir = sub.add_parser(
        "servir",
        help="serve o painel em http://127.0.0.1:<porta>; bloqueante, Ctrl+C encerra",
    )
    p_servir.add_argument(
        "--porta",
        type=int,
        default=servidor.PORTA_PADRAO,
        help=f"porta TCP (padrao: {servidor.PORTA_PADRAO})",
    )
    _fonte(p_servir)

    p_exportar = sub.add_parser(
        "exportar",
        help="gera o relatorio HTML estatico (offline, sem CDN)",
    )
    p_exportar.add_argument(
        "--saida",
        default=_SAIDA_PADRAO,
        help=f"caminho do HTML (padrao: {_SAIDA_PADRAO})",
    )
    _fonte(p_exportar)

    p_resumo = sub.add_parser(
        "resumo", help="imprime o resumo do periodo em texto"
    )
    _fonte(p_resumo)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI; devolve o codigo de saida.
    CLI entry point; returns the exit code.
    """
    parser = montar_parser()
    args = parser.parse_args(argv)

    try:
        leituras = serie.ler_csv(args.dados)
        tarifa = custo.carregar_tarifa(args.tarifa)
    except (serie.SerieError, custo.TarifaError, OSError, yaml.YAMLError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    if args.comando == "servir":
        porta = args.porta
        if not (0 <= porta <= 65535):
            print(
                "ERRO: porta deve estar em 0-65535 / port must be 0-65535",
                file=sys.stderr,
            )
            return 1

    con = consulta.conexao(":memory:")
    try:
        consulta.carregar(con, leituras)
        resumo = api.montar_resumo(con, tarifa)
        if args.comando == "servir":
            return servidor.main(
                args.porta, api.resumo_json(resumo), relatorio.carregar_template()
            )
        if args.comando == "exportar":
            saida = relatorio.exportar_html(resumo, Path(args.saida))
            print(f"Relatorio em {saida} / Report at {saida}")
            print(
                "Abra o arquivo no navegador (funciona offline, sem CDN) / "
                "Open the file in a browser (works offline, no CDN)"
            )
            return 0
        print(relatorio.resumo_em_texto(resumo))
        return 0
    finally:
        con.close()

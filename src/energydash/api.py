"""Payload agregado do painel (JSON), usado pelo servidor e pelo exportador.
Aggregated dashboard payload (JSON), used by the server and the exporter.

Todo numero sai arredondado para casas fixas, o que torna a saida
deterministica (mesma serie -> mesmo JSON).
Every number is rounded to a fixed number of decimals, which makes the
output deterministic (same series -> same JSON).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

from energydash import consulta, custo, desvio, linha_base, serie


def _arredondar(valor: float, casas: int) -> float:
    """Arredondar de forma deterministica. / Deterministic rounding."""
    return round(valor, casas)


def montar_resumo(
    con: sqlite3.Connection,
    tarifa: custo.Tarifa,
    limiar: float = desvio.LIMIAR_PADRAO,
    margem_minima: float = desvio.MARGEM_MINIMA_PADRAO,
) -> dict:
    """Montar o payload do painel a partir do banco e da tarifa.
    Build the dashboard payload from the database and the tariff.
    """
    leituras = consulta.leituras_periodo(con)
    andares = serie.andares(leituras)
    ini, fim = serie.periodo(leituras)
    dias = (fim.date() - ini.date()).days + 1
    base = linha_base.LinhaBase(leituras)
    desvios = desvio.detectar_desvios(
        leituras, base, limiar=limiar, margem_minima=margem_minima
    )

    total = serie.total_kwh(leituras)
    kwh_ponta, kwh_fora = custo.consumo_por_banda(leituras, tarifa)
    custo_ponta = kwh_ponta * tarifa.preco_ponta
    custo_fora = kwh_fora * tarifa.preco_fora_ponta

    por_andar: dict = {}
    for andar in andares:
        serie_andar = serie.filtrar_por_andar(leituras, andar)
        por_dia = serie.por_dia(serie_andar)
        por_andar[andar] = {
            "kwh": _arredondar(serie.total_kwh(serie_andar), 2),
            "custo": _arredondar(custo.custo_periodo(serie_andar, tarifa), 2),
            "custo_ponta": _arredondar(
                sum(
                    r.kwh
                    for r in serie_andar
                    if custo.banda(tarifa, r.timestamp) == "ponta"
                )
                * tarifa.preco_ponta,
                2,
            ),
            "media_diaria_kwh": _arredondar(
                serie.total_kwh(serie_andar) / len(por_dia), 2
            ),
            "serie_diaria": [
                {"dia": d.isoformat(), "kwh": _arredondar(v, 2)}
                for d, v in sorted(por_dia.items())
            ],
        }

    perfil_horario = {
        andar: [
            _arredondar(v, 3)
            for v in serie.media_por_horario(leituras, andar)
        ]
        for andar in andares
    }

    dias_ponta_txt = "/".join(
        ["seg", "ter", "qua", "qui", "sex", "sab", "dom"][d]
        for d in tarifa.dias_ponta
    )

    return {
        "app": "energy-dashboard-predial",
        "periodo": {
            "inicio": ini.isoformat(timespec="minutes"),
            "fim": fim.isoformat(timespec="minutes"),
            "dias": dias,
        },
        "andares": andares,
        "geral": {
            "total_kwh": _arredondar(total, 2),
            "demanda_kw": _arredondar(custo.demanda_kw(leituras), 2),
            "fator_de_carga": _arredondar(
                custo.fator_de_carga(leituras) or 0.0, 3
            ),
            "desvios": len(desvios),
        },
        "metodo": {
            "linha_base": "mesmo horario da semana anterior + mesmo mes anterior",
            "limiar_percentual": _arredondar(limiar * 100.0, 1),
            "margem_minima_kwh": _arredondar(margem_minima, 2),
        },
        "custo": {
            "moeda": tarifa.moeda,
            "ponta_kwh": _arredondar(kwh_ponta, 2),
            "fora_ponta_kwh": _arredondar(kwh_fora, 2),
            "custo_ponta": _arredondar(custo_ponta, 2),
            "custo_fora_ponta": _arredondar(custo_fora, 2),
            "total_custo": _arredondar(custo_ponta + custo_fora, 2),
            "taxa_fixa_mensal": _arredondar(tarifa.taxa_fixa_mensal, 2),
            "banda_ponta": f"{dias_ponta_txt}, {tarifa.hora_ponta_inicio:02d}h-{tarifa.hora_ponta_fim - 1:02d}h",
        },
        "por_andar": por_andar,
        "perfil_horario": perfil_horario,
        "desvios": [
            {
                "andar": d.andar,
                "inicio": d.inicio.isoformat(timespec="minutes"),
                "fim": d.fim.isoformat(timespec="minutes"),
                "duracao_horas": _arredondar(d.duracao_horas, 1),
                "intervalos": d.intervalos,
                "pico_kwh": _arredondar(d.pico_kwh, 2),
                "pico_percentual": _arredondar(d.pico_percentual, 1),
                "media_percentual": _arredondar(d.media_percentual, 1),
            }
            for d in desvios
        ],
    }


def resumo_json(resumo: dict, indent: Optional[int] = None) -> str:
    """Serializar o payload para JSON deterministico (chaves ordenadas).
    Serialize the payload to deterministic JSON (sorted keys).

    ``</`` vira ``<\\/`` para que o JSON seja seguro dentro de <script>.
    ``</`` becomes ``<\\/`` so the JSON is safe inside <script>.
    """
    texto = json.dumps(
        resumo, ensure_ascii=True, sort_keys=True, default=str, indent=indent
    )
    return texto.replace("</", "<\\/")

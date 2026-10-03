"""Gera os dados ficticios do projeto: serie-consumo.csv e tarifa.yaml.
Generates the project's fictitious data: serie-consumo.csv and tarifa.yaml.

Deterministico: seed fixa e apenas biblioteca padrao; rodar de novo
produz byte a byte os mesmos arquivos.
Deterministic: fixed seed and stdlib only; re-running produces byte-identical
files.

Uso / Usage:
    python tools/gerar_dados.py
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20260601
RAIZ = Path(__file__).resolve().parents[1]
CSV_RELATIVO = "dados/serie-consumo.csv"
TARIFA_RELATIVO = "dados/tarifa.yaml"

DATA_INICIO = datetime(2026, 6, 1, 0, 0)
DIAS = 90
ANDARES = ("andar-1", "andar-2", "andar-3")

# Perfil horario base em kWh por intervalo de 15 min, dias uteis.
# Base hourly profile in kWh per 15-min interval, weekdays.
# andares: 1 = area tecnica (elevadores, bomba, DC), 2 = escritorios,
# 3 = escritorios com ar-condicionado.
# 2026-06-01 e segunda-feira; o periodo cobre 01/06 a 29/08.
# 2026-06-01 is a Monday; the period covers 06/01 to 08/29.
PERFIS = {
    # 0-5: madrugada | 6-9: manha | 10-16: tarde | 17-21: noite | 22-23
    "andar-1": [0.55] * 6 + [0.70] * 4 + [0.85] * 7 + [0.95] * 5 + [0.60] * 2,
    "andar-2": [0.08] * 6 + [0.25] * 3 + [0.45] * 9 + [0.35] * 3 + [0.12] * 3,
    "andar-3": [0.15] * 6 + [0.30] * 3 + [0.55] * 9 + [0.40] * 4 + [0.18] * 2,
}
FATOR_FIM_DE_SEMANA = {
    "andar-1": 0.90,
    "andar-2": 0.45,
    "andar-3": 0.50,
}
RUIDO_SIGMA = 0.08

# Desvios plantados (exatamente tres; documentados em docs/ e no relatorio).
# Planted deviations (exactly three; documented in docs/ and the report).
# 1) andar-2: halogenios ligados fora do horario, sexta 2026-06-26, 20h-23h
# 2) andar-3: ar-condicionado em consumo elevado a noite, oito noites
#    seguidas, de 2026-07-26 22h ate 2026-08-03 05h45 (22h-05h59 por noite)
# 3) andar-1: equipamento tecnico em regime alto de 2026-08-17 ate o fim
#    do periodo (2026-08-29). Planted on the last 13 days: the baseline
#    (previous week + previous month) absorbs a persistent change after
#    about 7 days, so starting the regime earlier would hide part of it.
#    (see docs/metodo-de-linha-base.md)
DESVIO_HALOGENO = {
    "andar": "andar-2",
    "data": datetime(2026, 6, 26).date(),
    "horas": (20, 21, 22),
    "extra_kwh": 3.5,
}
DESVIO_AR = {
    "andar": "andar-3",
    "inicio": datetime(2026, 7, 26, 22, 0),
    "fim": datetime(2026, 8, 3, 5, 45),
    "horas": (22, 23, 0, 1, 2, 3, 4, 5),
    "extra_kwh": 2.2,
}
DESVIO_REGIME_ALTO = {
    "andar": "andar-1",
    "de": datetime(2026, 8, 17).date(),
    "extra_kwh": 2.4,
}


def valor_base(rng: random.Random, andar: str, ts: datetime) -> float:
    """Consumo esperado sem desvio, com ruido gaussiano deterministico.
    Expected consumption without deviation, with deterministic noise.
    """
    valor = float(PERFIS[andar][ts.hour])
    if ts.weekday() >= 5:
        valor *= FATOR_FIM_DE_SEMANA[andar]
    return valor * (1.0 + rng.gauss(0.0, RUIDO_SIGMA))


def desvio_em(andar: str, ts: datetime) -> float:
    """Extra em kWh para os desvios plantados; zero fora deles.
    Extra kWh for the planted deviations; zero elsewhere.
    """
    if (
        andar == DESVIO_HALOGENO["andar"]
        and ts.date() == DESVIO_HALOGENO["data"]
        and ts.hour in DESVIO_HALOGENO["horas"]
    ):
        return DESVIO_HALOGENO["extra_kwh"]
    if (
        andar == DESVIO_AR["andar"]
        and DESVIO_AR["inicio"] <= ts <= DESVIO_AR["fim"]
        and ts.hour in DESVIO_AR["horas"]
    ):
        return DESVIO_AR["extra_kwh"]
    if andar == DESVIO_REGIME_ALTO["andar"] and ts.date() >= DESVIO_REGIME_ALTO["de"]:
        return DESVIO_REGIME_ALTO["extra_kwh"]
    return 0.0


TARIFA_YAML = """# Tarifa ficticia do energy-dashboard-predial.
# Valores inventados para demonstracao; nao usar como referencia comercial.
# Fictitious tariff; invented values for demonstration, not a commercial reference.
moeda: BRL
preco_ponta: 0.9874
preco_fora_ponta: 0.6432
hora_ponta_inicio: "17:00"
hora_ponta_fim: "23:00"
# 0=segunda, 1=terca, ..., 4=sexta (0=Monday, 1=Tuesday, ..., 4=Friday)
dias_ponta: [0, 1, 2, 3, 4]
taxa_fixa_mensal: 78.45
"""


def main() -> int:
    """Gerar CSV e YAML em dados/. / Generate CSV and YAML in dados/."""
    rng = random.Random(SEED)
    linhas: list[tuple[str, str, str]] = []
    for andar in ANDARES:
        for dia in range(DIAS):
            dia_zero = DATA_INICIO + timedelta(days=dia)
            for hora in range(24):
                for quarto in range(4):
                    ts = dia_zero + timedelta(hours=hora, minutes=15 * quarto)
                    valor = valor_base(rng, andar, ts) + desvio_em(andar, ts)
                    linhas.append(
                        (ts.isoformat(timespec="minutes"), andar, f"{valor:.3f}")
                    )

    caminho_csv = RAIZ / CSV_RELATIVO
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    with caminho_csv.open("w", encoding="utf-8", newline="") as arq:
        escritor = csv.writer(arq, lineterminator="\n")
        escritor.writerow(["ts", "andar", "kwh"])
        escritor.writerows(linhas)

    caminho_tarifa = RAIZ / TARIFA_RELATIVO
    caminho_tarifa.parent.mkdir(parents=True, exist_ok=True)
    caminho_tarifa.write_text(TARIFA_YAML, encoding="utf-8", newline="\n")

    print(
        f"Gerados {len(linhas)} intervalos em {CSV_RELATIVO} "
        f"({len(ANDARES)} andares x {DIAS} dias x 96 intervalos)"
    )
    print(f"Tarifa em {TARIFA_RELATIVO}")
    print(
        "Desvios plantados: andar-2 2026-06-26 20h-23h; "
        "andar-3 2026-07-26 22h..2026-08-03 05h45 (oito noites, 22h-05h59); "
        "andar-1 2026-08-17..2026-08-29 (regime alto)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

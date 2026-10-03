"""Consultas em SQLite local (biblioteca padrao sqlite3).
Queries on local SQLite (stdlib sqlite3).

O banco guarda as leituras em uma unica tabela ``leitura(ts, andar, kwh)``.
``ts`` e texto ISO-8601, o que preserva a ordem lexica = ordem cronologica.
The database stores the readings in a single ``leitura(ts, andar, kwh)``
table. ``ts`` is ISO-8601 text, which keeps lexicographic order equal to
chronological order.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Iterable, Optional

from energydash.serie import Leitura, ler_csv

SCHEMA = """
CREATE TABLE IF NOT EXISTS leitura (
    ts TEXT NOT NULL,
    andar TEXT NOT NULL,
    kwh REAL NOT NULL,
    UNIQUE (ts, andar)
);
CREATE INDEX IF NOT EXISTS idx_leitura_andar_ts ON leitura (andar, ts);
CREATE INDEX IF NOT EXISTS idx_leitura_ts ON leitura (ts);
"""


def conexao(banco: str = ":memory:") -> sqlite3.Connection:
    """Abrir (ou criar) o banco e garantir o schema.
    Open (or create) the database and ensure the schema.
    """
    con = sqlite3.connect(banco)
    con.executescript(SCHEMA)
    return con


def carregar(con: sqlite3.Connection, leituras: Iterable[Leitura]) -> int:
    """Inserir leituras; devolver o numero de linhas processadas.
    Insert readings; return the number of processed rows.
    """
    linhas = [
        (r.timestamp.isoformat(timespec="minutes"), r.andar, r.kwh)
        for r in leituras
    ]
    con.executemany(
        "INSERT INTO leitura (ts, andar, kwh) VALUES (?, ?, ?)", linhas
    )
    con.commit()
    return len(linhas)


def carregar_csv(con: sqlite3.Connection, caminho) -> int:
    """Ler o CSV e inserir; devolver o numero de linhas.
    Read the CSV and insert; return the number of rows.
    """
    return carregar(con, ler_csv(caminho))


def total_linhas(con: sqlite3.Connection) -> int:
    """Quantidade de leituras no banco.
    Number of readings in the database.
    """
    return int(con.execute("SELECT COUNT(*) FROM leitura").fetchone()[0])


def andares(con: sqlite3.Connection) -> list[str]:
    """Andares presentes, ordenados.
    Floors present, ordered.
    """
    linhas = con.execute(
        "SELECT DISTINCT andar FROM leitura ORDER BY andar"
    ).fetchall()
    return [linha[0] for linha in linhas]


def min_max(con: sqlite3.Connection) -> Optional[tuple[datetime, datetime]]:
    """(primeiro, ultimo) timestamp do banco; None se vazio.
    (first, last) timestamp of the database; None when empty.
    """
    linha = con.execute("SELECT MIN(ts), MAX(ts) FROM leitura").fetchone()
    if linha is None or linha[0] is None:
        return None
    return datetime.fromisoformat(linha[0]), datetime.fromisoformat(linha[1])


def leituras_periodo(
    con: sqlite3.Connection,
    inicio: Optional[datetime] = None,
    fim: Optional[datetime] = None,
    andar: Optional[str] = None,
) -> list[Leitura]:
    """Leituras no periodo [inicio, fim] e/ou de um andar, em ordem.
    Readings in the range [inicio, fim] and/or for one floor, ordered.
    """
    sql = "SELECT ts, andar, kwh FROM leitura WHERE 1=1"
    params: list = []
    if inicio is not None:
        sql += " AND ts >= ?"
        params.append(inicio.isoformat(timespec="minutes"))
    if fim is not None:
        sql += " AND ts <= ?"
        params.append(fim.isoformat(timespec="minutes"))
    if andar is not None:
        sql += " AND andar = ?"
        params.append(andar)
    sql += " ORDER BY ts, andar"
    linhas = con.execute(sql, params).fetchall()
    return [
        Leitura(
            timestamp=datetime.fromisoformat(linha[0]),
            andar=linha[1],
            kwh=linha[2],
        )
        for linha in linhas
    ]


def consumo_por_dia(
    con: sqlite3.Connection, andar: Optional[str] = None
) -> dict[date, float]:
    """Somar kwh por dia do calendario.
    Sum kwh per calendar day.
    """
    sql = "SELECT date(ts) AS d, SUM(kwh) FROM leitura"
    params: list = []
    if andar is not None:
        sql += " WHERE andar = ?"
        params.append(andar)
    sql += " GROUP BY d ORDER BY d"
    linhas = con.execute(sql, params).fetchall()
    return {date.fromisoformat(linha[0]): linha[1] for linha in linhas}


def consumo_por_andar(con: sqlite3.Connection) -> dict[str, float]:
    """Somar kwh por andar.
    Sum kwh per floor.
    """
    linhas = con.execute(
        "SELECT andar, SUM(kwh) FROM leitura GROUP BY andar ORDER BY andar"
    ).fetchall()
    return {linha[0]: linha[1] for linha in linhas}

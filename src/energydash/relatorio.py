"""Geracao do relatorio HTML offline e do resumo em texto.
Generation of the offline HTML report and the text summary.

O HTML e um arquivo unico (CSS e JS inline, graficos em canvas puro,
sem CDN): abre com duplo clique, mesmo sem internet.
The HTML is a single file (inline CSS and JS, pure-canvas charts, no
CDN): it opens with a double click, even without internet.
"""

from __future__ import annotations

from pathlib import Path


def carregar_template() -> str:
    """Ler o template HTML do pacote.
    Read the HTML template from the package.
    """
    caminho = Path(__file__).parent / "templates" / "dash.html"
    return caminho.read_text(encoding="utf-8")


def gerar_html(resumo: dict, template: str | None = None) -> str:
    """Substituir ``__DADOS__`` no template pelo payload JSON.
    Replace ``__DADOS__`` in the template with the JSON payload.
    """
    base = carregar_template() if template is None else template
    from energydash import api  # import local evita ciclo no pacote inteiro

    if base.count("__DADOS__") != 1:
        raise ValueError(
            "template deve conter exatamente um __DADOS__ / "
            "template must hold exactly one __DADOS__"
        )
    return base.replace("__DADOS__", api.resumo_json(resumo))


def exportar_html(resumo: dict, caminho: str | Path) -> Path:
    """Escrever o HTML no caminho (criando as pastas pai).
    Write the HTML at the path (creating parent folders).
    """
    saida = Path(caminho)
    if saida.parent and not saida.parent.exists():
        saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(gerar_html(resumo), encoding="utf-8", newline="\n")
    return saida


def resumo_em_texto(resumo: dict) -> str:
    """Relatorio em texto para o terminal.
    Text report for the terminal.
    """
    g = resumo["geral"]
    c = resumo["custo"]
    metodo = resumo["metodo"]
    linhas = [
        "RELATORIO DE CONSUMO - energy-dashboard-predial",
        "================================================",
        f'Periodo: {resumo["periodo"]["inicio"][:10]} a '
        f'{resumo["periodo"]["fim"][:10]} ({resumo["periodo"]["dias"]} dias)',
        f'Andares: {len(resumo["andares"])} ({", ".join(resumo["andares"])})',
        f'Total: {g["total_kwh"]:.1f} kWh',
        f'Custo estimado: {c["moeda"]} {c["total_custo"]:.2f} '
        f'(ponta: {c["moeda"]} {c["custo_ponta"]:.2f} | '
        f'fora de ponta: {c["moeda"]} {c["custo_fora_ponta"]:.2f})',
        f'Demanda: {g["demanda_kw"]:.2f} kW | Fator de carga: {g["fator_de_carga"]:.2f}',
        f'Metodo: {metodo["linha_base"]} | '
        f'Limiar: {metodo["limiar_percentual"]:.0f}% acima | '
        f'margem minima {metodo["margem_minima_kwh"]:.2f} kWh',
        "",
        "Consumo por andar:",
    ]
    for andar in resumo["andares"]:
        p = resumo["por_andar"][andar]
        linhas.append(
            f'  {andar}: {p["kwh"]:.1f} kWh | custo {c["moeda"]} {p["custo"]:.2f} '
            f'| media {p["media_diaria_kwh"]:.1f} kWh/dia'
        )
    linhas.append("")
    desvios = resumo["desvios"]
    linhas.append(f'Desvios detectados: {len(desvios)}')
    if not desvios:
        linhas.append("  nenhum / none")
    for i, d in enumerate(desvios, start=1):
        linhas.append(
            f'  {i}. {d["andar"]} | {d["inicio"]} a {d["fim"]} '
            f'({d["duracao_horas"]:.1f} h, {d["intervalos"]} intervalos) | '
            f'pico {d["pico_kwh"]:.2f} kWh '
            f'(+{d["pico_percentual"]:.0f}% da linha de base)'
        )
    return "\n".join(linhas)

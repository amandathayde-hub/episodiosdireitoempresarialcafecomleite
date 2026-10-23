"""Relatório mensal de visitas (GoatCounter), publicado como "issue" no
GitHub: o GitHub avisa a dona do repositório por e-mail.

Uso (no GitHub Actions, dia 1º de cada mês):
    python scripts/relatorio_visitas.py            # mês anterior
    python scripts/relatorio_visitas.py --mes 2026-10

Precisa do segredo GOATCOUNTER_TOKEN (chave só de leitura) e, para publicar,
de GITHUB_TOKEN e GITHUB_REPOSITORY (o GitHub Actions fornece os dois).
Os sites medidos ficam em config.yaml, em "relatorio_visitas". Quando este
arquivo muda, o GitHub faz um teste que só lê as estatísticas (não publica).
"""

import argparse
import calendar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def _get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _contagem(item):
    for chave in ("count", "count_unique", "total"):
        if isinstance(item.get(chave), int):
            return item[chave]
    return 0


def dados_do_site(site, token, inicio, fim):
    """Total, páginas mais vistas, buscas (eventos) e origens do período."""
    base = f"https://{site['codigo']}.goatcounter.com/api/v0"
    q = urllib.parse.urlencode({"start": inicio.isoformat(), "end": fim.isoformat(), "limit": 100})
    total = _get(f"{base}/stats/total?{q}", token)
    hits = _get(f"{base}/stats/hits?{q}", token).get("hits", [])
    try:
        origens = _get(f"{base}/stats/toprefs?{q}", token).get("stats", [])
    except urllib.error.HTTPError:
        origens = []
    paginas = [h for h in hits if not h.get("event")]
    buscas = [h for h in hits if h.get("event") and str(h.get("path", "")).startswith("busca/")]
    return {
        "total": _contagem(total),
        "paginas": sorted(paginas, key=_contagem, reverse=True)[:10],
        "buscas": sorted(buscas, key=_contagem, reverse=True)[:15],
        "origens": sorted(origens, key=_contagem, reverse=True)[:8],
    }


def montar_texto(sites, dados, rotulo_mes, dona):
    linhas = [f"@{dona} segue o relatório de visitas de **{rotulo_mes}**.", ""]
    for site in sites:
        d = dados.get(site["codigo"])
        linhas.append(f"## {site['nome']}")
        if isinstance(d, str):
            linhas += [f"Não foi possível ler as estatísticas: {d}", ""]
            continue
        linhas.append(f"**Visitas no mês:** {d['total']}")
        if d["paginas"]:
            linhas += ["", "**Páginas mais vistas**", "", "| Página | Visitas |", "|---|---|"]
            linhas += [f"| {h.get('title') or h.get('path')} | {_contagem(h)} |" for h in d["paginas"]]
        if d["buscas"]:
            linhas += ["", "**Buscas mais feitas**", "", "| Termo | Vezes |", "|---|---|"]
            linhas += [f"| {str(h.get('path'))[len('busca/'):]} | {_contagem(h)} |" for h in d["buscas"]]
        if d["origens"]:
            linhas += ["", "**De onde vieram**", "", "| Origem | Visitas |", "|---|---|"]
            linhas += [f"| {h.get('name') or '(acesso direto)'} | {_contagem(h)} |" for h in d["origens"]]
        linhas.append("")
    linhas.append("_Relatório automático gerado pelo GitHub Actions a partir do GoatCounter (sem cookies)._")
    return "\n".join(linhas)


def publicar(titulo, corpo):
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues", method="POST",
        data=json.dumps({"title": titulo, "body": corpo}).encode(),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["html_url"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", help="AAAA-MM (padrão: o mês anterior)")
    ap.add_argument("--so-mostrar", action="store_true", help="não publica, só imprime")
    args = ap.parse_args()

    hoje = date.today()
    if args.mes:
        ano, mes = map(int, args.mes.split("-"))
    else:
        ano, mes = (hoje.year, hoje.month - 1) if hoje.month > 1 else (hoje.year - 1, 12)
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    rotulo = f"{MESES[mes - 1]} de {ano}"

    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    rel = config.get("relatorio_visitas") or {}
    sites = rel.get("sites") or []
    token = os.environ.get("GOATCOUNTER_TOKEN", "").strip()
    if not token:
        sys.exit("ERRO: segredo GOATCOUNTER_TOKEN não encontrado")

    dados = {}
    for site in sites:
        try:
            dados[site["codigo"]] = dados_do_site(site, token, inicio, fim)
        except Exception as e:  # noqa: BLE001 - um site com problema não impede os outros
            dados[site["codigo"]] = str(e)[:300]
            print(f"::warning title={site['nome']}::{str(e)[:300]}")

    corpo = montar_texto(sites, dados, rotulo, rel.get("avisar", "amandathayde-hub"))
    for site in sites:
        d = dados[site["codigo"]]
        resumo = d if isinstance(d, str) else (f"{d['total']} visitas; {len(d['paginas'])} páginas; "
                                               f"{len(d['buscas'])} termos buscados; {len(d['origens'])} origens")
        print(f"::notice title={site['nome']}::{resumo}")
    print(corpo)
    if not args.so_mostrar:
        url = publicar(f"Relatório de visitas – {rotulo}", corpo)
        print(f"::notice title=Relatório publicado::{url}")


if __name__ == "__main__":
    main()

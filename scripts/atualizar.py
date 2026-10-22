"""Comando principal: atualiza os dados dos episódios.

Uso:
    python scripts/atualizar.py            # lê o RSS e o YouTube, gera data/episodes.json
    python scripts/atualizar.py --rss arquivo.xml --playlist arquivo.json   # testes offline
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

import rss  # noqa: E402
import youtube  # noqa: E402
from titulos import chave_pessoa, pessoa_natural  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
RELATORIOS = DADOS / "relatorios"
TRANSCRICOES = RAIZ / "transcripts"


def carregar_yaml(nome):
    caminho = RAIZ / nome
    if not caminho.exists():
        return {}
    return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}


def identificar(ep):
    return str(ep["numero"]) if ep["numero"] is not None else f"extra-{ep['data']}"


def aplicar_overrides(episodios, overrides):
    por_ep = {str(k): v for k, v in (overrides.get("episodios") or {}).items()}
    usados = set()
    for ep in episodios:
        o = por_ep.get(ep["id"])
        if not o:
            continue
        usados.add(ep["id"])
        if "numero" in o:
            ep["numero"] = int(o["numero"])
            ep["id"] = str(ep["numero"])
        if "convidados" in o:
            ep["convidados"] = [pessoa_natural(n) for n in o["convidados"]]
            ep["origem_convidado"] = "correcao"
        if "temas" in o:
            ep["temas_manual"] = list(o["temas"])
        if "youtube" in o:
            ep["youtube_manual"] = o["youtube"]
        if o.get("ocultar"):
            ep["oculto"] = True
    return sorted(set(por_ep) - usados)


def unificar_pessoas(episodios, apelidos):
    """Junta grafias da mesma pessoa e guarda todas as variantes para a busca."""
    apelidos = {k.strip(): v.strip() for k, v in (apelidos or {}).items()}
    for ep in episodios:
        for p in ep["convidados"]:
            if p["nome"] in apelidos:
                original = p["nome"]
                p.update(pessoa_natural(apelidos[original]))
                p["variantes_extra"] = [original]

    grupos = {}
    for ep in episodios:
        for p in ep["convidados"]:
            grupos.setdefault(chave_pessoa(p), []).append(p)

    for membros in grupos.values():
        # Forma preferida: a que tem menos iniciais e, depois, a mais completa.
        canonico = max(membros, key=lambda p: (-p["nome"].count("."), -sum(len(w) == 1 and w.isupper() for w in p["nome"].split()),
                                               len(p["nome"]), p["nome"]))
        variantes = set()
        for p in membros:
            variantes.update([p["nome"], p["citacao"], *p.get("variantes_extra", [])])
        for p in membros:
            p["nome"] = canonico["nome"]
            p["citacao"] = canonico["citacao"]
            p["sobrenome"] = canonico["sobrenome"]
            partes = canonico["nome"].split()
            # Forma reduzida "Primeiro Último" para a busca.
            curto = f"{partes[0]} {canonico['sobrenome'].split()[-1]}" if len(partes) > 1 else canonico["nome"]
            variantes.add(curto)
            p["variantes"] = sorted(v for v in variantes if v != canonico["nome"])
            p.pop("variantes_extra", None)


def gravar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rss", help="arquivo XML local em vez de baixar o feed")
    ap.add_argument("--playlist", help="arquivo JSON local com [{id, titulo}]")
    args = ap.parse_args()

    config = carregar_yaml("config.yaml")
    overrides = carregar_yaml("overrides.yaml")

    print("1) Lendo o RSS...")
    xml = Path(args.rss).read_bytes() if args.rss else rss.baixar(config["rss"])
    episodios = rss.ler_feed(xml)
    for ep in episodios:
        ep["id"] = identificar(ep)
    print(f"   {len(episodios)} episódios no feed.")

    sem_uso = aplicar_overrides(episodios, overrides)

    print("2) Lendo a playlist do YouTube...")
    anterior = {}
    arquivo_eps = DADOS / "episodes.json"
    if arquivo_eps.exists():
        anterior = {e["guid"]: e for e in json.loads(arquivo_eps.read_text(encoding="utf-8"))}
    if args.playlist:
        videos = json.loads(Path(args.playlist).read_text(encoding="utf-8"))
    else:
        videos = youtube.listar_playlist(config["playlist_youtube"])
    if videos:
        print(f"   {len(videos)} vídeos na playlist.")
        rel_yt = youtube.casar(episodios, videos)
        gravar_json(RELATORIOS / "youtube.json", rel_yt)
    else:
        print("   YouTube indisponível: mantendo os links da última execução.")
        for ep in episodios:
            antes = anterior.get(ep["guid"], {})
            ep["youtube"] = antes.get("youtube")
            # Mantém o número que tinha sido descoberto pelo YouTube.
            if ep["numero"] is None and antes.get("numero") is not None:
                ep["numero"], ep["id"] = antes["numero"], antes["id"]
    for ep in episodios:
        if ep.get("youtube_manual"):
            ep["youtube"] = ep.pop("youtube_manual")

    unificar_pessoas(episodios, overrides.get("pessoas"))

    for ep in episodios:
        ep["transcricao"] = "ok" if (TRANSCRICOES / f"{ep['id']}.txt").exists() else "pendente"

    ids = [e["id"] for e in episodios]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})

    gravar_json(arquivo_eps, episodios)
    gravar_json(RELATORIOS / "titulos.json", {
        "convidado_pela_descricao": [{"id": e["id"], "titulo": e["titulo"],
                                      "convidados": [p["nome"] for p in e["convidados"]]}
                                     for e in episodios if e["origem_convidado"] == "descricao"],
        "atribuidos_a_apresentadora": [{"id": e["id"], "titulo": e["titulo"]}
                                       for e in episodios if e["origem_convidado"] == "apresentadora"],
        "sem_numero": [{"id": e["id"], "titulo": e["titulo"]} for e in episodios if e["numero"] is None],
        "ids_repetidos": repetidos,
        "correcoes_nao_usadas": sem_uso,
    })

    pendentes = sum(e["transcricao"] == "pendente" for e in episodios)
    print(f"3) Pronto: {len(episodios)} episódios em data/episodes.json "
          f"({pendentes} com transcrição pendente).")
    if repetidos:
        print(f"   ATENÇÃO: identificadores repetidos: {repetidos}")


if __name__ == "__main__":
    main()

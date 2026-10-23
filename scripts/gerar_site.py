"""Gera o site estático em site/ a partir de data/episodes.json e transcripts/.

Páginas: início (busca), uma por episódio, convidados, 404, sitemap.xml e
robots.txt. Depois disso o workflow roda o Pagefind, que cria o índice de
busca em site/pagefind/.

Uso: python scripts/gerar_site.py
"""

import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from temas import trechos_padrao  # noqa: E402
from titulos import sem_acentos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "site"
AVISO_TRANSCRICAO = "Transcrição automática, pode conter erros, especialmente em nomes próprios."
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]

e = html.escape


def data_por_extenso(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def duracao_legivel(seg):
    if not seg:
        return ""
    h, m = seg // 3600, round(seg % 3600 / 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def duracao_iso(seg):
    return f"PT{seg // 3600}H{seg % 3600 // 60}M{seg % 60}S" if seg else None


def ancora(nome):
    s = sem_acentos(nome).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def titulo_curto(ep):
    """O nome da obra, sem a referência bibliográfica (cidade, editora, ano)."""
    obra = ep.get("obra") or ep["titulo"]
    curto = re.split(r"\.\s+(?:[A-ZÀ-Ú][\wÀ-ú ]+:\s|In:|Revista|São Paulo|Rio de Janeiro|Belo Horizonte|Brasília|Ed\.|Editora)", obra)[0]
    return curto.rstrip(" .")


def link_youtube(ep, cfg):
    """Vídeo do episódio; se não foi encontrado, a busca pelo título no canal."""
    if ep.get("youtube"):
        return f"https://www.youtube.com/watch?v={ep['youtube']}"
    canal = cfg["youtube_canal"].rsplit("/", 1)[0]
    return f"{canal}/search?query={quote(titulo_curto(ep))}"


def rotulo(ep):
    return f"#{ep['numero']}" if ep["numero"] is not None else "Especial"


def nomes(pessoas):
    return ", ".join(p["nome"] for p in pessoas)


def resumo(ep, limite=155):
    texto = ep.get("descricao") or ep["titulo"]
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto if len(texto) <= limite else texto[: limite - 1].rsplit(" ", 1)[0] + "…"


# ---------------------------------------------------------------- moldura

def pagina(cfg, *, titulo, descricao, caminho, raiz, corpo, extra_head="", tipo_og="website", busca_ativa=False,
           convidados_ativa=False):
    url = cfg["url"].rstrip("/") + "/" + caminho
    imagem = cfg["url"].rstrip("/") + "/capa.jpg"
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descricao)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{tipo_og}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{e(cfg['nome_podcast'])}">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descricao)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(imagem)}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#660D44">
<link rel="icon" href="{raiz}static/icone.png">
<link rel="preload" href="{raiz}static/fontes/archivo-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{raiz}static/estilo.css">
{extra_head}
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo">
  <div class="topo-interno">
    <a class="marca" href="{raiz}" aria-label="Início – busca de episódios">
      <img src="{raiz}static/logo.webp" alt="Direito Empresarial Café com Leite" width="511" height="288">
    </a>
    <nav aria-label="Principal">
      <a href="{e(cfg['site_principal'])}">Site do podcast</a>
      <a href="{raiz}"{' aria-current="page"' if busca_ativa else ''}>Episódios</a>
      <a href="{raiz}convidados/"{' aria-current="page"' if convidados_ativa else ''}>Convidados</a>
    </nav>
  </div>
</header>
<main id="conteudo">
{corpo}
</main>
<footer class="rodape">
  <p>{e(cfg['nome_podcast'])}, com a Profa. Amanda Athayde · desde julho de 2021</p>
  <p>
    <a href="{e(cfg['spotify_programa'])}">Spotify</a> ·
    <a href="{e(cfg['youtube_canal'])}">YouTube</a> ·
    <a href="{e(cfg['site_principal'])}">Site do podcast</a>
  </p>
  <p class="discreto">Este site não usa cookies. As transcrições são automáticas e podem conter erros.</p>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- episódio

def transcricao_html(texto):
    """Parágrafos com [mm:ss] clicável. Abertura, anúncio e encerramento
    padrão ficam marcados para o Pagefind ignorar."""
    trechos = sorted(trechos_padrao(texto))
    pos, paragrafos, dentro = 0, [], False
    for bruto in texto.split("\n\n"):
        inicio_par = texto.find(bruto, pos)
        fim_par = inicio_par + len(bruto)
        pos = fim_par
        # Pontos de corte dentro deste parágrafo.
        cortes = sorted({max(inicio_par, min(fim_par, x)) for a, b in trechos for x in (a, b)
                         if inicio_par <= x <= fim_par} | {inicio_par, fim_par})
        partes = []
        for a, b in zip(cortes, cortes[1:]):
            pedaco = texto[a:b]
            ignorar = any(ta <= a and b <= tb for ta, tb in trechos)
            pedaco_html = e(pedaco)
            pedaco_html = re.sub(
                r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]",
                r'<button type="button" class="tempo" data-pagefind-ignore data-tempo="\1">\1</button>',
                pedaco_html)
            partes.append(f'<span class="padrao" data-pagefind-ignore>{pedaco_html}</span>' if ignorar else pedaco_html)
        if bruto.strip():
            paragrafos.append(f"<p>{''.join(partes)}</p>")
    del dentro
    return "\n".join(paragrafos)


def pagina_episodio(ep, cfg, pasta_trans, ordem):
    raiz = "../../"
    caminho = f"episodio/{ep['id']}/"
    arquivo = pasta_trans / f"{ep['id']}.txt"
    texto = arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""
    titulo = titulo_curto(ep)
    pessoas = ep["convidados"]

    conv_html = ", ".join(f'<a href="{raiz}convidados/#{ancora(p["nome"])}">{e(p["nome"])}</a>' for p in pessoas)
    variantes = sorted({v for p in pessoas + ep.get("autores", []) for v in p.get("variantes", [])})
    autores_html = ""
    if ep.get("autores"):
        autores_html = f'<p class="autores">Obra de: {e(nomes(ep["autores"]))}</p>'
    temas_html = "".join(
        f'<li><a class="etiqueta" href="{raiz}?tema={quote(t)}" data-pagefind-filter="tema">{e(t)}</a></li>'
        for t in ep.get("temas", []))

    botoes = []
    if ep.get("spotify"):
        botoes.append(f'<a class="botao spotify" href="{e(ep["spotify"])}">Ouvir no Spotify</a>')
    botoes.append(f'<a class="botao youtube" href="{e(link_youtube(ep, cfg))}">Assistir no YouTube</a>')

    video = ""
    if ep.get("youtube"):
        video = f"""
  <div class="video" data-youtube="{e(ep['youtube'])}">
    <button type="button" class="video-capa" aria-label="Carregar o vídeo do YouTube deste episódio">
      <img src="https://i.ytimg.com/vi/{e(ep['youtube'])}/hqdefault.jpg" alt="" loading="lazy" width="480" height="360">
      <span>▶ Ver o vídeo aqui</span>
    </button>
  </div>"""
    audio = f'<audio class="player" controls preload="none" src="{e(ep["mp3"])}"></audio>' if ep.get("mp3") else ""

    if texto:
        trans = f"""
  <details class="transcricao">
    <summary>Ler a transcrição completa</summary>
    <p class="aviso" data-pagefind-ignore>{AVISO_TRANSCRICAO} Clique no horário para ouvir aquele trecho.</p>
    <div class="texto">{transcricao_html(texto)}</div>
  </details>"""
    else:
        trans = '<p class="pendente">Transcrição pendente: ficará disponível em breve.</p>'

    anterior, proximo = ordem
    navegacao = '<nav class="vizinhos" aria-label="Outros episódios">'
    if proximo:
        navegacao += f'<a href="{raiz}episodio/{proximo["id"]}/">← {e(rotulo(proximo))} (mais novo)</a>'
    if anterior:
        navegacao += f'<a href="{raiz}episodio/{anterior["id"]}/">{e(rotulo(anterior))} (mais antigo) →</a>'
    navegacao += "</nav>"

    ld = {
        "@context": "https://schema.org",
        "@type": "PodcastEpisode",
        "name": f"{rotulo(ep)}: {titulo}",
        "url": cfg["url"].rstrip("/") + "/" + caminho,
        "datePublished": ep["data"],
        "description": resumo(ep, 500),
        "inLanguage": "pt-BR",
        "partOfSeries": {"@type": "PodcastSeries", "name": cfg["nome_podcast"], "url": cfg["site_principal"]},
        "actor": [{"@type": "Person", "name": p["nome"]} for p in pessoas],
    }
    if ep["numero"] is not None:
        ld["episodeNumber"] = ep["numero"]
    if ep.get("duracao_seg"):
        ld["timeRequired"] = duracao_iso(ep["duracao_seg"])
    if ep.get("mp3"):
        ld["associatedMedia"] = {"@type": "MediaObject", "contentUrl": ep["mp3"]}
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n' \
            f'<script src="{raiz}static/episodio.js" defer></script>'

    corpo = f"""
<article class="episodio" data-pagefind-body>
  <p class="voltar" data-pagefind-ignore><a href="{raiz}">← Voltar para a busca</a></p>
  <p class="meta-topo" data-pagefind-ignore>
    <span class="numero">{e(rotulo(ep))}</span>
    <time datetime="{ep['data']}">{data_por_extenso(ep['data'])}</time>
    {'· ' + duracao_legivel(ep.get('duracao_seg')) if ep.get('duracao_seg') else ''}
  </p>
  <h1>{e(titulo)}</h1>
  <p class="convidados" data-pagefind-weight="6">{conv_html}</p>
  <p class="so-leitor" aria-hidden="true" data-pagefind-weight="4">{e(' · '.join(variantes))}</p>
  {autores_html}
  <p class="referencia">{e(ep['titulo'])}</p>
  <ul class="temas" aria-label="Temas">{temas_html}</ul>
  <span data-pagefind-filter="ano" hidden>{ep['data'][:4]}</span>
  <span data-pagefind-meta="id" hidden>{e(ep['id'])}</span>
  <div class="ouvir" data-pagefind-ignore>
    {audio}
    <div class="botoes">{''.join(botoes)}</div>
    {video}
  </div>
  <section class="descricao">
    <h2 id="descricao">Sobre o episódio</h2>
    {''.join(f'<p>{e(p)}</p>' for p in (ep.get('descricao') or '').split(chr(10) + chr(10)) if p.strip())}
  </section>
  <section>
    <h2 id="transcricao">Transcrição</h2>
    {trans}
  </section>
  {navegacao}
</article>"""
    descricao = f"{rotulo(ep)} do podcast {cfg['nome_podcast']}, com {nomes(pessoas)}: {titulo}"
    return caminho, pagina(cfg, titulo=f"{rotulo(ep)}: {titulo} – {nomes(pessoas)}",
                           descricao=descricao[:300], caminho=caminho, raiz=raiz, corpo=corpo,
                           extra_head=extra, tipo_og="article")


# ---------------------------------------------------------------- início

def pagina_inicio(cfg, episodios, grupos_temas):
    anos = sorted({ep["data"][:4] for ep in episodios}, reverse=True)
    op_anos = "".join(f'<option value="{a}">{a}</option>' for a in anos)
    op_temas = ""
    for grupo, temas in grupos_temas.items():
        op_temas += f'<optgroup label="{e(grupo)}">' + "".join(
            f'<option value="{e(t)}">{e(t)}</option>' for t in temas) + "</optgroup>"
    horas = round(sum(ep.get("duracao_seg") or 0 for ep in episodios) / 3600)
    corpo = f"""
<section class="busca" aria-labelledby="titulo-busca">
  <h1 id="titulo-busca">Busque entre os {len(episodios)} episódios</h1>
  <p class="subtitulo">Procure por título, convidado, tema ou qualquer assunto falado nas conversas. São cerca de {horas} horas de Direito Empresarial.</p>
  <form class="caixa" role="search" action="./" onsubmit="return false">
    <label for="q" class="so-leitor">O que você procura?</label>
    <input id="q" name="q" type="search" placeholder="Ex.: business judgment rule, Forgioni, recuperação judicial" autocomplete="off" enterkeyhint="search">
  </form>
  <div class="filtros">
    <label>Ano
      <select id="ano"><option value="">Todos</option>{op_anos}</select>
    </label>
    <label>Tema
      <select id="tema"><option value="">Todos</option>{op_temas}</select>
    </label>
    <button type="button" id="limpar" class="link">Limpar filtros</button>
  </div>
</section>
<section aria-labelledby="titulo-resultados">
  <h2 id="titulo-resultados" class="so-leitor">Resultados</h2>
  <p id="contagem" class="contagem" aria-live="polite"></p>
  <ol id="resultados" class="resultados"></ol>
  <button type="button" id="mais" class="botao secundario" hidden>Mostrar mais</button>
  <noscript><p>Para buscar, ative o JavaScript. Você também pode ver a <a href="convidados/">lista de convidados</a>.</p></noscript>
</section>"""
    extra = '<script src="static/busca.js" defer></script>'
    return pagina(cfg, titulo=cfg["titulo"], caminho="", raiz="", corpo=corpo, extra_head=extra, busca_ativa=True,
                  descricao=f"Busca nos {len(episodios)} episódios do podcast {cfg['nome_podcast']}, "
                            f"com a Profa. Amanda Athayde: por título, convidado, tema e transcrição.")


# ---------------------------------------------------------------- convidados

def chave_ordem(p):
    """Ordem alfabética pelo nome pessoal (primeiro nome)."""
    return sem_acentos(p["nome"]).lower()


def pagina_convidados(cfg, episodios):
    raiz = "../"
    pessoas = {}
    autores = {}
    for ep in episodios:
        for p in ep["convidados"]:
            pessoas.setdefault(p["nome"], {"p": p, "eps": []})["eps"].append(ep)
        for p in ep.get("autores", []):
            if p["nome"] not in {c["nome"] for c in ep["convidados"]}:
                autores.setdefault(p["nome"], {"p": p, "eps": []})["eps"].append(ep)

    def lista(dic, prefixo):
        itens = sorted(dic.values(), key=lambda x: chave_ordem(x["p"]))
        letras, blocos, atual = [], [], None
        for item in itens:
            letra = sem_acentos(item["p"]["nome"][:1]).upper() or "#"
            if letra != atual:
                if atual is not None:
                    blocos.append("</ul>")
                blocos.append(f'<h3 id="{prefixo}-{letra}">{letra}</h3><ul class="pessoas">')
                letras.append(letra)
                atual = letra
            links = ", ".join(
                f'<a href="{raiz}episodio/{x["id"]}/" title="{e(titulo_curto(x))}">{e(rotulo(x))}</a>'
                for x in sorted(item["eps"], key=lambda x: x["data"]))
            nome = item["p"]["nome"]
            blocos.append(f'<li id="{ancora(nome)}"><span class="nome">{e(nome)}</span> <span class="eps">{links}</span></li>')
        if atual is not None:
            blocos.append("</ul>")
        indice = " ".join(f'<a href="#{prefixo}-{x}">{x}</a>' for x in letras)
        return f'<nav class="letras" aria-label="Ir para a letra">{indice}</nav>' + "".join(blocos)

    corpo = f"""
<section class="pagina-convidados">
  <h1>Convidados</h1>
  <p class="subtitulo">{len(pessoas)} pessoas participaram do podcast, em ordem alfabética pelo nome. Clique no número para abrir o episódio.</p>
  {lista(pessoas, 'c')}
  <h2>Autores das obras comentadas</h2>
  <p class="subtitulo">Autores de obras discutidas por outros convidados.</p>
  {lista(autores, 'a')}
</section>"""
    return pagina(cfg, titulo=f"Convidados – {cfg['nome_podcast']}", caminho="convidados/", raiz=raiz, corpo=corpo,
                  convidados_ativa=True,
                  descricao=f"Lista dos {len(pessoas)} convidados do podcast {cfg['nome_podcast']}, com links para os episódios.")


# ---------------------------------------------------------------- principal

def main():
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    cfg = dict(config["site"])
    temas_cfg = yaml.safe_load((RAIZ / "temas.yaml").read_text(encoding="utf-8")) or {}
    grupos_temas = {g: list((t or {}).keys()) for g, t in (temas_cfg.get("grupos") or {}).items()}
    episodios = [ep for ep in json.loads((RAIZ / "data" / "episodes.json").read_text(encoding="utf-8"))
                 if not ep.get("oculto")]
    episodios.sort(key=lambda ep: ep["data"], reverse=True)
    pasta_trans = RAIZ / "transcripts"

    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    (SAIDA / "static").mkdir(parents=True)
    for item in (RAIZ / "static").iterdir():
        destino = SAIDA / "static" / item.name
        shutil.copytree(item, destino) if item.is_dir() else shutil.copy2(item, destino)

    def gravar(caminho, conteudo):
        alvo = SAIDA / caminho / "index.html" if not caminho.endswith((".html", ".xml", ".txt", ".json")) else SAIDA / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")

    urls = [("", date.today().isoformat()), ("convidados/", date.today().isoformat())]
    for i, ep in enumerate(episodios):
        mais_novo = episodios[i - 1] if i > 0 else None
        mais_antigo = episodios[i + 1] if i + 1 < len(episodios) else None
        caminho, conteudo = pagina_episodio(ep, cfg, pasta_trans, (mais_antigo, mais_novo))
        gravar(caminho, conteudo)
        urls.append((caminho, ep["data"]))

    gravar("", pagina_inicio(cfg, episodios, grupos_temas))
    gravar("convidados/", pagina_convidados(cfg, episodios))
    gravar("404.html", pagina(cfg, titulo="Página não encontrada", descricao="Página não encontrada.",
                              caminho="404.html", raiz=urlparse(cfg["url"]).path.rstrip("/") + "/",
                              corpo='<section><h1>Página não encontrada</h1><p><a href="./">Voltar para a busca</a></p></section>'))

    # Lista leve para a página inicial (mostrar e filtrar sem digitar nada).
    lista = [{
        "id": ep["id"], "r": rotulo(ep), "t": titulo_curto(ep), "c": nomes(ep["convidados"]),
        "d": ep["data"], "dx": data_por_extenso(ep["data"]), "du": duracao_legivel(ep.get("duracao_seg")),
        "te": ep.get("temas", []), "yt": link_youtube(ep, cfg), "sp": ep.get("spotify"),
        "tr": ep.get("transcricao") == "ok",
    } for ep in episodios]
    gravar("static/episodios.json", json.dumps(lista, ensure_ascii=False, separators=(",", ":")))

    base = cfg["url"].rstrip("/") + "/"
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{e(base + c)}</loc><lastmod>{d}</lastmod></url>" for c, d in urls]
    sitemap.append("</urlset>")
    gravar("sitemap.xml", "\n".join(sitemap) + "\n")
    gravar("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n")
    # Capa para compartilhamento; se não der para baixar, usa o logo.
    try:
        import urllib.request
        with urllib.request.urlopen(cfg["capa"], timeout=60) as r:
            (SAIDA / "capa.jpg").write_bytes(r.read())
    except Exception:  # noqa: BLE001
        shutil.copy2(RAIZ / "static" / "icone.png", SAIDA / "capa.jpg")
    if cfg.get("dominio"):
        (SAIDA / "CNAME").write_text(cfg["dominio"].strip() + "\n", encoding="utf-8")
    (SAIDA / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Site gerado em site/: {len(episodios)} episódios, "
          f"{sum(1 for ep in episodios if ep.get('transcricao') == 'ok')} com transcrição.")


if __name__ == "__main__":
    main()

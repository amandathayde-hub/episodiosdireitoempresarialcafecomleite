"""Leitura do feed RSS do podcast."""

import email.utils
import html
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

from titulos import interpretar, limpar_titulo

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

# Rodapé repetido nas descrições: tudo a partir daqui é removido.
_RODAPE = re.compile(r"👩‍?⚖️?\s*Profa\.?\s*Amanda Athayde.*$", re.DOTALL)


def baixar(url, tentativas=4):
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "episodios-cafecomleite/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - qualquer falha de rede
            erro = e
            import time
            time.sleep(2 ** (i + 1))
    raise RuntimeError(f"Não consegui baixar {url}: {erro}")


def html_para_texto(conteudo):
    """Converte o HTML da descrição em texto com parágrafos."""
    t = conteudo or ""
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</p\s*>", "\n\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = unicodedata.normalize("NFC", t)
    t = _RODAPE.sub("", t)
    t = re.sub(r"[ \t ]+", " ", t)
    t = re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", t)
    return t.strip()


def _segundos(duracao):
    if not duracao:
        return None
    try:
        total = 0
        for parte in duracao.strip().split(":"):
            total = total * 60 + int(float(parte))
        return total
    except ValueError:
        return None


def ler_feed(xml_bytes):
    """Devolve a lista de episódios do feed, do mais novo para o mais antigo."""
    raiz = ET.fromstring(xml_bytes)
    episodios = []
    for item in raiz.findall("channel/item"):
        titulo = limpar_titulo(item.findtext("title"))
        descricao = html_para_texto(item.findtext("description"))
        info = interpretar(titulo, descricao)
        data = email.utils.parsedate_to_datetime(item.findtext("pubDate"))
        enclosure = item.find("enclosure")
        episodios.append({
            "guid": (item.findtext("guid") or "").strip(),
            "numero": info["numero"],
            "titulo": titulo,
            "convidados": info["convidados"],
            "origem_convidado": info["origem_convidado"],
            "obra": info["obra"],
            "ano_obra": info["ano_obra"],
            "data": data.date().isoformat(),
            "duracao_seg": _segundos(item.findtext(f"{ITUNES}duration")),
            "descricao": descricao,
            "spotify": (item.findtext("link") or "").strip(),
            "mp3": enclosure.get("url") if enclosure is not None else None,
        })
    return episodios

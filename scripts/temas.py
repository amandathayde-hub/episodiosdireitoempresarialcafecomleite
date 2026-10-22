"""Classificação automática dos episódios em temas (ver temas.yaml)."""

import re

from titulos import sem_acentos


def _normalizar(texto):
    return " " + re.sub(r"\s+", " ", sem_acentos(texto or "").lower()) + " "


def _inicio_da_frase(texto, pos):
    """Recua até o começo da frase (ou até depois da marcação [mm:ss])."""
    corte = max(texto.rfind(". ", 0, pos), texto.rfind("? ", 0, pos), texto.rfind("] ", 0, pos))
    return corte + 2 if corte != -1 and pos - corte < 60 else pos


def trechos_padrao(transcricao):
    """Trechos que se repetem em todos os episódios e não devem contar para a
    busca nem para os temas: abertura, anúncio do meio e encerramento.
    Devolve uma lista de (inicio, fim) em caracteres."""
    if not transcricao:
        return []
    # sem_acentos preserva o tamanho do texto, então as posições batem.
    texto = sem_acentos(transcricao).lower()
    n = len(texto)
    trechos = []
    m = re.search(r"xicara de cafe com leite de direito empresarial de hoje", texto)
    if m and m.start() < n * 0.2:
        trechos.append((0, _inicio_da_frase(texto, m.start())))
    for m in re.finditer(r"segura so um pouquinho que eu (ja )?volto", texto):
        volta = re.compile(r"vamos voltar (para|pra) (a )?nossa conversa[^.?!]*[.?!]")
        fim = volta.search(texto, m.end(), m.end() + 2500)
        if fim:
            trechos.append((_inicio_da_frase(texto, m.start()), fim.end()))
    for m in re.finditer(r"xicara de cafe com leite (foi|ja foi|esta) devidamente tomada", texto):
        if m.start() > n * 0.7:
            trechos.append((_inicio_da_frase(texto, m.start()), n))
            break
    return trechos


def texto_da_conversa(transcricao):
    """A transcrição sem os trechos padrão."""
    partes, pos = [], 0
    for inicio, fim in sorted(trechos_padrao(transcricao)):
        partes.append(transcricao[pos:inicio])
        pos = max(pos, fim)
    partes.append(transcricao[pos:])
    return " ".join(partes)


def carregar(config_temas):
    grupos = config_temas.get("grupos") or {}
    minimo = int(config_temas.get("minimo_na_transcricao", 8))
    regras = []
    for grupo, temas in grupos.items():
        for tema, palavras in (temas or {}).items():
            padroes = [re.compile(r"(?<![a-z0-9])" + re.escape(sem_acentos(str(p)).lower()) + r"(?![a-z0-9])")
                       for p in palavras or []]
            regras.append({"grupo": grupo, "tema": tema, "padroes": padroes})
    return regras, minimo


def classificar(ep, transcricao, regras, minimo):
    metadados = _normalizar(" ".join([ep["titulo"], ep.get("obra", ""), ep.get("descricao", "")]))
    conversa = _normalizar(texto_da_conversa(transcricao)) if transcricao else ""
    temas = []
    for r in regras:
        if any(p.search(metadados) for p in r["padroes"]):
            temas.append(r["tema"])
        elif conversa and sum(len(p.findall(conversa)) for p in r["padroes"]) >= minimo:
            temas.append(r["tema"])
    return temas


def aplicar(episodios, pasta_transcricoes, config_temas):
    regras, minimo = carregar(config_temas)
    for ep in episodios:
        if ep.get("temas_manual") is not None:
            ep["temas"] = ep["temas_manual"]
            continue
        arquivo = pasta_transcricoes / f"{ep['id']}.txt"
        texto = arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""
        ep["temas"] = classificar(ep, texto, regras, minimo)
    return [{"grupo": r["grupo"], "tema": r["tema"]} for r in regras]

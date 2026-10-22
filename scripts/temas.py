"""Classificação automática dos episódios em temas (ver temas.yaml)."""

import re

from titulos import sem_acentos


def _normalizar(texto):
    return " " + re.sub(r"\s+", " ", sem_acentos(texto or "").lower()) + " "


def trecho_da_conversa(transcricao):
    """Tira a abertura e o encerramento padrão do podcast, que se repetem em
    todos os episódios e atrapalhariam a busca e os temas.
    Devolve (inicio, fim) em caracteres; se não reconhecer, devolve tudo."""
    if not transcricao:
        return 0, 0
    texto = sem_acentos(transcricao).lower()
    n = len(texto)
    inicio, fim = 0, n
    abertura = [m.start() for m in re.finditer(r"(a nossa )?xicara de cafe com leite de direito empresarial de hoje", texto)]
    if abertura and abertura[0] < n * 0.2:
        inicio = abertura[0]
        # Volta até o começo da frase, preservando a marcação [mm:ss].
        ponto = max(texto.rfind(". ", 0, inicio), texto.rfind("] ", 0, inicio))
        if ponto != -1 and inicio - ponto < 40:
            inicio = ponto + 2
    for m in re.finditer(r"xicara de cafe com leite (foi|ja foi|esta) devidamente tomada", texto):
        if m.start() > n * 0.7:
            frase = max(texto.rfind(". ", 0, m.start()), texto.rfind("] ", 0, m.start()))
            fim = frase + 2 if frase != -1 else m.start()
            break
    return inicio, fim


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
    inicio, fim = trecho_da_conversa(transcricao)
    conversa = _normalizar(transcricao[inicio:fim]) if transcricao else ""
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

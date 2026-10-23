"""Interpretação dos títulos dos episódios.

Fórmula padrão (episódios novos):
    #N: SOBRENOME, Nome; SOBRENOME2, Nome2. Título da obra. Cidade: Editora, Ano.
    #N: ATHAYDE, Amanda. Aula ao vivo – Tema da aula.

Também aceita as variações encontradas no feed antigo: "EP #1:", "#EP99:",
"EP116:", "#EP 245:", "EP#200:", "A #308:", "#296: EPXX:", autores separados
por ". " / " e " / " - ", iniciais ("PARGENDLER, M."), "et al.", "(org.)",
prenome em caixa alta, sobrenome só com inicial maiúscula no começo
("Sampaio, Gisela."), nomes em ordem natural ("Ivo Waisberg comenta ...",
"Nicole Bromberg. Título") e "SOBRENOME e SOBRENOME.".

Quando nada disso aparece, o convidado é procurado na descrição
("Fulana de Tal comenta ..."); se ainda assim não houver, o episódio fica
atribuído à apresentadora (ex.: "Aula Ao Vivo - ...").
"""

import re
import unicodedata

APRESENTADORA = "Amanda Athayde"

_INVISIVEIS = re.compile(r"[​-‏⁠﻿]")
_SUFIXO_CANAL = re.compile(r"\s*\|\s*Direito Empresarial Caf.*$", re.IGNORECASE)

_NUMERO = re.compile(
    r"^\s*(?:A\s+)?(?:#\s*EP|EP\s*#|EP|#)\s*(\d{1,4})\s*[:.\-–]?\s*(?:EP\s*X+\s*:\s*)?",
    re.IGNORECASE,
)

_MAI = "A-ZÀ-ÖØ-Þ"
_MIN = "a-zß-öø-ÿ"
_PART = r"(?:de|da|do|dos|das|del|di|van|von|e)"
_PALAVRA = rf"[{_MAI}][{_MIN}]+(?:['’\-][{_MAI}]?[{_MIN}]+)*"
_INICIAL = rf"[{_MAI}]\."
_LETRA = rf"[{_MAI}](?=\s)"  # inicial sem ponto: "Angelo G Prata"
_ITEM = rf"(?:{_PALAVRA}|{_LETRA})"
# Prenome: palavras (com partículas no meio), opcionalmente seguidas de
# iniciais ("Ricardo V. B."), ou só iniciais ("A. O.").
_PRENOME = (
    rf"(?:{_ITEM}(?:\s+(?:{_PART}\s+)?{_ITEM})*(?:\s+{_PART}(?=\s*[.;,]))?"
    rf"(?:\s+(?:{_PART}\s+)?{_INICIAL}(?:\s?(?:{_PART}\s+)?{_INICIAL})*)?"
    rf"|{_INICIAL}(?:\s?{_INICIAL})*)"
)
_PRENOME_CAIXA_ALTA = rf"[{_MAI}]{{2,}}(?:\s+[{_MAI}]{{2,}})*(?=\s*\.)"
_SOBRENOME = rf"[{_MAI}][{_MAI}'’\-]+(?:\s+[{_MAI}][{_MAI}'’\-]*)*"
_SOBRENOME_TITULO = rf"[{_MAI}][{_MIN}'’\-]+"  # "Sampaio", só no início

_AUTOR = re.compile(
    rf"\s*(?P<sobrenome>{_SOBRENOME})\s*,\s*"
    rf"(?P<prenome>{_PRENOME}|{_PRENOME_CAIXA_ALTA})"
    rf"(?P<etal>\s+et\s+al\.?)?"
    rf"(?:\s*\((?:orgs?|coords?|eds?)\.?\))?"
)
_AUTOR_INICIO = re.compile(
    rf"\s*(?P<sobrenome>{_SOBRENOME_TITULO})\s*,\s*(?P<prenome>{_PRENOME})(?=\s*\.)"
)
_SO_SOBRENOMES = re.compile(rf"\s*(?P<a>{_SOBRENOME})\s+e\s+(?P<b>{_SOBRENOME})\s*\.\s*")
# Nome em ordem natural ("Ivo Waisberg"). O "e" fica de fora das partículas
# para "Fulano e Beltrana" serem lidos como duas pessoas.
_PART_NATURAL = r"(?:de|da|do|dos|das|del|di|van|von)"
_NOME_NATURAL = rf"{_PALAVRA}(?:\s+(?:{_PART_NATURAL}\s+)?{_PALAVRA}){{1,5}}"
_NATURAL = re.compile(
    rf"\s*(?:Prof(?:a|essora|essor)?\.?\s+)?(?P<a>{_NOME_NATURAL})"
    rf"(?:\s+e\s+(?P<b>{_NOME_NATURAL}))?"
    rf"(?P<comenta>\s*,?\s*comenta\b(?:\s+sobre\b)?\s*:?)?"
)
_SEPARADOR = re.compile(rf"\s*(?:[;.:,](?:\s*e\s+(?={_SOBRENOME}\s*,))?|\s[-–]\s|\s+e\s+(?={_SOBRENOME}\s*,))\s*(?:[;.]\s*)*")
_PROXIMO_AUTOR = re.compile(rf"\s+(?={_SOBRENOME}\s*,)")
_COMENTA_DESCRICAO = re.compile(
    rf"^\s*(?:(?:A|O)\s+(?:advogad[ao]|professor[a]?|autor[a]?)\s+)?"
    rf"(?:Prof(?:a|essora|essor)?\.?\s+)?(?P<nome>{_NOME_NATURAL}(?:\s*(?:,|\be\b)\s*{_NOME_NATURAL})*)\s*,?\s+comentam?\b"
)

# Palavras que, no início do título, indicam que não é um nome de pessoa.
_NAO_SAO_NOMES = {"Aula", "Ao", "Vivo", "Encerramento", "Lei", "Leis", "Manual",
                  "Projeto", "Mecanismo", "Tratado", "Curso", "Reforma", "Novo",
                  "Nova", "Direito", "Pós-Graduação", "Temporada", "Especial"}

_PARTICULAS = {"de", "da", "do", "dos", "das", "e", "del", "di", "van", "von"}
_SUFIXOS = {"JR": "Jr.", "JR.": "Jr.", "JUNIOR": "Júnior", "JÚNIOR": "Júnior",
            "FILHO": "Filho", "NETO": "Neto", "SOBRINHO": "Sobrinho"}


def sem_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _capitalizar(palavra):
    if palavra.upper() in _SUFIXOS:
        return _SUFIXOS[palavra.upper()]
    if palavra.lower() in _PARTICULAS:
        return palavra.lower()
    return "-".join(p[:1].upper() + p[1:].lower() for p in palavra.split("-"))


def _legivel(texto):
    return " ".join(_capitalizar(p) for p in texto.split())


def pessoa(sobrenome, prenome=""):
    """Monta {nome, sobrenome, citacao} a partir de 'SOBRENOME' e 'Prenome'."""
    sobrenome = re.sub(r"\s+", " ", sobrenome).strip()
    prenome = re.sub(r"\s+", " ", prenome).strip()
    if prenome.isupper() and len(prenome) > 2 and "." not in prenome:
        prenome = _legivel(prenome)
    nome = f"{prenome} {_legivel(sobrenome)}".strip()
    citacao = f"{sobrenome.upper()}, {prenome}" if prenome else sobrenome.upper()
    return {"nome": nome, "sobrenome": _legivel(sobrenome), "citacao": citacao}


def pessoa_natural(nome):
    """'Ivo Waisberg' -> {nome, sobrenome, citacao}, mantendo a grafia."""
    partes = re.sub(r"\s+", " ", nome).strip().split()
    corte = len(partes) - 1
    if corte > 1 and partes[-1].upper().rstrip(".") in {k.rstrip(".") for k in _SUFIXOS}:
        corte -= 1
    sobrenome = " ".join(partes[corte:])
    prenome = " ".join(partes[:corte])
    citacao = f"{sobrenome.upper()}, {prenome}" if prenome else sobrenome.upper()
    return {"nome": " ".join(partes), "sobrenome": sobrenome, "citacao": citacao}


def chave_pessoa(p):
    """Chave para juntar grafias da mesma pessoa: último sobrenome (sem
    Filho/Neto/Júnior) + primeiro prenome, sem acentos e minúsculas."""
    sob = [s for s in p["sobrenome"].split() if s.upper().rstrip(".") not in
           {k.rstrip(".") for k in _SUFIXOS}] or p["sobrenome"].split()
    prenome = p["nome"][: len(p["nome"]) - len(p["sobrenome"])].split()
    primeiro = prenome[0] if prenome else ""
    return sem_acentos(f"{sob[-1]}|{primeiro}").lower().replace(".", "")


def _palavras(p):
    return [w for w in sem_acentos(p["nome"]).lower().replace(".", "").split()
            if w not in _PARTICULAS]


def mesma_pessoa(a, b):
    """Diz se duas grafias são da mesma pessoa. Exemplos: "Fábio Ulhoa" e
    "Fábio Ulhoa Coelho"; "Pedro Turra" e "P. G. R. Turra"."""
    pa, pb = _palavras(a), _palavras(b)
    if not pa or not pb:
        return False
    if set(pa) <= set(pb) or set(pb) <= set(pa):
        return True
    if pa[0] == pb[0] and set(pa[1:]) & set(pb[1:]):
        return True
    sobrenome_a, sobrenome_b = chave_pessoa(a).split("|")[0], chave_pessoa(b).split("|")[0]
    return sobrenome_a == sobrenome_b and pa[0][0] == pb[0][0] and (len(pa[0]) == 1 or len(pb[0]) == 1)


def limpar_titulo(titulo):
    titulo = unicodedata.normalize("NFC", _INVISIVEIS.sub("", titulo or ""))
    return _SUFIXO_CANAL.sub("", re.sub(r"\s+", " ", titulo)).strip()


def separar_numero(titulo):
    titulo = limpar_titulo(titulo)
    m = _NUMERO.match(titulo)
    if not m:
        return None, titulo
    return int(m.group(1)), titulo[m.end():].strip()


def _autores_citacao(texto, pos):
    """Lê autores no formato SOBRENOME, Prenome a partir de pos."""
    autores = []
    while True:
        m = _AUTOR.match(texto, pos)
        if not m and not autores and pos == 0:
            m = _AUTOR_INICIO.match(texto, pos)
        if not m:
            break
        fim = m.end()
        sep = _SEPARADOR.match(texto, fim) or _PROXIMO_AUTOR.match(texto, fim)
        termina_com_ponto = texto[:fim].rstrip().endswith((".", ")"))
        if not sep and fim < len(texto) and not termina_com_ponto:
            break
        autores.append(pessoa(m.group("sobrenome"), m.group("prenome")))
        if m.groupdict().get("etal"):
            autores[-1]["et_al"] = True
        pos = sep.end() if sep else fim
        while pos < len(texto) and texto[pos] in " .;":
            pos += 1
    return autores, pos


# Episódios sem convidado: encerramentos de temporada e avisos.
_SEM_CONVIDADO = re.compile(r"encerramento|p[óo]s-gradua", re.IGNORECASE)


def convidados_da_descricao(descricao_texto):
    """'Fulana comenta…' ou 'Fulano e Beltrana comentam…' → lista de pessoas."""
    m = _COMENTA_DESCRICAO.match(descricao_texto or "")
    if not m:
        return []
    partes = re.split(r"\s*,\s*|\s+e\s+(?=[A-ZÀ-Ú][a-zà-ÿ]+\s+[A-ZÀ-Ú])", m.group("nome"))
    # Só separa quando cada parte parece um nome completo (duas palavras ou mais).
    if len(partes) > 1 and all(len(x.split()) >= 2 for x in partes):
        return [pessoa_natural(x) for x in partes]
    return [pessoa_natural(m.group("nome"))]


def interpretar(titulo, descricao_texto=""):
    """Devolve dict com numero, convidados, autores (da obra, quando não são
    os convidados), obra, ano_obra e origem do convidado ('titulo',
    'comentador', 'descricao' ou 'apresentadora')."""
    numero, resto = separar_numero(titulo)
    convidados, pos, origem = [], 0, "titulo"

    m = _SO_SOBRENOMES.match(resto)
    if m:
        convidados = [pessoa(m.group("a")), pessoa(m.group("b"))]
        pos = m.end()
    else:
        convidados, pos = _autores_citacao(resto, 0)
        if not convidados:
            m = _NATURAL.match(resto)
            if m:
                nomes = [n for n in (m.group("a"), m.group("b")) if n]
                fim = m.end()
                aceito = (bool(m.group("comenta"))
                          or all(n in (descricao_texto or "") for n in nomes)
                          or not any(w in _NAO_SAO_NOMES for n in nomes for w in n.split()))
                sep = _SEPARADOR.match(resto, fim)
                if aceito and (m.group("comenta") or sep):
                    convidados = [pessoa_natural(n) for n in nomes]
                    pos = fim if m.group("comenta") else sep.end()
                    if not m.group("comenta"):
                        mais, pos = _autores_citacao(resto, pos)
                        convidados += mais

    obra = resto[pos:].strip(" .;:-–") if convidados else resto.strip()
    if not convidados:
        pessoas = convidados_da_descricao(descricao_texto)
        if pessoas:
            convidados, origem = pessoas, "descricao"
        elif _SEM_CONVIDADO.search(resto):
            convidados, origem = [], "sem_convidado"
        else:
            convidados, origem = [pessoa_natural(APRESENTADORA)], "apresentadora"

    # Quem comenta a obra pode não ser o autor: "Fulana comenta sobre ..."
    # na descrição faz dela a convidada, e os nomes do título viram autores.
    autores = []
    if origem == "titulo":
        comentadores = convidados_da_descricao(descricao_texto)
        for comentador in comentadores:
            # Mesma pessoa, mas com o nome por extenso na descrição: usa o mais completo.
            for i, p in enumerate(convidados):
                if mesma_pessoa(comentador, p) and "." in p["nome"] and "." not in comentador["nome"]:
                    convidados[i] = comentador
        novos = [c for c in comentadores if not any(mesma_pessoa(c, p) for p in convidados)]
        if comentadores and len(novos) == len(comentadores):
            autores, convidados, origem = convidados, comentadores, "comentador"


    anos = re.findall(r"\b(1[89]\d{2}|20\d{2})\b", obra)
    if obra and not obra.endswith((".", "?", "!", "”", '"')):
        obra += "."
    return {
        "numero": numero,
        "convidados": convidados,
        "autores": autores,
        "obra": obra,
        "ano_obra": int(anos[-1]) if anos else None,
        "origem_convidado": origem,
    }

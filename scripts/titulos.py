"""Interpretação dos títulos dos episódios.

Formato padrão:
    #N: SOBRENOME, Nome; SOBRENOME2, Nome2. Título da obra. Cidade: Editora, Ano.

Também aceita as variações encontradas no feed ("EP #1:", "#EP99:", "EP116:",
"#EP 245:", "EP#200:", "A #308:", títulos sem número, autores separados por
". " em vez de ";", iniciais, "et al.", "SOBRENOME e SOBRENOME.").

Quando o título não traz nenhum autor no padrão SOBRENOME, Nome, o episódio é
atribuído à apresentadora (ex.: "Aula Ao Vivo - ...").
"""

import re
import unicodedata

APRESENTADORA = {"nome": "Amanda Athayde", "citacao": "ATHAYDE, Amanda"}

# Caracteres invisíveis que às vezes aparecem colados no início do título.
_INVISIVEIS = re.compile(r"[​-‏⁠﻿]")

# Número do episódio no início: "#12:", "EP #1:", "#EP99:", "EP116:", "EP#200:",
# "#EP 245:", "A #308:" etc.
_NUMERO = re.compile(
    r"^\s*(?:A\s+)?(?:#\s*EP|EP\s*#|EP|#)\s*(\d{1,4})\s*[:.\-–]?\s*",
    re.IGNORECASE,
)

_MAIUSC = "A-ZÀ-ÖØ-Þ"
_MINUSC = "a-zß-öø-ÿ"
# Sobrenome em caixa alta: "FORGIONI", "GONÇALVES NETO", "MARTINS-COSTA",
# "CAMILO JR", "SAAD DINIZ".
_SOBRENOME = rf"[{_MAIUSC}][{_MAIUSC}'’\-]+(?:\s+[{_MAIUSC}][{_MAIUSC}'’\-]*)*"
# Um item do prenome: palavra capitalizada, partícula ou inicial com ponto.
_PRENOME_ITEM = (
    rf"(?:[{_MAIUSC}][{_MINUSC}'’\-]+|de|da|do|dos|das|e|del|di|van|von"
    rf"|[{_MAIUSC}]\.(?:\s?[{_MAIUSC}]\.)*)"
)
_AUTOR = re.compile(
    rf"\s*(?P<sobrenome>{_SOBRENOME})\s*,\s*"
    rf"(?P<prenome>{_PRENOME_ITEM}(?:\s+{_PRENOME_ITEM})*)"
    rf"(?P<etal>\s+et\s+al\.?)?"
)
# "BERLE e MEANS." (sem prenomes)
_SO_SOBRENOMES = re.compile(rf"^\s*(?P<a>{_SOBRENOME})\s+e\s+(?P<b>{_SOBRENOME})\s*\.\s*")
# Separadores entre autores e entre autores e obra: ";", ".", ". ." etc.
_SEPARADOR = re.compile(r"\s*(?:[;.]\s*)+")

_PARTICULAS = {"de", "da", "do", "dos", "das", "e", "del", "di", "van", "von"}
_SUFIXOS = {"JR": "Jr.", "JUNIOR": "Júnior", "JÚNIOR": "Júnior", "FILHO": "Filho",
            "NETO": "Neto", "SOBRINHO": "Sobrinho"}


def sem_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _capitalizar(palavra):
    if palavra.upper() in _SUFIXOS:
        return _SUFIXOS[palavra.upper()]
    if palavra.lower() in _PARTICULAS:
        return palavra.lower()
    return "-".join(p[:1].upper() + p[1:].lower() for p in palavra.split("-"))


def _sobrenome_legivel(sobrenome):
    return " ".join(_capitalizar(p) for p in sobrenome.split())


def _autor(sobrenome, prenome=""):
    sobrenome = re.sub(r"\s+", " ", sobrenome).strip()
    prenome = re.sub(r"\s+", " ", prenome).strip()
    nome = f"{prenome} {_sobrenome_legivel(sobrenome)}".strip()
    citacao = f"{sobrenome}, {prenome}" if prenome else sobrenome
    return {"nome": nome, "citacao": citacao}


def chave_pessoa(nome):
    """Chave para juntar grafias da mesma pessoa (acentos e maiúsculas)."""
    return re.sub(r"[^a-z ]", "", sem_acentos(nome).lower()).strip()


def separar_numero(titulo):
    titulo = _INVISIVEIS.sub("", titulo).strip()
    m = _NUMERO.match(titulo)
    if not m:
        return None, titulo
    return int(m.group(1)), titulo[m.end():].strip()


def interpretar(titulo):
    """Devolve dict com numero, convidados, obra, ano e 'interpretado' (bool)."""
    numero, resto = separar_numero(titulo)
    convidados = []
    pos = 0

    m = _SO_SOBRENOMES.match(resto)
    if m:
        convidados = [_autor(m.group("a")), _autor(m.group("b"))]
        pos = m.end()
    else:
        while True:
            m = _AUTOR.match(resto, pos)
            if not m:
                break
            fim = m.end()
            # O prenome precisa terminar num separador (";" ou ".") ou no fim.
            sep = _SEPARADOR.match(resto, fim)
            if not sep and fim < len(resto):
                break
            # "Paula. A evolução": o "A" seguinte não é inicial, é o título.
            convidados.append(_autor(m.group("sobrenome"), m.group("prenome")))
            if m.group("etal"):
                convidados[-1]["et_al"] = True
            pos = sep.end() if sep else fim

    obra = resto[pos:].strip() if convidados else resto
    anos = re.findall(r"\b(1[89]\d{2}|20\d{2})\b", obra)
    interpretado = bool(convidados)
    if not convidados:
        convidados = [dict(APRESENTADORA)]

    return {
        "numero": numero,
        "convidados": convidados,
        "obra": obra.rstrip(" .") + ("." if obra and not obra.endswith((".", "?", "!")) else ""),
        "ano_obra": int(anos[-1]) if anos else None,
        "interpretado": interpretado,
    }

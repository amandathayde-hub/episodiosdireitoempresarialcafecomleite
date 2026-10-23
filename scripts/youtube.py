"""Lista os vídeos da playlist do YouTube e casa cada um com um episódio.

Só usamos a lista de vídeos (id + título), que não exige login. As
transcrições vêm do áudio do feed (ver transcricao.py), não do YouTube.
"""

import difflib
import json
import re
import subprocess
import sys

from titulos import limpar_titulo, sem_acentos, separar_numero


def listar_playlist(url):
    """Devolve [{id, titulo}] ou None se o YouTube não responder."""
    cmd = [sys.executable, "-m", "yt_dlp", "--flat-playlist", "--dump-single-json",
           "--no-warnings", url]
    for tentativa in range(3):
        try:
            saida = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True).stdout
            dados = json.loads(saida)
            return [{"id": e["id"], "titulo": limpar_titulo(e.get("title") or "")}
                    for e in dados.get("entries", []) if e.get("id")]
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: playlist do YouTube indisponível (tentativa {tentativa + 1}): {e}")
    return None


def _normalizar(texto):
    texto = re.sub(r"(\.\.\.|…)\s*$", "", texto)
    # "Aula Ao Vivo - Tema" no feed costuma ser só "Tema" no YouTube.
    texto = re.sub(r"^\s*aula ao vivo\s*[-–:]\s*", "", texto, flags=re.IGNORECASE)
    texto = sem_acentos(texto).lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _semelhanca(titulo_rss, titulo_yt):
    a, b = _normalizar(titulo_rss), _normalizar(titulo_yt)
    if not a or not b:
        return 0.0
    # Títulos do YouTube costumam vir cortados: compara só o começo.
    return difflib.SequenceMatcher(None, a[: len(b)], b).ratio()


def casar(episodios, videos, limiar=0.85):
    """Preenche ep['youtube'] e devolve o relatório do casamento."""
    por_numero = {}
    for v in videos:
        numero, _ = separar_numero(v["titulo"])
        v["numero"] = numero
        if numero is not None:
            por_numero.setdefault(numero, []).append(v)

    usados = set()
    relatorio = {"sem_video": [], "duplicados": [], "por_semelhanca": [], "videos_sobrando": []}
    numeros_rss = {ep["numero"] for ep in episodios if ep["numero"] is not None}

    # 1ª passada: casa pelo número "#N".
    pendentes = []
    for ep in episodios:
        candidatos = por_numero.get(ep["numero"], []) if ep["numero"] is not None else []
        # Confere o título, para não casar números digitados errado.
        candidatos = [v for v in candidatos if _semelhanca(ep["titulo"], v["titulo"]) >= 0.5] or candidatos
        if not candidatos:
            pendentes.append(ep)
            continue
        # A playlist vem do mais novo para o mais antigo; o último é o original.
        escolhido = candidatos[-1]
        if len(candidatos) > 1:
            relatorio["duplicados"].append({"id": ep["id"], "videos": [v["id"] for v in candidatos],
                                            "usado": escolhido["id"]})
        ep["youtube"] = escolhido["id"]
        usados.update(v["id"] for v in candidatos)

    # 2ª passada: para os que sobraram, procura o título mais parecido entre
    # os vídeos ainda livres (sem aceitar vídeo com outro número).
    for ep in pendentes:
        livres = [v for v in videos if v["id"] not in usados
                  and (v["numero"] is None or ep["numero"] is None or v["numero"] == ep["numero"]
                       or v["numero"] not in numeros_rss)]
        melhor = max(livres, key=lambda v: _semelhanca(ep["titulo"], v["titulo"]), default=None)
        nota = _semelhanca(ep["titulo"], melhor["titulo"]) if melhor else 0
        if melhor and nota >= limiar:
            ep["youtube"] = melhor["id"]
            usados.add(melhor["id"])
            item = {"id": ep["id"], "video": melhor["id"], "titulo_video": melhor["titulo"],
                    "semelhanca": round(nota, 2)}
            # Episódio sem número no feed, mas com número no YouTube: adota o número.
            if ep["numero"] is None and melhor["numero"] is not None and melhor["numero"] not in numeros_rss:
                ep["numero"] = melhor["numero"]
                ep["id"] = str(melhor["numero"])
                numeros_rss.add(melhor["numero"])
                item["numero_adotado"] = melhor["numero"]
            relatorio["por_semelhanca"].append(item)
        else:
            ep["youtube"] = None
            relatorio["sem_video"].append({"id": ep["id"], "titulo": ep["titulo"]})

    relatorio["videos_sobrando"] = [{"id": v["id"], "titulo": v["titulo"]}
                                    for v in videos if v["id"] not in usados]
    return relatorio

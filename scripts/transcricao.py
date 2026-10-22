"""Transcrição dos episódios a partir do MP3 do feed, com o Whisper.

Duas fontes, escolhidas em config.yaml (transcricao.fonte):
  local  (padrão) roda o Whisper (faster-whisper, modelo large-v3-turbo) na
         própria máquina do GitHub Actions. Grátis para repositório público.
  groq   envia o áudio ao Groq (chave no segredo GROQ_API_KEY). Mais rápido,
         mas em 2026-10 cortava palavras acentuadas ("voc" em vez de "você").

Para cada episódio pendente: baixa o MP3, transcreve usando o título como
"dica" para acertar nomes próprios, junta o texto em parágrafos com a
marcação de tempo [mm:ss] e grava transcripts/<id>.txt.
"""

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

URL_GROQ = "https://api.groq.com/openai/v1/audio/transcriptions"
PEDACO_SEG = 600

# Frases que o Whisper costuma "inventar" em trechos de música ou silêncio.
_ALUCINACOES = re.compile(
    r"(legendas? (pela|por) .*amara\.org|inscreva-se no canal|obrigad[oa] por assistir"
    r"|legendado por|transcri[çc][ãa]o (feita )?por)",
    re.IGNORECASE,
)


class LimiteAtingido(Exception):
    """O Groq pediu para esperar muito tempo (limite diário ou de saldo)."""


class ChaveInvalida(Exception):
    """A chave do Groq não existe ou foi recusada."""


def _baixar(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": "episodios-cafecomleite/1.0"})
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r, open(destino, "wb") as f:
                while bloco := r.read(1 << 20):
                    f.write(bloco)
            return
        except Exception:  # noqa: BLE001
            if tentativa == 3:
                raise
            time.sleep(5 * 2 ** tentativa)


def cortar_audio(mp3, pasta):
    """Converte para mono 16 kHz MP3 32 kbps e corta em pedaços de 10 min."""
    padrao = str(Path(pasta) / "pedaco_%03d.mp3")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3),
         "-ac", "1", "-ar", "16000", "-b:a", "32k",
         "-f", "segment", "-segment_time", str(PEDACO_SEG), "-reset_timestamps", "1", padrao],
        check=True,
    )
    return sorted(Path(pasta).glob("pedaco_*.mp3"))


def _multipart(campos, arquivo):
    limite = uuid.uuid4().hex
    partes = []
    for nome, valor in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n{valor}\r\n'.encode())
    partes.append(
        f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{arquivo.name}"\r\n'
        f"Content-Type: audio/mpeg\r\n\r\n".encode() + arquivo.read_bytes() + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def transcrever_pedaco(arquivo, chave, modelo, idioma, dica):
    corpo, tipo = _multipart({"model": modelo, "language": idioma, "temperature": "0",
                              "response_format": "verbose_json", "prompt": dica[:400]}, arquivo)
    for tentativa in range(6):
        req = urllib.request.Request(URL_GROQ, data=corpo, method="POST", headers={
            "Authorization": f"Bearer {chave}", "Content-Type": tipo,
            "User-Agent": "episodios-cafecomleite/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", "replace")[:300]
            if e.code in (401, 403):
                raise ChaveInvalida(f"Groq recusou a chave (HTTP {e.code}): {detalhe}") from e
            if e.code == 429:
                espera = float(e.headers.get("retry-after") or 60)
                if espera > 300:
                    raise LimiteAtingido(f"limite do Groq; pede espera de {espera:.0f}s: {detalhe}") from e
                time.sleep(espera + 1)
                continue
            if e.code >= 500 and tentativa < 5:
                time.sleep(10 * (tentativa + 1))
                continue
            raise RuntimeError(f"Groq HTTP {e.code}: {detalhe}") from e
        except urllib.error.URLError:
            if tentativa == 5:
                raise
            time.sleep(10 * (tentativa + 1))
    raise LimiteAtingido("o Groq continuou pedindo para esperar")


def _tempo(seg):
    seg = int(seg)
    h, m, s = seg // 3600, seg % 3600 // 60, seg % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def montar_texto(segmentos, paragrafo_seg=60):
    """Junta os trechos em parágrafos de ~1 minuto, com [mm:ss] no início."""
    paragrafos, atual, inicio, anterior = [], [], None, None
    for inicio_seg, texto in segmentos:
        texto = texto.strip()
        if not texto or _ALUCINACOES.search(texto) or texto == anterior:
            continue
        anterior = texto
        if inicio is None:
            inicio = inicio_seg
        atual.append(texto)
        if inicio_seg - inicio >= paragrafo_seg and texto.endswith((".", "?", "!")):
            paragrafos.append(f"[{_tempo(inicio)}] " + " ".join(atual))
            atual, inicio = [], None
    if atual:
        paragrafos.append(f"[{_tempo(inicio)}] " + " ".join(atual))
    return "\n\n".join(paragrafos) + "\n"


def _dica(ep):
    nomes = ", ".join(p["nome"] for p in ep["convidados"] + ep.get("autores", []))
    return f"Podcast Direito Empresarial Café com Leite, com Amanda Athayde. {nomes}. {ep['obra']}"


def transcrever_episodio_groq(ep, chave, modelo, idioma):
    with tempfile.TemporaryDirectory() as pasta:
        mp3 = Path(pasta) / "episodio.mp3"
        _baixar(ep["mp3"], mp3)
        pedacos = cortar_audio(mp3, pasta)
        segmentos = []
        for i, pedaco in enumerate(pedacos):
            resposta = transcrever_pedaco(pedaco, chave, modelo, idioma, _dica(ep))
            deslocamento = i * PEDACO_SEG
            if resposta.get("segments"):
                segmentos += [(deslocamento + s["start"], s["text"]) for s in resposta["segments"]]
            else:
                segmentos.append((deslocamento, resposta.get("text", "")))
    return montar_texto(segmentos)


def _audio_16k(arquivo):
    """Decodifica com o ffmpeg para o formato que o Whisper usa."""
    import numpy as np
    bruto = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(arquivo), "-f", "f32le",
                            "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(bruto, dtype=np.float32)


def transcrever_episodio_local(ep, modelo_whisper, idioma):
    with tempfile.TemporaryDirectory() as pasta:
        mp3 = Path(pasta) / "episodio.mp3"
        _baixar(ep["mp3"], mp3)
        audio = _audio_16k(mp3)
    segmentos, _ = modelo_whisper.transcribe(
        audio, language=idioma, beam_size=1, vad_filter=True,
        initial_prompt=_dica(ep)[:400], condition_on_previous_text=False)
    return montar_texto([(s.start, s.text) for s in segmentos])


def dividir(episodios, partes):
    """Divide os episódios em 'partes' grupos de duração parecida (sempre do
    mesmo jeito, para cada máquina saber qual é a sua parte)."""
    grupos = [[] for _ in range(partes)]
    cargas = [0] * partes
    for ep in sorted(episodios, key=lambda e: (-(e.get("duracao_seg") or 0), e["id"])):
        i = cargas.index(min(cargas))
        grupos[i].append(ep)
        cargas[i] += ep.get("duracao_seg") or 0
    return grupos


def pendentes(episodios):
    return [e for e in episodios if e["transcricao"] == "pendente" and e.get("mp3") and not e.get("oculto")]


def transcrever_pendentes(episodios, pasta_saida, config, fatia=0, de=1, limite_seg=5 * 3600):
    """Transcreve a parte 'fatia' (de 'de' partes) dos pendentes."""
    fonte = config.get("fonte", "local")
    rel = {"transcritos": [], "falhas": [], "parou_por": None}
    lista = dividir(pendentes(episodios), de)[fatia]
    if fonte not in ("local", "groq"):
        rel["parou_por"] = "fonte de transcrição desligada no config.yaml"
        return rel
    if not lista:
        return rel

    if fonte == "groq":
        chave = os.environ.get("GROQ_API_KEY", "").strip()
        if not chave:
            rel["parou_por"] = "segredo GROQ_API_KEY não encontrado"
            return rel
        lista = lista[: int(config.get("maximo_por_execucao", 60))]
        modelo = config.get("modelo_groq", "whisper-large-v3-turbo")
        transcrever = lambda ep: transcrever_episodio_groq(ep, chave, modelo, config.get("idioma", "pt"))  # noqa: E731
    else:
        from faster_whisper import WhisperModel
        modelo = WhisperModel(config.get("modelo_local", "large-v3-turbo"), device="cpu", compute_type="int8")
        transcrever = lambda ep: transcrever_episodio_local(ep, modelo, config.get("idioma", "pt"))  # noqa: E731

    inicio = time.time()
    for ep in lista:
        if time.time() - inicio > limite_seg:
            rel["parou_por"] = "tempo máximo da execução (continua na próxima)"
            break
        print(f"   transcrevendo {ep['id']}: {ep['titulo'][:70]}", flush=True)
        try:
            texto = transcrever(ep)
        except LimiteAtingido as e:
            rel["parou_por"] = str(e)
            break
        except ChaveInvalida:
            raise
        except Exception as e:  # noqa: BLE001 - um episódio com problema não para os outros
            print(f"   falhou: {e}")
            rel["falhas"].append({"id": ep["id"], "erro": str(e)[:300]})
            continue
        (pasta_saida / f"{ep['id']}.txt").write_text(texto, encoding="utf-8")
        ep["transcricao"] = "ok"
        rel["transcritos"].append(ep["id"])
    return rel

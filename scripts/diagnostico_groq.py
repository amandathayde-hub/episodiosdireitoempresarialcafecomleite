"""Diagnóstico: compara formatos e modelos do Groq num trecho de 10 minutos,
medindo quantas palavras acentuadas vêm cortadas ("voc" em vez de "você").
Uso (no GitHub Actions): python scripts/diagnostico_groq.py <id-do-episodio>
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import transcricao as t  # noqa: E402

BOAS = re.compile(r"\b(você|também|então|não|está|já|só|até)\b", re.I)
CORTADAS = re.compile(r"\b(voc|tamb|ent|n|est|j|s|at)\b(?![\wÀ-ÿ])", re.I)


def taxa(texto):
    b, c = len(BOAS.findall(texto)), len(CORTADAS.findall(texto))
    return f"{c}/{b + c} cortadas ({100 * c / max(1, b + c):.0f}%)"


def chamar(arquivo, chave, modelo, formato, dica):
    corpo, tipo = t._multipart({"model": modelo, "language": "pt", "temperature": "0",
                                "response_format": formato, **({"prompt": dica} if dica else {})}, arquivo)
    import urllib.request
    req = urllib.request.Request(t.URL_GROQ, data=corpo, method="POST", headers={
        "Authorization": f"Bearer {chave}", "Content-Type": tipo, "User-Agent": "diagnostico/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r:
        bruto = r.read()
    return bruto.decode("utf-8") if formato == "text" else json.loads(bruto)


def main():
    ep_id = sys.argv[1]
    chave = os.environ["GROQ_API_KEY"].strip()
    ep = next(e for e in json.loads(Path("data/episodes.json").read_text(encoding="utf-8")) if e["id"] == ep_id)
    dica = f"Podcast Direito Empresarial Café com Leite, com Amanda Athayde. {ep['obra']}"[:400]
    with tempfile.TemporaryDirectory() as pasta:
        mp3 = Path(pasta) / "ep.mp3"
        t._baixar(ep["mp3"], mp3)
        pedaco = t.cortar_audio(mp3, pasta)[1]
        r = {"text": ""} if os.environ.get("PULAR_GROQ") else chamar(pedaco, chave, "whisper-large-v3-turbo", "verbose_json", "")
        texto_groq = r.get("text", "")
        exemplos = [texto_groq[max(0, m.start() - 50):m.end() + 30] for m in CORTADAS.finditer(texto_groq)][:4]
        print(f"::notice title=Groq turbo sem dica::{taxa(texto_groq)} || exemplos: {' ### '.join(exemplos)}")

        import time
        import traceback
        try:
            from faster_whisper import WhisperModel
        except Exception:  # noqa: BLE001
            print(f"::error title=import faster_whisper::{traceback.format_exc()[-900:]}".replace("\n", " | "))
            return
        for nome in ("large-v3-turbo", "small"):
          try:
            inicio = time.time()
            modelo = WhisperModel(nome, device="cpu", compute_type="int8")
            carregado = time.time()
            segs, _ = modelo.transcribe(str(pedaco), language="pt", beam_size=1, vad_filter=True)
            texto = " ".join(s.text for s in segs)
            fim = time.time()
            exemplos = [texto[max(0, m.start() - 50):m.end() + 30] for m in CORTADAS.finditer(texto)][:3]
            print(f"::notice title=faster-whisper {nome}::{taxa(texto)}; carregar {carregado - inicio:.0f}s, "
                  f"transcrever 10 min de áudio em {fim - carregado:.0f}s || {texto[:200]} || exemplos: {' ### '.join(exemplos)}")
          except Exception:  # noqa: BLE001
            print(f"::error title=faster-whisper {nome}::{traceback.format_exc()[-900:]}".replace("\n", " | "))


if __name__ == "__main__":
    main()

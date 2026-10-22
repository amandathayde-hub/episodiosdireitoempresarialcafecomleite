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
        testes = [
            ("whisper-large-v3-turbo", "verbose_json", dica),
            ("whisper-large-v3-turbo", "verbose_json", ""),
            ("whisper-large-v3-turbo", "json", dica),
            ("whisper-large-v3-turbo", "text", dica),
            ("whisper-large-v3", "verbose_json", dica),
            ("whisper-large-v3", "json", dica),
        ]
        for modelo, formato, d in testes:
            try:
                r = chamar(pedaco, chave, modelo, formato, d)
            except Exception as e:  # noqa: BLE001
                print(f"::warning title={modelo} {formato}::erro {str(e)[:300]}")
                continue
            if isinstance(r, str):
                resultado = f"text: {taxa(r)}"
            else:
                resultado = f"campo text: {taxa(r.get('text', ''))}"
                if r.get("segments"):
                    resultado += f" | segmentos: {taxa(' '.join(s['text'] for s in r['segments']))}"
            amostra = (r if isinstance(r, str) else r.get("text", ""))[:200].replace("\n", " ")
            print(f"::notice title={modelo} {formato} {'com dica' if d else 'sem dica'}::{resultado} || {amostra}")


if __name__ == "__main__":
    main()

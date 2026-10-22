"""Transcreve uma parte dos episódios pendentes (usado pelo GitHub Actions,
que divide o trabalho entre várias máquinas ao mesmo tempo).

Uso: python scripts/transcrever_fatia.py --fatia 0 --de 4
Lê data/episodes.json e grava as transcrições novas em novas/ (o passo
seguinte do workflow junta tudo em transcripts/).
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

import transcricao  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fatia", type=int, default=0)
    ap.add_argument("--de", type=int, default=1)
    ap.add_argument("--limite-horas", type=float, default=5.0)
    args = ap.parse_args()

    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8")) or {}
    episodios = json.loads((RAIZ / "data" / "episodes.json").read_text(encoding="utf-8"))
    pasta = RAIZ / "novas"
    pasta.mkdir(exist_ok=True)

    try:
        rel = transcricao.transcrever_pendentes(episodios, pasta, config.get("transcricao", {}),
                                                fatia=args.fatia, de=args.de,
                                                limite_seg=args.limite_horas * 3600)
    except transcricao.ChaveInvalida as e:
        print(f"::error title=Chave do Groq::{str(e)[:500]}")
        sys.exit(1)

    resumo = (f"parte {args.fatia + 1} de {args.de}: {len(rel['transcritos'])} transcritos "
              f"{rel['transcritos']}; falhas: {rel['falhas']}")
    if rel["parou_por"]:
        resumo += f"; parou: {rel['parou_por']}"
    print(f"::notice title=Transcrição::{resumo[:1500]}")


if __name__ == "__main__":
    main()

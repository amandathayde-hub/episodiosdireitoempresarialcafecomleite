# Busca de episódios – Direito Empresarial Café com Leite

Site público e gratuito para encontrar episódios do podcast
**Direito Empresarial Café com Leite**, da Profa. Amanda Athayde, por:

1. palavras do **título**;
2. **nome do convidado** ou do autor da obra (nome completo ou reduzido, com ou sem acento);
3. **assuntos falados na conversa** (busca na transcrição);
4. **descrição** do episódio;

com filtros por **ano** e por **tema**.

O site se atualiza sozinho todos os dias. Ninguém precisa apertar botão.

---

## Como funciona (sem termos técnicos)

```
 Spotify (RSS)  ──┐
                  ├──►  GitHub Actions (todo dia, 6h07 de Brasília)  ──►  GitHub Pages (site público)
 YouTube (lista) ─┘        1. lê os episódios novos
                          2. transcreve o áudio novo com o Whisper
                          3. classifica os temas
                          4. gera as páginas e o índice de busca
                          5. publica
```

* **Fonte dos episódios:** o feed RSS do Spotify for Creators
  (`https://anchor.fm/s/654b6580/podcast/rss`). Tudo o que é publicado no
  Spotify aparece aqui em até 24 horas.
* **YouTube:** usado só para o botão "Assistir no YouTube". O vídeo de cada
  episódio é encontrado pelo número `#N` do título ou, se não houver número,
  pelo título mais parecido.
* **Transcrições:** feitas com o **Whisper** (modelo *large-v3-turbo*), que
  roda nas próprias máquinas do GitHub, a partir do MP3 do feed. Ficam em
  `transcripts/<número>.txt`. Episódios já transcritos não são refeitos.
  Enquanto um episódio não tem transcrição, ele aparece no site com o aviso
  "transcrição pendente", mas não some.
* **Busca:** feita no navegador do ouvinte com o **Pagefind**, que divide o
  índice em pedaços pequenos (bom para celular) e ignora acentos e
  maiúsculas ("recuperacao" encontra "recuperação"). A abertura, o anúncio do
  meio e o encerramento padrão dos episódios ficam fora da busca.
* **Custo:** zero. GitHub Pages e GitHub Actions não cobram por repositório
  público (confira os limites atuais na documentação do GitHub, citada no
  `CHECKLIST.md`).
* **Privacidade:** o site não usa cookies nem rastreamento. O vídeo do
  YouTube só é carregado quando a pessoa clica nele.

## Onde está cada coisa

| Arquivo ou pasta | Para que serve | Você edita? |
|---|---|---|
| `overrides.yaml` | **Correções manuais**: convidado, autor, tema, número, vídeo do YouTube, esconder episódio, grafias de nomes | **Sim** |
| `temas.yaml` | Temas e palavras-chave da classificação automática | **Sim** |
| `config.yaml` | Endereço do feed, da playlist, do site; fonte de transcrição | Raramente |
| `MANUAL.md` | O que fazer quando algo dá errado | Leia |
| `CHECKLIST.md` | Passos para publicar com o domínio próprio | Leia |
| `data/episodes.json` | Todos os episódios (gerado automaticamente) | Não |
| `data/relatorios/` | Listas para revisão: títulos não interpretados, episódios sem vídeo, vídeos duplicados | Leia |
| `transcripts/` | Uma transcrição por episódio (gerado automaticamente) | Não |
| `scripts/` | O programa (Python) | Não |
| `static/` | Visual do site (cores, fonte, logo) | Não |
| `.github/workflows/atualizar.yml` | A rotina diária | Não |

## Regras de interpretação dos títulos

Fórmula padrão para episódios novos:

```
#N: SOBRENOME, Nome; SOBRENOME2, Nome2. Título da obra. Cidade: Editora, Ano.
#N: ATHAYDE, Amanda. Aula ao vivo – Tema da aula.
```

O sistema também entende as variações antigas (`EP #1:`, `#EP99:`, `EP#200:`,
autores separados por ponto, iniciais etc.). Quando a descrição diz
"Fulana comenta…" e Fulana não é autora da obra, ela vira a **convidada** e os
nomes do título viram **autores da obra**. Sem nenhum nome, o episódio fica
com Amanda Athayde. Grafias diferentes da mesma pessoa são unificadas
(mesmo sobrenome e mesmo primeiro nome); exceções vão no `overrides.yaml`.

## Rodar no próprio computador (opcional, para técnicos)

```bash
pip install -r requirements.txt faster-whisper
python scripts/atualizar.py              # dados
python scripts/transcrever_fatia.py      # transcrições pendentes (lento)
python scripts/gerar_site.py             # páginas em site/
npx -y pagefind@1.5.2 --site site        # índice de busca
python -m http.server -d site 8000       # abrir http://localhost:8000
```

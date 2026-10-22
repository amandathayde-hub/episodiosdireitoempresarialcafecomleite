# Manual de sobrevivência

Tudo aqui se faz pelo site do GitHub, sem instalar nada.
Repositório: https://github.com/amandathayde-hub/episodiosdireitoempresarialcafecomleite

**Como editar um arquivo no GitHub:** abra o arquivo → clique no ícone de
lápis (✏️ "Edit this file") → altere → botão verde **Commit changes…** →
**Commit changes**. Qualquer alteração em `overrides.yaml`, `temas.yaml` ou
`config.yaml` faz o site se atualizar sozinho em alguns minutos.

---

### 1. A atualização falhou (recebi e-mail do GitHub)

1. Abra a aba **Actions** do repositório e clique na execução com ❌.
2. Veja qual etapa falhou e leia o quadro **Annotations** (as mensagens em
   português foram escritas para isso).
3. Na maioria das vezes é algo temporário (Spotify, YouTube ou GitHub fora do
   ar). **Não precisa fazer nada:** a execução do dia seguinte refaz tudo.
4. Se falhar vários dias seguidos, encaminhe o e-mail para quem cuida do site
   técnico, ou abra uma conversa com o Claude colando a mensagem do erro.

Nada se perde quando uma execução falha: episódios e transcrições já gravados
continuam no site.

### 2. Corrigir o nome de um convidado

Edite `overrides.yaml`, seção `episodios:` (use o número do episódio entre aspas):

```yaml
  "266":
    convidados: ["Bertrand Wanderer"]
```

Se a mesma pessoa aparece com grafias diferentes, use a seção `pessoas:`:

```yaml
pessoas:
  "Chico Mussnich": "Francisco Antunes Maciel Müssnich"
```

A grafia antiga continua funcionando na busca.

### 3. Corrigir ou acrescentar um tema

* Para **um episódio**: em `overrides.yaml`, escreva `temas:` com a lista
  completa (substitui a classificação automática):

  ```yaml
    "235":
      temas: ["Recuperação judicial e falência", "Acordos sancionadores e leniência"]
  ```

  Use os nomes exatamente como estão em `temas.yaml`.
* Para **todos os episódios**: edite as palavras-chave em `temas.yaml`.

### 4. Outras correções em `overrides.yaml`

```yaml
  "314":
    youtube: "4ekEghNHt1k"     # código do vídeo (o que vem depois de watch?v=)
  "560":
    numero: 60                 # número correto
  "123":
    ocultar: true              # tira o episódio do site
```

### 5. Forçar a atualização agora

Aba **Actions** → **Atualizar episódios** (à esquerda) → botão
**Run workflow** → **Run workflow**. Leva de 5 minutos (sem episódio novo)
até cerca de 1 hora (com episódio novo para transcrever).

### 6. Refazer a transcrição de um episódio

Apague o arquivo `transcripts/<número>.txt` (abra o arquivo → menu "…" →
**Delete file** → **Commit changes**). A próxima execução transcreve de novo.

### 7. Trocar a fonte de transcrição

Em `config.yaml`, na linha `fonte:`:

* `local`: Whisper nas máquinas do GitHub, grátis (**padrão**);
* `groq`: Whisper no Groq, pago e rápido, usa o segredo `GROQ_API_KEY`. Em
  outubro de 2026 o Groq cortava palavras acentuadas ("voc" em vez de
  "você"), por isso não é o padrão;
* `nenhuma`: pausa as transcrições (episódios novos ficam "pendentes").

# Checklist de publicação

Marque cada item quando concluir. Os nomes dos botões do GitHub podem mudar
com o tempo; se algo estiver diferente, a documentação oficial está nos links.

## A. Ligar o site (GitHub Pages)

- [ ] Abrir https://github.com/amandathayde-hub/episodiosdireitoempresarialcafecomleite/settings/pages
- [ ] Em **Build and deployment → Source**, escolher **GitHub Actions**.
- [ ] Esperar a próxima execução da aba **Actions** terminar com ✅.
- [ ] Abrir https://amandathayde-hub.github.io/episodiosdireitoempresarialcafecomleite/ e testar:
      buscar "Forgioni" (deve trazer o EP #1), "business judgment rule" (deve
      trazer o #325) e "recuperacao" sem acento.

## B. Domínio próprio: episodios.direitoempresarialcafecomleite.com

O subdomínio não se compra à parte: ele é criado de graça no painel onde o
domínio `direitoempresarialcafecomleite.com` está registrado (o mesmo que
aponta o `podcast.` para o WordPress).

- [ ] No painel de DNS do domínio, criar um registro:
      **Tipo** `CNAME` · **Nome/Host** `episodios` · **Valor/Destino** `amandathayde-hub.github.io`
- [ ] (Recomendado) Verificar o domínio no GitHub, para ninguém mais usá-lo:
      https://github.com/settings/pages → **Add a domain**.
- [ ] Em https://github.com/amandathayde-hub/episodiosdireitoempresarialcafecomleite/settings/pages,
      campo **Custom domain**: `episodios.direitoempresarialcafecomleite.com` → **Save**.
- [ ] Esperar o GitHub confirmar o DNS (pode levar de minutos a algumas horas)
      e marcar **Enforce HTTPS**.
- [ ] Em `config.yaml`, trocar `url:` por `https://episodios.direitoempresarialcafecomleite.com`
      (assim os links de compartilhamento, o sitemap e o Google usam o endereço novo).

Documentação: https://docs.github.com/pt/pages/configuring-a-custom-domain-for-your-github-pages-site

## C. Link no WordPress

- [ ] No site atual, acrescentar no menu (ou um botão na página inicial) o link
      **"Buscar episódios"** → `https://episodios.direitoempresarialcafecomleite.com`.

## D. Google e redes

- [ ] (Opcional) Google Search Console: adicionar o endereço novo e enviar
      `https://episodios.direitoempresarialcafecomleite.com/sitemap.xml`.
- [ ] Colar o link de um episódio no WhatsApp ou LinkedIn e conferir a prévia
      (título, descrição e capa).

## E. Avisos de falha por e-mail

- [ ] Em https://github.com/settings/notifications, na seção **Actions**,
      deixar ligado o e-mail para **"Only notify for failed workflows"**.
- [ ] Observação: segundo a documentação do GitHub, o aviso de falha de
      rotinas agendadas vai para quem **criou** a rotina ou para quem **alterou
      por último o horário** (`cron`) no arquivo `.github/workflows/atualizar.yml`.
      Como a rotina foi criada pela integração do Claude, se você não receber
      os avisos, edite essa linha (por exemplo, troque `"7 9 * * *"` por
      `"8 9 * * *"`) para que eles passem a ir para você.
      Fonte: https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs

## F. Limpeza (opcional)

- [ ] Apagar os ramos de teste que ficaram do início do projeto:
      https://github.com/amandathayde-hub/episodiosdireitoempresarialcafecomleite/branches
      → ícone de lixeira em `teste-sem-prefixo`, `claude/etapa-1` e `claude/etapa-1-parser`.

## G. Depois da versão 1 aprovada

- [x] **Estatísticas de visitas sem cookies** (GoatCounter): ativado em todas as
      páginas do site de episódios. Painel: https://direitoempresarialcafecomleite.goatcounter.com
      (para desligar, apague o endereço em `goatcounter:` no `config.yaml`).
- [ ] Revisar os temas adicionais propostos a partir das transcrições completas.

## Limites e custos (conferir antes de divulgar)

* GitHub Actions: gratuito para repositórios públicos nas máquinas padrão —
  https://docs.github.com/pt/billing/concepts/product-billing/github-actions
* GitHub Pages: limites de tamanho e tráfego —
  https://docs.github.com/pt/pages/getting-started-with-github-pages/github-pages-limits

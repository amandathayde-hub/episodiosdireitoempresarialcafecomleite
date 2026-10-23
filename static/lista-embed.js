// Trecho para a página inicial do WordPress: "Como navegar" (busca direta,
// o que dá para fazer, temas), botões para as abas Episódios e Convidados e,
// abaixo, a lista de todos os episódios (do mais novo para o mais antigo).
// Uso, num widget "HTML" do Elementor:
//   <div id="cafe-episodios"></div>
//   <script src="https://ENDERECO-DO-SITE-DE-EPISODIOS/static/lista-embed.js" defer></script>
// Tudo vem de static/episodios.json, atualizado todo dia.
(function () {
  var script = document.currentScript;
  var base = script.src.replace(/static\/lista-embed\.js.*$/, "");
  var alvo = document.getElementById("cafe-episodios");
  if (!alvo) return;
  var POR_PAGINA = 20;

  var estilo = document.createElement("style");
  estilo.textContent = [
    ".cafe-lista{font-family:inherit;color:#3a3a3a;max-width:64rem;margin:0 auto;padding:0 16px;box-sizing:border-box}",
    ".cafe-lista *{box-sizing:border-box}",
    ".cafe-lista h2{color:#660D44;font-size:clamp(1.6rem,4vw,2.2rem);text-align:center;margin:0 0 .4rem;line-height:1.2}",
    ".cafe-lista .cafe-sub{text-align:center;color:#535353;font-size:1.05rem;margin:0 auto 1.4rem;max-width:44rem}",
    ".cafe-lista form{display:flex;gap:.5rem;max-width:44rem;margin:0 auto 1.6rem}",
    ".cafe-lista input[type=search]{flex:1;min-width:0;font:inherit;font-size:1.1rem;padding:.85rem 1rem;border:2px solid #5E275B;border-radius:10px;background:#fff;color:#3a3a3a}",
    ".cafe-lista input[type=search]:focus{outline:3px solid #9C4199;outline-offset:1px}",
    ".cafe-lista button,.cafe-lista .cafe-botao{font:inherit;font-weight:700;cursor:pointer;border-radius:999px;text-decoration:none;display:inline-block;text-align:center}",
    ".cafe-lista form button{padding:.85rem 1.3rem;background:#9C4199;color:#fff;border:2px solid #9C4199}",
    ".cafe-lista form button:hover{background:#5E275B;border-color:#5E275B}",
    ".cafe-lista .cafe-cartoes{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.9rem;margin:0 0 1.6rem}",
    ".cafe-lista .cafe-cartao{background:#fff;border:1px solid #E0E0E0;border-radius:14px;padding:1.1rem 1rem;text-decoration:none;color:#3a3a3a;display:block;transition:border-color .15s}",
    ".cafe-lista .cafe-cartao:hover{border-color:#9C4199}",
    ".cafe-lista .cafe-cartao strong{display:block;color:#660D44;font-size:1.08rem;margin:.35rem 0 .3rem}",
    ".cafe-lista .cafe-cartao span{font-size:.95rem;line-height:1.5}",
    ".cafe-lista .cafe-icone{font-size:1.6rem;line-height:1}",
    ".cafe-lista h3{color:#5E275B;font-size:1.05rem;margin:0 0 .6rem;text-align:center}",
    ".cafe-lista .cafe-temas{display:flex;flex-wrap:wrap;gap:.45rem;justify-content:center;margin:0 0 1.8rem}",
    ".cafe-lista .cafe-tema{font-size:.9rem;padding:.4rem .85rem;border-radius:999px;border:1px solid #9C4199;color:#660D44;background:#fff;text-decoration:none}",
    ".cafe-lista .cafe-tema:hover{background:#f6e3f4}",
    ".cafe-lista .cafe-botoes{display:flex;flex-wrap:wrap;gap:.75rem;justify-content:center;margin:0 0 2rem}",
    ".cafe-lista .cafe-botao{padding:.85rem 1.4rem;background:#9C4199;color:#fff;border:2px solid #9C4199}",
    ".cafe-lista .cafe-botao:hover{background:#5E275B;border-color:#5E275B;color:#fff}",
    ".cafe-lista .cafe-botao.sec{background:#fff;color:#660D44}",
    ".cafe-lista .cafe-botao.sec:hover{background:#F3F3F3;color:#660D44}",
    ".cafe-lista .cafe-titulo-lista{text-align:left;font-size:1.5rem;margin:.5rem 0 .2rem}",
    ".cafe-lista .cafe-cont{color:#535353;margin:0 0 .8rem}",
    ".cafe-lista ol{list-style:none;margin:0;padding:0}",
    ".cafe-lista li{border:1px solid #E0E0E0;border-radius:10px;padding:.85rem 1rem;margin:0 0 .7rem;background:#fff}",
    ".cafe-lista .cafe-meta{font-size:.9rem;color:#535353;display:flex;flex-wrap:wrap;gap:.2rem .7rem;align-items:center}",
    ".cafe-lista .cafe-num{background:#660D44;color:#fff;font-weight:700;font-size:.8rem;padding:.05rem .5rem;border-radius:999px}",
    ".cafe-lista .cafe-tit{display:block;margin:.25rem 0;font-weight:700;font-size:1.05rem;color:#660D44;text-decoration:none;overflow-wrap:anywhere}",
    ".cafe-lista .cafe-tit:hover{text-decoration:underline}",
    ".cafe-lista .cafe-quem{margin:0;font-weight:600;color:#5E275B}",
    ".cafe-lista .cafe-mais{display:block;margin:1rem auto;padding:.6rem 1.2rem;border:2px solid #9C4199;background:#fff;color:#660D44}",
    "@media (max-width:600px){.cafe-lista form{flex-direction:column}.cafe-lista form button{width:100%}" +
      ".cafe-lista .cafe-cartoes{grid-template-columns:1fr 1fr;gap:.6rem}.cafe-lista .cafe-cartao{padding:.8rem .7rem}" +
      ".cafe-lista .cafe-cartao strong{font-size:.98rem}.cafe-lista .cafe-cartao span{font-size:.86rem}" +
      ".cafe-lista .cafe-tema{font-size:.85rem;padding:.35rem .7rem}}"
  ].join("");
  document.head.appendChild(estilo);

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function cartao(icone, titulo, texto, link) {
    return '<a class="cafe-cartao" href="' + link + '"><span class="cafe-icone" aria-hidden="true">' + icone +
      "</span><strong>" + titulo + "</strong><span>" + texto + "</span></a>";
  }

  alvo.className = "cafe-lista";
  alvo.innerHTML =
    "<h2>Como navegar pelos episódios</h2>" +
    '<p class="cafe-sub">Busque em todos os episódios: no título, no nome do convidado e em <strong>tudo o que foi falado</strong> nas conversas.</p>' +
    '<form role="search" action="' + base + '" method="get">' +
    '<label for="cafe-q" style="position:absolute;left:-9999px">Buscar episódios</label>' +
    '<input id="cafe-q" name="q" type="search" placeholder="Ex.: recuperação judicial, Forgioni, business judgment rule" autocomplete="off">' +
    '<button type="submit">Buscar</button></form>' +
    '<div class="cafe-cartoes">' +
    cartao("🔎", "Busque no que foi falado", 'Cada episódio foi transcrito: a busca encontra o termo e mostra o trecho da conversa.', base) +
    cartao("🏷️", "Filtre por tema", "Societário, S.A., limitadas, recuperação judicial, concorrência, contratos e mais.", base) +
    cartao("👥", "Encontre por convidado", "Todos os convidados em ordem alfabética, com os episódios de cada um.", base + "convidados/") +
    cartao("🎧", "Ouça ou assista aqui", "Em cada episódio: YouTube ou áudio na própria página, além do Spotify.", base) +
    "</div>" +
    '<h3>Explore por tema</h3><div class="cafe-temas"></div>' +
    '<div class="cafe-botoes">' +
    '<a class="cafe-botao" href="' + base + '">Pesquisar episódios</a>' +
    '<a class="cafe-botao sec" href="' + base + 'convidados/">Ver todos os convidados</a>' +
    "</div>" +
    '<h2 class="cafe-titulo-lista">Todos os episódios</h2><p class="cafe-cont"></p><ol></ol>' +
    '<button type="button" class="cafe-mais" hidden>Mostrar mais episódios</button>';

  var lista = alvo.querySelector("ol");
  var botao = alvo.querySelector(".cafe-mais");
  var dados = [];
  var mostrados = 0;

  function mais() {
    lista.insertAdjacentHTML("beforeend", dados.slice(mostrados, mostrados + POR_PAGINA).map(function (ep) {
      return "<li><div class=\"cafe-meta\"><span class=\"cafe-num\">" + esc(ep.r) + "</span><span>" + esc(ep.dx) +
        "</span>" + (ep.du ? "<span>" + esc(ep.du) + "</span>" : "") + "</div>" +
        '<a class="cafe-tit" href="' + base + "episodio/" + encodeURIComponent(ep.id) + '/">' + esc(ep.t) + "</a>" +
        (ep.c ? '<p class="cafe-quem">' + esc(ep.c) + "</p>" : "") + "</li>";
    }).join(""));
    mostrados = Math.min(dados.length, mostrados + POR_PAGINA);
    botao.hidden = mostrados >= dados.length;
  }

  function mostrarTemas(eps) {
    var contagem = {};
    eps.forEach(function (ep) { ep.te.forEach(function (t) { contagem[t] = (contagem[t] || 0) + 1; }); });
    var temas = Object.keys(contagem).sort(function (a, b) { return contagem[b] - contagem[a]; });
    alvo.querySelector(".cafe-temas").innerHTML = temas.map(function (t) {
      return '<a class="cafe-tema" href="' + base + "?tema=" + encodeURIComponent(t) + '">' + esc(t) + "</a>";
    }).join("");
  }

  botao.addEventListener("click", mais);
  fetch(base + "static/episodios.json").then(function (r) { return r.json(); }).then(function (eps) {
    dados = eps;
    alvo.querySelector("h2").textContent = "Como navegar pelos " + eps.length + " episódios";
    alvo.querySelector(".cafe-cont").textContent = eps.length + " episódios, do mais novo para o mais antigo.";
    mostrarTemas(eps);
    mais();
  }).catch(function () {
    alvo.querySelector(".cafe-cont").innerHTML = 'Não foi possível carregar a lista agora. <a href="' + base + '">Abrir a busca de episódios</a>.';
  });
})();

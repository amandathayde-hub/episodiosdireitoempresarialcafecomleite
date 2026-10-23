// Trecho para a página inicial do WordPress: botões para as abas Episódios e
// Convidados e, abaixo, a lista de todos os episódios (do mais novo para o
// mais antigo). Uso, num widget "HTML" do Elementor:
//   <div id="cafe-episodios"></div>
//   <script src="https://ENDERECO-DO-SITE-DE-EPISODIOS/static/lista-embed.js" defer></script>
// A lista vem de static/episodios.json, atualizado todo dia.
(function () {
  var script = document.currentScript;
  var base = script.src.replace(/static\/lista-embed\.js.*$/, "");
  var alvo = document.getElementById("cafe-episodios");
  if (!alvo) return;
  var POR_PAGINA = 20;

  var estilo = document.createElement("style");
  estilo.textContent = [
    ".cafe-lista{font-family:inherit;color:#3a3a3a;max-width:60rem;margin:0 auto}",
    ".cafe-lista .cafe-botoes{display:flex;flex-wrap:wrap;gap:.75rem;justify-content:center;margin:0 0 1.5rem}",
    ".cafe-lista .cafe-botao{display:inline-block;padding:.85rem 1.4rem;border-radius:999px;background:#9C4199;color:#fff;font-weight:700;text-decoration:none;border:2px solid #9C4199}",
    ".cafe-lista .cafe-botao:hover{background:#5E275B;border-color:#5E275B;color:#fff}",
    ".cafe-lista .cafe-botao.sec{background:#fff;color:#660D44}",
    ".cafe-lista .cafe-botao.sec:hover{background:#F3F3F3}",
    ".cafe-lista h2{color:#660D44;font-size:1.4rem;margin:1rem 0 .3rem}",
    ".cafe-lista .cafe-cont{color:#535353;margin:0 0 .8rem}",
    ".cafe-lista ol{list-style:none;margin:0;padding:0}",
    ".cafe-lista li{border:1px solid #E0E0E0;border-radius:10px;padding:.85rem 1rem;margin:0 0 .7rem;background:#fff}",
    ".cafe-lista .cafe-meta{font-size:.9rem;color:#535353;display:flex;flex-wrap:wrap;gap:.2rem .7rem;align-items:center}",
    ".cafe-lista .cafe-num{background:#660D44;color:#fff;font-weight:700;font-size:.8rem;padding:.05rem .5rem;border-radius:999px}",
    ".cafe-lista .cafe-tit{display:block;margin:.25rem 0;font-weight:700;font-size:1.05rem;color:#660D44;text-decoration:none;overflow-wrap:anywhere}",
    ".cafe-lista .cafe-tit:hover{text-decoration:underline}",
    ".cafe-lista .cafe-quem{margin:0;font-weight:600;color:#5E275B}",
    ".cafe-lista .cafe-mais{display:block;margin:1rem auto;padding:.6rem 1.2rem;border-radius:999px;border:2px solid #9C4199;background:#fff;color:#660D44;font:inherit;font-weight:700;cursor:pointer}"
  ].join("");
  document.head.appendChild(estilo);

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  alvo.className = "cafe-lista";
  alvo.innerHTML =
    '<div class="cafe-botoes">' +
    '<a class="cafe-botao" href="' + base + '">Pesquisar episódios por palavra ou tema</a>' +
    '<a class="cafe-botao sec" href="' + base + 'convidados/">Ver todos os convidados</a>' +
    "</div>" +
    "<h2>Todos os episódios</h2><p class=\"cafe-cont\"></p><ol></ol>" +
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

  botao.addEventListener("click", mais);
  fetch(base + "static/episodios.json").then(function (r) { return r.json(); }).then(function (eps) {
    dados = eps;
    alvo.querySelector(".cafe-cont").textContent = eps.length + " episódios, do mais novo para o mais antigo.";
    mais();
  }).catch(function () {
    alvo.querySelector(".cafe-cont").innerHTML = 'Não foi possível carregar a lista agora. <a href="' + base + '">Abrir a busca de episódios</a>.';
  });
})();

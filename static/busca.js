// Página inicial: busca com o Pagefind (índice em pedaços, tolerante a
// acentos) e filtros por ano e tema. Sem texto digitado, lista os episódios
// do mais novo para o mais antigo usando static/episodios.json.
(function () {
  var POR_PAGINA = 20;
  var campo = document.getElementById("q");
  var selAno = document.getElementById("ano");
  var selTema = document.getElementById("tema");
  var lista = document.getElementById("resultados");
  var contagem = document.getElementById("contagem");
  var botaoMais = document.getElementById("mais");
  var episodios = [];
  var porId = {};
  var pagefind = null;
  var atual = { itens: [], mostrados: 0 };
  var rodada = 0;
  var espera = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function carregarPagefind() {
    if (!pagefind) {
      // Caminho relativo a este arquivo (static/busca.js).
      pagefind = import("../pagefind/pagefind.js").then(function (pf) {
        pf.options({ excerptLength: 30 });
        return pf;
      });
    }
    return pagefind;
  }

  function cartao(ep, trecho) {
    var botoes = "";
    if (ep.sp) botoes += '<a class="botao spotify" href="' + esc(ep.sp) + '">Ouvir no Spotify</a>';
    if (ep.yt) botoes += '<a class="botao youtube" href="' + esc(ep.yt) + '">Assistir no YouTube</a>';
    var temas = ep.te.map(function (t) {
      return '<li><a class="etiqueta" href="?tema=' + encodeURIComponent(t) + '">' + esc(t) + "</a></li>";
    }).join("");
    return '<li class="resultado">' +
      '<div class="meta"><span class="numero">' + esc(ep.r) + "</span>" +
      '<time datetime="' + esc(ep.d) + '">' + esc(ep.dx) + "</time>" +
      (ep.du ? "<span>" + esc(ep.du) + "</span>" : "") +
      (ep.tr ? "" : '<span class="selo-pendente">transcrição pendente</span>') + "</div>" +
      '<h3><a href="episodio/' + encodeURIComponent(ep.id) + '/">' + esc(ep.t) + "</a></h3>" +
      '<p class="quem">' + esc(ep.c) + "</p>" +
      (trecho ? '<p class="trecho">… ' + trecho + " …</p>" : "") +
      (temas ? '<ul class="temas" aria-label="Temas">' + temas + "</ul>" : "") +
      '<div class="botoes">' + botoes + "</div></li>";
  }

  // O trecho mostrado vem da conversa (transcrição) ou da descrição; se o
  // termo só aparece no título ou no nome, o cartão já mostra isso.
  function melhorTrecho(dados) {
    var secoes = (dados.sub_results || []).filter(function (s) {
      return /#(transcricao|descricao)$/.test(s.url);
    });
    var prefere = secoes.filter(function (s) { return /#transcricao$/.test(s.url); })[0] || secoes[0];
    return prefere ? prefere.excerpt : "";
  }

  function filtrosAtivos() {
    var f = {};
    if (selAno.value) f.ano = selAno.value;
    if (selTema.value) f.tema = selTema.value;
    return f;
  }

  function guardarNaUrl() {
    var p = new URLSearchParams();
    if (campo.value.trim()) p.set("q", campo.value.trim());
    if (selAno.value) p.set("ano", selAno.value);
    if (selTema.value) p.set("tema", selTema.value);
    var nova = location.pathname + (p.toString() ? "?" + p.toString() : "");
    history.replaceState(null, "", nova);
  }

  function texto(n, um, varios) { return n + " " + (n === 1 ? um : varios); }

  async function mostrarMais() {
    var minha = rodada;
    var fatia = atual.itens.slice(atual.mostrados, atual.mostrados + POR_PAGINA);
    var html = await Promise.all(fatia.map(async function (item) {
      if (item.resultado) {
        var dados = await item.resultado.data();
        var ep = porId[dados.meta.id];
        return ep ? cartao(ep, melhorTrecho(dados)) : "";
      }
      return cartao(item.ep, "");
    }));
    if (minha !== rodada) return;
    lista.insertAdjacentHTML("beforeend", html.join(""));
    atual.mostrados += fatia.length;
    botaoMais.hidden = atual.mostrados >= atual.itens.length;
  }

  async function buscar() {
    var minha = ++rodada;
    guardarNaUrl();
    var termo = campo.value.trim();
    var filtros = filtrosAtivos();
    lista.innerHTML = "";
    atual = { itens: [], mostrados: 0 };

    if (!termo) {
      atual.itens = episodios.filter(function (ep) {
        return (!filtros.ano || ep.d.slice(0, 4) === filtros.ano) &&
               (!filtros.tema || ep.te.indexOf(filtros.tema) !== -1);
      }).map(function (ep) { return { ep: ep }; });
      contagem.textContent = Object.keys(filtros).length
        ? texto(atual.itens.length, "episódio encontrado", "episódios encontrados")
        : texto(atual.itens.length, "episódio", "episódios") + ", do mais novo para o mais antigo";
    } else {
      contagem.textContent = "Buscando…";
      botaoMais.hidden = true;
      var busca;
      try {
        var pf = await carregarPagefind();
        busca = await pf.search(termo, { filters: filtros });
      } catch (erro) {
        pagefind = null;
        contagem.textContent = "Não foi possível buscar agora. Verifique a conexão e tente de novo.";
        return;
      }
      if (minha !== rodada) return;
      atual.itens = busca.results.map(function (r) { return { resultado: r }; });
      contagem.textContent = atual.itens.length
        ? texto(atual.itens.length, "episódio encontrado", "episódios encontrados") + " para “" + termo + "”"
        : "Nenhum episódio encontrado para “" + termo + "”. Tente outra palavra ou tire os filtros.";
    }
    await mostrarMais();
  }

  function agendar() {
    clearTimeout(espera);
    espera = setTimeout(buscar, 250);
  }

  campo.addEventListener("input", function () {
    if (campo.value.length > 1) carregarPagefind().then(function (pf) { pf.preload(campo.value); });
    agendar();
  });
  selAno.addEventListener("change", buscar);
  selTema.addEventListener("change", buscar);
  botaoMais.addEventListener("click", mostrarMais);
  document.getElementById("limpar").addEventListener("click", function () {
    selAno.value = ""; selTema.value = ""; buscar();
  });

  fetch("static/episodios.json").then(function (r) { return r.json(); }).then(function (dados) {
    episodios = dados;
    dados.forEach(function (ep) { porId[ep.id] = ep; });
    var p = new URLSearchParams(location.search);
    campo.value = p.get("q") || "";
    selAno.value = p.get("ano") || "";
    selTema.value = p.get("tema") || "";
    buscar();
  });
})();

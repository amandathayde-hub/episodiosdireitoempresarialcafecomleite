// Página do episódio: escolha do player (YouTube, Spotify ou só o áudio),
// horário clicável na transcrição. O YouTube e o Spotify só são chamados
// depois do clique da pessoa.
(function () {
  var abas = Array.prototype.slice.call(document.querySelectorAll(".abas-player [role=tab]"));
  var audio = document.querySelector(".player");
  var video = document.getElementById("painel-youtube");
  var spotify = document.getElementById("painel-spotify");

  function mostrar(aba) {
    abas.forEach(function (a) {
      var ativo = a === aba;
      a.setAttribute("aria-selected", ativo ? "true" : "false");
      document.getElementById(a.getAttribute("aria-controls")).hidden = !ativo;
    });
    if (aba.id !== "aba-audio" && audio) audio.pause();
  }

  abas.forEach(function (aba, i) {
    aba.addEventListener("click", function () { mostrar(aba); });
    aba.addEventListener("keydown", function (ev) {
      var passo = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
      if (!passo) return;
      var proxima = abas[(i + passo + abas.length) % abas.length];
      proxima.focus();
      mostrar(proxima);
    });
  });

  function carregarVideo(inicio) {
    var iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube-nocookie.com/embed/" + video.dataset.youtube +
      "?autoplay=1" + (inicio ? "&start=" + inicio : "");
    iframe.title = "Vídeo do episódio no YouTube";
    iframe.allow = "autoplay; encrypted-media; picture-in-picture";
    iframe.allowFullscreen = true;
    video.replaceChildren(iframe);
  }

  if (video) {
    video.querySelector(".video-capa").addEventListener("click", function () { carregarVideo(0); });
  }

  if (spotify) {
    spotify.querySelector(".carregar-spotify").addEventListener("click", function () {
      var iframe = document.createElement("iframe");
      iframe.src = "https://open.spotify.com/embed/episode/" + spotify.dataset.spotify;
      iframe.title = "Episódio no Spotify";
      iframe.height = 232;
      iframe.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
      iframe.loading = "lazy";
      spotify.replaceChildren(iframe);
    });
  }

  // Horário da transcrição: toca a partir dali no player que estiver aberto
  // (YouTube, se estiver selecionado; senão, o áudio).
  document.addEventListener("click", function (ev) {
    var botao = ev.target.closest(".tempo");
    if (!botao) return;
    var segundos = botao.dataset.tempo.split(":").map(Number)
      .reduce(function (total, p) { return total * 60 + p; }, 0);
    var abaYoutube = document.getElementById("aba-youtube");
    var alvo;
    if (video && abaYoutube && abaYoutube.getAttribute("aria-selected") === "true") {
      carregarVideo(segundos);
      alvo = video;
    } else if (audio) {
      var abaAudio = document.getElementById("aba-audio");
      if (abaAudio) mostrar(abaAudio);
      audio.currentTime = segundos;
      audio.play();
      alvo = audio;
    }
    if (alvo) alvo.scrollIntoView({ behavior: "smooth", block: "center" });
  });
})();

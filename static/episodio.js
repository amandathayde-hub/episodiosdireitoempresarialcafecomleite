// Página do episódio: horário clicável na transcrição e vídeo carregado só
// quando a pessoa pede (o YouTube não é chamado antes do clique).
(function () {
  var audio = document.querySelector(".player");

  document.addEventListener("click", function (ev) {
    var botao = ev.target.closest(".tempo");
    if (!botao || !audio) return;
    var partes = botao.dataset.tempo.split(":").map(Number);
    var segundos = partes.reduce(function (total, p) { return total * 60 + p; }, 0);
    audio.currentTime = segundos;
    audio.play();
    audio.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  var video = document.querySelector(".video");
  if (video) {
    video.querySelector(".video-capa").addEventListener("click", function () {
      var iframe = document.createElement("iframe");
      iframe.src = "https://www.youtube-nocookie.com/embed/" + video.dataset.youtube + "?autoplay=1";
      iframe.title = "Vídeo do episódio no YouTube";
      iframe.allow = "autoplay; encrypted-media; picture-in-picture";
      iframe.allowFullscreen = true;
      video.replaceChildren(iframe);
      if (audio) audio.pause();
    });
  }
})();

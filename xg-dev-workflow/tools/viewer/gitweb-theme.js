/* status viewer — runs inside the gitweb pages served under /gitweb/ (same origin as the viewer): applies the
   theme and brightness the main page stored, before the body paints. */
(function () {
  function get(k) { try { return JSON.parse(localStorage.getItem("svd2-" + k)); } catch (e) { return null; } }
  var theme = get("theme"), lum = +get("lum") || 100;
  if (theme) document.documentElement.setAttribute("data-theme", theme);
  if (lum !== 100) document.documentElement.style.filter = "brightness(" + lum / 100 + ")";
})();

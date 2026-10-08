/* status viewer — runs inside the gitweb pages served under /gitweb/ (same origin as the viewer): applies the
   theme and brightness the main page stored, before the body paints. */
(function () {
  function get(k) { try { return JSON.parse(localStorage.getItem("svd2-" + k)); } catch (e) { return null; } }
  var root = document.documentElement, theme = get("theme");
  if (theme) root.setAttribute("data-theme", theme);
  var cs = getComputedStyle(root);
  function scale(list, k) {   // the main page's surface and interface-text brightness, as lightness on the same tokens
    if (!k || k === 100) return;
    list.forEach(function (p) { root.style.setProperty(p, "oklch(from " + cs.getPropertyValue(p).trim() + " calc(l * " + k / 100 + ") c h)"); });
  }
  scale(["--chrome", "--paper", "--card", "--card2", "--ln", "--ln2"], +get("blum"));
  scale(["--ink", "--tx", "--mu", "--faint"], +get("lum"));
})();

/* V1 visitor data layer: reads the page-embedded payload and exposes image URLs.
   Image sizes are computed once at build time (site/scripts/build.py) and shipped
   per item, so the browser never invents its own sizes. */
(function (global) {
  function readAppData(id) {
    var node = document.getElementById(id || "app-data");
    if (!node) throw new Error("app data block is missing");
    try {
      return JSON.parse(node.textContent);
    } catch (err) {
      throw new Error("app data block is not valid JSON: " + err.message);
    }
  }

  function src(item, kind) {
    var images = (item && item.img) || {};
    var url = images[kind] || images.full || "";
    if (!url) throw new Error("missing image url for " + (item && item.id));
    return url;
  }

  function normalize(text) {
    var value = String(text == null ? "" : text);
    if (value.normalize) value = value.normalize("NFKC");
    return value.trim().toLowerCase();
  }

  global.T9_readAppData = readAppData;
  global.T9_src = src;
  global.T9_normalize = normalize;
})(window);

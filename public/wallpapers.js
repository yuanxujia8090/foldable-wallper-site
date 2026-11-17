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

  function pathExtension(value) {
    var path = String(value || "").split(/[?#]/)[0];
    var cut = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
    var base = cut >= 0 ? path.slice(cut + 1) : path;
    var dot = base.lastIndexOf(".");
    if (dot <= 0) return "";
    var ext = base.slice(dot + 1).toLowerCase();
    return /^[a-z0-9]+$/.test(ext) ? ext : "";
  }

  function declaredMatch(name, ext) {
    if (typeof name !== "string" || /[\u0000-\u001f\u007f]/.test(name)) return "";
    var trimmed = name.trim();
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*\.(webp|png|jpg|jpeg)$/i.test(trimmed)) return "";
    if (pathExtension(trimmed) !== ext) return "";
    return trimmed;
  }

  function safeStem(id) {
    var stem = String(id == null ? "" : id).replace(/[^A-Za-z0-9._-]+/g, "");
    if (!stem || stem === "." || stem === "..") return "wallpaper";
    return stem;
  }

  function downloadName(item, url) {
    var ext = pathExtension(url);
    var known = ext === "webp" || ext === "png" || ext === "jpg" || ext === "jpeg";
    var declared = known ? declaredMatch(item && item.download_filename, ext) : "";
    if (declared) return declared;
    return safeStem(item && item.id) + "." + (known ? ext : "jpg");
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
  global.T9_downloadName = downloadName;
  global.T9_normalize = normalize;
})(window);

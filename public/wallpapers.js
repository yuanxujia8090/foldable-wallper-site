/* V1 visitor data layer — manifest + devices; R2 full URL or picsum /w/h */
(function (global) {
  var IMAGE_EXT = /\.(jpe?g|png|webp)(\?|#|$)/i;

  function isFullImageUrl(url) {
    if (!url || typeof url !== "string") return false;
    if (!/^https?:\/\//i.test(url)) return false;
    if (/r2\.dev/i.test(url)) return true;
    if (IMAGE_EXT.test(url)) return true;
    return false;
  }

  function smallSource(item, kind) {
    var img = item && item.img;
    if (!img || typeof img !== "object") return "";
    var url = kind === "strip" ? (img.strip || img.thumb) : (img.thumb || img.strip);
    if (typeof url !== "string") return "";
    return url.trim();
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
    if (kind === "thumb" || kind === "strip") {
      var small = smallSource(item, kind);
      if (small) return small;
    }
    var full =
      item.cdn_url_full ||
      item.cdn_url_preview ||
      (isFullImageUrl(item.cdn_url) ? item.cdn_url : null);
    if (full) return full;
    // relative local path (draft / offline sample frames)
    if (item.cdn_url && /^(?:\.\.?\/)?(?:assets\/|data\/)/i.test(item.cdn_url)) return item.cdn_url;
    if (/^data:|^blob:/.test(item.cdn_url || "")) return item.cdn_url;

    var w = item.w || 1600;
    var h = item.h || 900;
    if (kind === "thumb") {
      if (item.ratio === "phone-portrait") { w = 360; h = 640; }
      else if (item.ratio === "foldable") { w = 420; h = 350; }
      else { w = 480; h = 270; }
    } else if (kind === "strip") {
      if (item.ratio === "phone-portrait") { w = 220; h = 390; }
      else if (item.ratio === "foldable") { w = 320; h = 266; }
      else { w = 480; h = 270; }
    } else if (kind === "full") {
      w = item.w || (item.ratio === "phone-portrait" ? 900 : item.ratio === "foldable" ? 1200 : 1600);
      h = item.h || (item.ratio === "phone-portrait" ? 1600 : item.ratio === "foldable" ? 1000 : 900);
    } else if (kind === "hero-half") {
      w = 1200;
      h = item.ratio === "phone-portrait" ? 1600 : 900;
    }
    var base = item.cdn_url || "";
    return base + "/" + w + "/" + h;
  }

  function publishedOnly(items) {
    return (items || []).filter(function (it) {
      return !it.status || it.status === "published";
    });
  }

  function loadJson(url) {
    return fetch(url, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("Failed to load " + url + " (" + res.status + ")");
      return res.json();
    });
  }

  function loadManifest(url) {
    url = url || "data/wallpapers.json";
    return loadJson(url).then(function (doc) {
      var items = Array.isArray(doc) ? doc : (doc.items || []);
      return publishedOnly(items);
    });
  }

  function loadDevices(url) {
    url = url || "config/devices.json";
    return loadJson(url).then(function (doc) {
      return doc.hot_devices || doc.devices || [];
    });
  }

  global.T9_src = src;
  global.T9_downloadName = downloadName;
  global.T9_loadManifest = loadManifest;
  global.T9_loadDevices = loadDevices;
  global.T9_publishedOnly = publishedOnly;
})(window);

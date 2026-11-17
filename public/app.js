/* Shared visitor logic for both language pages.
   The page ships its own strings, wallpaper data and image URLs in #app-data, so
   nothing here fetches translations or replaces the generated language. */
(function () {
  "use strict";

  var MAX_QUERY = 200;
  var CARD_HEIGHT = 120;

  var app;
  try {
    app = window.T9_readAppData();
  } catch (err) {
    reportEmptyPage(err);
    return;
  }

  var t = app.strings || {};
  var items = app.items || [];
  var byId = {};
  items.forEach(function (item) {
    if (item && item.id) byId[item.id] = item;
  });

  var allowed = {
    devices: (app.devices || []).map(function (device) { return device.id; }),
    styles: app.styles || [],
    ratios: app.ratios || []
  };
  var deviceLabels = {};
  (app.devices || []).forEach(function (device) {
    deviceLabels[device.id] = device.label;
  });

  var state = { q: "", query: "", device: null, styles: [], ratios: [], wallpaper: null };

  var els = {
    q: document.getElementById("q"),
    sheet: document.getElementById("sheet"),
    grid: document.getElementById("sheetGrid"),
    empty: document.getElementById("emptyMsg"),
    count: document.getElementById("countLine"),
    strip: document.getElementById("heroStrip"),
    caption: document.getElementById("stripCaption"),
    lightbox: document.getElementById("lightbox"),
    lbImg: document.getElementById("lbImg"),
    lbTitle: document.getElementById("lbTitle"),
    lbAttrs: document.getElementById("lbAttrs"),
    lbDownload: document.getElementById("lbDownload"),
    lbSave: document.getElementById("lbSave"),
    lbClose: document.getElementById("lbClose")
  };

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var numberFormat = makeNumberFormat(app.lang);
  var lastTrigger = null;

  function makeNumberFormat(locale) {
    try {
      return new Intl.NumberFormat(locale);
    } catch (err) {
      return { format: function (value) { return String(value); } };
    }
  }

  function fill(template, values) {
    var out = template == null ? "" : String(template);
    Object.keys(values).forEach(function (key) {
      out = out.split("{" + key + "}").join(String(values[key]));
    });
    return out;
  }

  function countText(visible, total) {
    return fill(t["find.count"], {
      visible: numberFormat.format(visible),
      total: numberFormat.format(total)
    });
  }

  function closest(node, selector) {
    if (!node || !node.closest) return null;
    return node.closest(selector);
  }

  /* —— filtering —— */
  function matches(item) {
    if (state.device && item.device_tags.indexOf(state.device) === -1) return false;
    if (state.styles.length && state.styles.indexOf(item.style) === -1) return false;
    if (state.ratios.length && state.ratios.indexOf(item.ratio) === -1) return false;
    if (state.query && String(item.search || "").indexOf(state.query) === -1) return false;
    return true;
  }

  function buildFrame(item) {
    var figure = document.createElement("figure");
    figure.className = "frame";
    figure.tabIndex = 0;
    figure.setAttribute("role", "button");
    figure.setAttribute("data-id", item.id);
    figure.setAttribute("aria-label", fill(t["sheet.open"], { title: item.title }));
    var img = document.createElement("img");
    img.src = window.T9_src(item, "thumb");
    img.alt = item.alt || item.title || "";
    img.width = item.thumbW || 213;
    img.height = CARD_HEIGHT;
    img.loading = "lazy";
    figure.appendChild(img);
    return figure;
  }

  function renderSheet() {
    var list = items.filter(matches);
    if (els.grid) {
      els.grid.textContent = "";
      list.forEach(function (item) { els.grid.appendChild(buildFrame(item)); });
    }
    if (els.empty) els.empty.hidden = list.length > 0;
    if (els.count) els.count.textContent = countText(list.length, items.length);
  }

  function syncChips() {
    document.querySelectorAll("[data-device]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.getAttribute("data-device") === state.device));
    });
    document.querySelectorAll("[data-style]").forEach(function (button) {
      button.setAttribute("aria-pressed",
        String(state.styles.indexOf(button.getAttribute("data-style")) !== -1));
    });
    document.querySelectorAll("[data-ratio]").forEach(function (button) {
      button.setAttribute("aria-pressed",
        String(state.ratios.indexOf(button.getAttribute("data-ratio")) !== -1));
    });
  }

  /* —— address state —— */
  function collectValues(params, name, allowedValues) {
    var out = [];
    params.getAll(name).forEach(function (raw) {
      String(raw).split(",").forEach(function (value) {
        var trimmed = value.trim();
        if (!trimmed) return;
        if (allowedValues && allowedValues.indexOf(trimmed) === -1) return;
        if (out.indexOf(trimmed) === -1) out.push(trimmed);
      });
    });
    if (allowedValues) out.sort(orderBy(allowedValues));
    return out;
  }

  function orderBy(list) {
    return function (a, b) { return list.indexOf(a) - list.indexOf(b); };
  }

  function readLocation() {
    var params = null;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (err) {
      params = null;
    }
    var next = { q: "", query: "", device: null, styles: [], ratios: [], wallpaper: null };
    if (!params) return next;
    next.q = String(params.getAll("q")[0] || "").slice(0, MAX_QUERY);
    next.query = window.T9_normalize(next.q);
    var devices = collectValues(params, "device", allowed.devices);
    next.device = devices.length ? devices[0] : null;
    next.styles = collectValues(params, "style", allowed.styles);
    next.ratios = collectValues(params, "ratio", allowed.ratios);
    params.getAll("wallpaper").forEach(function (id) {
      if (!next.wallpaper && byId[id]) next.wallpaper = id;
    });
    return next;
  }

  function queryString() {
    var params = new URLSearchParams();
    if (state.q) params.set("q", state.q.slice(0, MAX_QUERY));
    if (state.device) params.set("device", state.device);
    if (state.styles.length) params.set("style", state.styles.join(","));
    if (state.ratios.length) params.set("ratio", state.ratios.join(","));
    if (state.wallpaper && byId[state.wallpaper]) params.set("wallpaper", state.wallpaper);
    return params.toString();
  }

  function syncLangLink(query) {
    var other = (query || "") ? "?" + query : "";
    document.querySelectorAll(".lang-switch a").forEach(function (link) {
      if (link.getAttribute("hreflang") === app.lang) return;
      link.setAttribute("href", app.otherPath + other);
    });
  }

  function writeLocation() {
    var query = queryString();
    var next = window.location.pathname + (query ? "?" + query : "");
    try {
      window.history.replaceState({ path: next }, "", next);
    } catch (err) {
      /* file:// or blocked history: filtering still works, only the address stays put */
    }
    syncLangLink(query);
  }

  /* —— lightbox —— */
  function attrRow(label, value) {
    var row = document.createElement("div");
    var strong = document.createElement("strong");
    strong.textContent = label;
    row.appendChild(strong);
    row.appendChild(document.createTextNode(" " + value));
    return row;
  }

  function ratioLabel(item) {
    var label = t["ratio." + item.ratio] || item.ratio;
    if (item.w && item.h) return label + " · " + item.w + " × " + item.h;
    return label;
  }

  function deviceLabel(item) {
    return item.device_tags.map(function (tag) {
      return deviceLabels[tag] || tag;
    }).join(", ");
  }

  function fillAttrs(item) {
    if (!els.lbAttrs) return;
    els.lbAttrs.textContent = "";
    [
      [t["lb.ratio"], ratioLabel(item)],
      [t["lb.style"], t["style." + item.style] || item.style],
      [t["lb.devices"], deviceLabel(item)],
      [t["lb.date"], item.created_at || "—"],
      [t["lb.id"], item.id]
    ].forEach(function (pair) {
      els.lbAttrs.appendChild(attrRow(pair[0], pair[1]));
    });
  }

  function downloadBlob(url, filename) {
    return fetch(url, { mode: "cors", cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("download fetch failed (" + response.status + ")");
      return response.blob();
    }).then(function (blob) {
      var objectUrl = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 4000);
    });
  }

  function runDownload(button) {
    if (!els.lbDownload) return Promise.resolve();
    var url = els.lbDownload.getAttribute("data-url");
    var filename = els.lbDownload.getAttribute("data-filename");
    if (!url || !filename) return Promise.resolve();
    if (button) button.setAttribute("aria-busy", "true");
    return downloadBlob(url, filename).catch(function (err) {
      if (window.console) window.console.error(err);
      var item = byId[state.wallpaper];
      if (item && els.lbTitle) {
        els.lbTitle.textContent = fill(t["lb.downloadFailed"], { title: item.title });
      }
    }).then(function () {
      if (button) button.setAttribute("aria-busy", "false");
    });
  }

  function openLightbox(item, silent) {
    if (!item) return;
    if (!silent) lastTrigger = document.activeElement;
    var full = window.T9_src(item, "full");
    var filename = window.T9_downloadName(item, full);
    els.lbImg.src = item.img.preview || full;
    els.lbImg.alt = item.alt || item.title || "";
    els.lbTitle.textContent = item.title;
    fillAttrs(item);
    els.lbDownload.setAttribute("href", "#");
    els.lbDownload.setAttribute("download", filename);
    els.lbDownload.setAttribute("aria-busy", "false");
    els.lbDownload.setAttribute("data-url", full);
    els.lbDownload.setAttribute("data-filename", filename);
    els.lightbox.hidden = false;
    els.lightbox.classList.add("is-open");
    if (!silent) els.lbClose.focus();

    state.wallpaper = item.id;
    if (!silent) writeLocation();
  }

  function closeLightbox(silent) {
    if (!els.lightbox || !els.lightbox.classList.contains("is-open")) {
      if (!silent) {
        state.wallpaper = null;
        writeLocation();
      }
      return;
    }
    els.lightbox.classList.remove("is-open");
    els.lightbox.hidden = true;
    state.wallpaper = null;
    if (!silent) {
      writeLocation();
      if (lastTrigger && lastTrigger.focus) lastTrigger.focus();
      lastTrigger = null;
    }
  }

  function syncLightbox() {
    if (state.wallpaper && byId[state.wallpaper]) openLightbox(byId[state.wallpaper], true);
    else closeLightbox(true);
  }

  /* —— hero strip —— */
  function bindStrip() {
    var strip = els.strip;
    if (!strip) return;
    var suppressClick = false;
    var down = false;
    var startX = 0;
    var startLeft = 0;
    var moved = false;

    function updateLit() {
      var middle = strip.scrollLeft + strip.clientWidth / 2;
      var figures = Array.prototype.slice.call(strip.querySelectorAll("figure"));
      var best = null;
      var bestDistance = Infinity;
      figures.forEach(function (figure) {
        var centre = figure.offsetLeft + figure.offsetWidth / 2;
        var distance = Math.abs(centre - middle);
        if (distance < bestDistance) {
          bestDistance = distance;
          best = figure;
        }
        figure.classList.remove("is-lit");
      });
      if (best) {
        best.classList.add("is-lit");
        var item = byId[best.getAttribute("data-id")];
        if (els.caption) els.caption.textContent = item ? item.title : "";
      }
    }

    strip.addEventListener("scroll", function () {
      window.requestAnimationFrame(updateLit);
    }, { passive: true });

    strip.addEventListener("pointerdown", function (event) {
      down = true;
      moved = false;
      startX = event.clientX;
      startLeft = strip.scrollLeft;
      strip.classList.add("is-dragging");
      if (strip.setPointerCapture) strip.setPointerCapture(event.pointerId);
    });
    strip.addEventListener("pointermove", function (event) {
      if (!down) return;
      var delta = event.clientX - startX;
      if (Math.abs(delta) > 6) moved = true;
      strip.scrollLeft = startLeft - delta;
    });
    function endDrag() {
      down = false;
      suppressClick = moved;
      strip.classList.remove("is-dragging");
    }
    strip.addEventListener("pointerup", endDrag);
    strip.addEventListener("pointercancel", endDrag);

    strip.addEventListener("click", function (event) {
      if (suppressClick) {
        suppressClick = false;
        return;
      }
      var figure = closest(event.target, "figure[data-id]");
      if (!figure) return;
      openLightbox(byId[figure.getAttribute("data-id")]);
    });

    updateLit();
  }

  /* —— wiring —— */
  function bindFilters() {
    if (els.q) {
      els.q.addEventListener("input", function (event) {
        var raw = String(event.target.value || "").slice(0, MAX_QUERY);
        state.q = raw;
        state.query = window.T9_normalize(raw);
        renderSheet();
        writeLocation();
      });
    }

    document.addEventListener("click", function (event) {
      var button = closest(event.target, "[data-style],[data-ratio],[data-device]");
      if (!button) return;
      if (button.hasAttribute("data-style")) {
        var style = button.getAttribute("data-style");
        var styleIndex = state.styles.indexOf(style);
        if (styleIndex === -1) state.styles.push(style);
        else state.styles.splice(styleIndex, 1);
        state.styles.sort(orderBy(allowed.styles));
      } else if (button.hasAttribute("data-ratio")) {
        var ratio = button.getAttribute("data-ratio");
        var ratioIndex = state.ratios.indexOf(ratio);
        if (ratioIndex === -1) state.ratios.push(ratio);
        else state.ratios.splice(ratioIndex, 1);
        state.ratios.sort(orderBy(allowed.ratios));
      } else {
        var device = button.getAttribute("data-device");
        state.device = state.device === device ? null : device;
      }
      syncChips();
      renderSheet();
      writeLocation();
    });
  }

  function bindSheet() {
    if (els.grid) {
      els.grid.addEventListener("click", function (event) {
        var frame = closest(event.target, ".frame[data-id]");
        if (!frame) return;
        openLightbox(byId[frame.getAttribute("data-id")]);
      });
      els.grid.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " " && event.key !== "Spacebar") return;
        var frame = closest(event.target, ".frame[data-id]");
        if (!frame) return;
        event.preventDefault();
        openLightbox(byId[frame.getAttribute("data-id")]);
      });
      els.grid.addEventListener("mouseenter", function () {
        if (els.sheet) els.sheet.classList.add("is-dimming");
      }, true);
      els.grid.addEventListener("mouseleave", function () {
        if (els.sheet) els.sheet.classList.remove("is-dimming");
      });
    }

    ["quietRow", "showRun"].forEach(function (id) {
      var row = document.getElementById(id);
      if (!row) return;
      row.addEventListener("click", function (event) {
        var figure = closest(event.target, "[data-id]");
        if (!figure) return;
        openLightbox(byId[figure.getAttribute("data-id")]);
      });
    });
  }

  function bindLightbox() {
    if (!els.lightbox) return;
    els.lbClose.addEventListener("click", function () { closeLightbox(); });
    els.lightbox.addEventListener("click", function (event) {
      if (event.target === els.lightbox) closeLightbox();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && els.lightbox.classList.contains("is-open")) closeLightbox();
    });
    els.lbDownload.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      runDownload(els.lbDownload);
    });
    els.lbSave.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      runDownload(els.lbSave);
    });
  }

  function entrances() {
    if (reduced || !("IntersectionObserver" in window)) {
      document.querySelectorAll(".reveal, .rise").forEach(function (element) {
        element.classList.add("is-in");
        element.style.opacity = "1";
        element.style.transform = "none";
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach(function (element) {
      observer.observe(element);
    });
    document.querySelectorAll(".rise").forEach(function (element, index) {
      element.style.transitionDelay = (index % 8) * 70 + "ms";
    });

    document.querySelectorAll(".hero-top > *").forEach(function (element, index) {
      element.style.opacity = "0";
      element.style.transform = "translateY(16px)";
      element.style.transition = "opacity 800ms cubic-bezier(0.22,1,0.36,1), transform 800ms cubic-bezier(0.22,1,0.36,1)";
      element.style.transitionDelay = (60 + index * 80) + "ms";
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          element.style.opacity = "1";
          element.style.transform = "none";
        });
      });
    });

    var figures = els.strip ? els.strip.querySelectorAll("figure") : [];
    Array.prototype.slice.call(figures).forEach(function (figure, index) {
      figure.style.opacity = "0";
      figure.style.transform = "translateY(12px)";
      figure.style.transition = "opacity 700ms cubic-bezier(0.22,1,0.36,1), transform 700ms cubic-bezier(0.22,1,0.36,1), filter 180ms cubic-bezier(0.22,1,0.36,1)";
      figure.style.transitionDelay = (200 + index * 40) + "ms";
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          figure.style.opacity = "1";
          figure.style.transform = "none";
        });
      });
    });
  }

  function showLoadError() {
    var message = t["error.loadTitle"] || t["error.loadBody"] || "";
    if (els.count) els.count.textContent = message;
    if (els.empty) {
      els.empty.hidden = false;
      els.empty.textContent = t["error.loadBody"] || message;
    }
  }

  function reportEmptyPage(error) {
    var message = document.documentElement.getAttribute("data-load-error") || "";
    if (!message) {
      var zh = String(document.documentElement.getAttribute("lang") || "").indexOf("zh") === 0;
      message = zh
        ? "这一批没能加载。请用本地服务器打开，不要用 file:// 直接打开。"
        : "This batch did not load. Open via a local server, not as a file:// page.";
    }
    var count = document.getElementById("countLine");
    var empty = document.getElementById("emptyMsg");
    if (count) count.textContent = message;
    if (empty) {
      empty.hidden = false;
      empty.textContent = message;
    }
    if (window.console) window.console.error(error);
  }

  function applyState(next) {
    state.q = next.q;
    state.query = next.query;
    state.device = next.device;
    state.styles = next.styles;
    state.ratios = next.ratios;
    state.wallpaper = next.wallpaper;
  }

  function start() {
    applyState(readLocation());
    if (els.q) els.q.value = state.q;
    syncChips();
    bindFilters();
    bindSheet();
    bindLightbox();
    bindStrip();
    renderSheet();
    syncLightbox();
    syncLangLink(queryString());
    entrances();
    window.addEventListener("popstate", function () {
      applyState(readLocation());
      if (els.q) els.q.value = state.q;
      syncChips();
      renderSheet();
      syncLightbox();
      syncLangLink(queryString());
    });
  }

  try {
    start();
  } catch (err) {
    showLoadError();
    if (window.console) window.console.error(err);
  }
})();

// Language switcher: renders tab buttons in the MkDocs Material **header** bar,
// rewrites the current URL to point at the same page in another edition, and
// dynamically updates the left sidebar navigation links to match.
//
// URL mapping rules (from mkdocs.yml → extra.languages):
//   zh: book/chapter1.md       (default, no suffix)
//   en: book-en/chapter1.md
//   ta: book-ta/chapter1.ta.md   (.ta suffix before .md)
//   vi: book-vi/chapter1.vi.md   (.vi suffix before .md)

(function () {
  "use strict";

  const cfg = window.config.extra?.languages;
  if (!cfg) return;

  // ── helpers ────────────────────────────────────────────────────

  /** Detect active language code from the current URL path. */
  function detectLang(path) {
    const p = path.replace(/\/$/, "");
    for (const [code, lang] of Object.entries(cfg)) {
      if (p.includes(lang.prefix)) return code;
    }
    return Object.entries(cfg).find(([, l]) => l.default)?.[0] || "zh";
  }

  /** Map the current URL to the equivalent page in *targetLang*. */
  function mapUrl(currentPath, targetLang) {
    if (targetLang === currentLang) return null;
    const src = cfg[currentLang];
    const dst = cfg[targetLang];

    let url = currentPath;
    url = url.replace(src.prefix, dst.prefix);
    if (src.suffix) url = url.replace(src.suffix + ".md", ".md");
    if (dst.suffix) url = url.replace(/\.md$/, dst.suffix + ".md");
    return (
      url ||
      dst.prefix + "introduction" + (dst.suffix || "") + ".md"
    );
  }

  // ── sidebar rewriting ──────────────────────────────────────────
  // Every sidebar link (<a>) is rewritten so its href points at the
  // currently-active edition rather than the default (Chinese) one.

  function rewriteSidebar(targetCode) {
    const target = cfg[targetCode];
    const defaultLang = Object.entries(cfg).find(([, l]) => l.default)?.[0] || "zh";

    document.querySelectorAll(".md-nav__link").forEach((el) => {
      let href = el.getAttribute("href");
      if (!href || href.startsWith("http") || href.startsWith("#")) return;
      // Strip leading slash for consistent processing.
      href = href.replace(/^\//, "");

      // Replace default prefix → target prefix.
      const defPrefix = cfg[defaultLang].prefix.replace(/\/$/, "");
      const tgtPrefix = target.prefix.replace(/\/$/, "");
      if (defPrefix && href.startsWith(defPrefix)) {
        href = tgtPrefix + href.slice(defPrefix.length);
      }

      // Handle suffixes.
      const defSuffix = cfg[defaultLang].suffix || "";
      const tgtSuffix = target.suffix || "";
      if (defSuffix) {
        href = href.replace(defSuffix + ".html", ".html");
      }
      if (tgtSuffix && href.endsWith(".html")) {
        href = href.replace(/\.html$/, tgtSuffix + ".html");
      }

      el.setAttribute("href", "/" + href);
    });
  }

  // ── render & mount ─────────────────────────────────────────────

  function render() {
    const path = location.pathname;
    const currentLang = detectLang(path);

    // ── inject tab bar into the header (next to search / repo icon) ──
    const headerInner =
      document.querySelector(".md-header__inner") ??
      document.querySelector(".md-header > nav") ??
      document.querySelector("header.md-header nav");

    if (!headerInner) return;

    // Avoid double-mounting.
    if (document.getElementById("lang-tabs-root")) return;

    const root = document.createElement("div");
    root.id = "lang-tabs-root";
    root.className = "lang-tabs-wrap";
    root.setAttribute("role", "tablist");
    root.setAttribute("aria-label", "Language");

    for (const [code, lang] of Object.entries(cfg)) {
      const btn = document.createElement("button");
      btn.className =
        "lang-tab" + (code === currentLang ? " lang-tab--active" : "");
      btn.textContent = lang.label;
      btn.dataset.lang = code;

      btn.addEventListener("click", () => {
        if (code === currentLang) return;
        const target = mapUrl(path, code);
        if (target) location.href = target;
      });

      root.appendChild(btn);
    }

    // Insert before the right-side group (search, repo link, …).
    const rightGroup =
      headerInner.querySelector(".md-header__source") ??
      headerInner.querySelector("[class*='source']") ??
      Array.from(headerInner.children).pop();
    headerInner.insertBefore(root, rightGroup);

    // ── rewrite sidebar for non-default languages ──
    if (currentLang !== (Object.entries(cfg).find(([, l]) => l.default)?.[0] || "zh")) {
      rewriteSidebar(currentLang);
    }
  }

  // MkDocs instant-navigation may not fire DOMContentLoaded again.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    // Run immediately; also re-run after SPA navigation.
    render();
    document.addEventListener("locationchange", render);
    // Fallback: watch URL changes for instant-nav.
    const origPushState = history.pushState;
    history.pushState = function () {
      origPushState.apply(this, arguments);
      setTimeout(render, 50);
    };
  }
})();

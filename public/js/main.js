/* Quill's site: the nav, the pictures that ease in from the margins, the hero video's pause button, and the download links. */
(function () {
  "use strict";

  var REPO = "sadmicrowave/quill-dictation-app";

  // --- the nav turns solid once the page has moved
  var nav = document.getElementById("nav");
  function onScroll() {
    if (!nav) return;
    var solid = window.scrollY > 40;
    nav.dataset.solid = solid ? "true" : "false";
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // --- pictures and text ease in once, when their row comes into view. (The row is watched, not the picture itself: a picture that
  // is waiting off to the side of the page would never count as visible.)
  var targets = document.querySelectorAll(".reveal-left, .reveal-right, .reveal-up");
  var rows = new Map();
  targets.forEach(function (el) {
    var row = el.parentElement;
    if (!rows.has(row)) rows.set(row, []);
    rows.get(row).push(el);
  });
  if ("IntersectionObserver" in window) {
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          (rows.get(entry.target) || []).forEach(function (el) { el.classList.add("is-visible"); });
          seen.unobserve(entry.target);
        }
      });
    }, { threshold: 0.25, rootMargin: "0px 0px -6% 0px" });
    rows.forEach(function (_, row) { seen.observe(row); });
  } else {
    targets.forEach(function (el) { el.classList.add("is-visible"); });
  }

  // --- the hero video: starts by itself (muted); a button pauses it
  var video = document.getElementById("hero-video");
  var toggle = document.getElementById("hero-toggle");
  if (video) {
    var attempt = video.play();
    if (attempt && attempt.catch) attempt.catch(function () { /* the browser wants a click first: the poster stays */ });
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) video.pause();
  }
  if (video && toggle) {
    var label = function () { toggle.setAttribute("aria-label", video.paused ? "Play the video" : "Pause the video"); toggle.dataset.paused = video.paused; };
    toggle.addEventListener("click", function () { video.paused ? video.play() : video.pause(); });
    video.addEventListener("play", label);
    video.addEventListener("pause", label);
    label();
  }

  // --- the download links follow the newest GitHub release, so the site never needs a rebuild per release
  var os = /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent) ? "mac" : /Win/i.test(navigator.platform || navigator.userAgent) ? "windows" : "other";
  document.documentElement.dataset.os = os;

  function pick(assets, kind) {
    var rules = kind === "mac" ? [/\.dmg$/i, /mac.*\.zip$/i, /darwin|macos|osx/i] : [/\.exe$/i, /\.msi$/i, /win.*\.zip$/i, /windows/i];
    for (var i = 0; i < rules.length; i++) {
      var hit = assets.find(function (a) { return rules[i].test(a.name); });
      if (hit) return hit;
    }
    return null;
  }
  function mb(bytes) { return bytes ? " · " + Math.max(1, Math.round(bytes / 1048576)) + " MB" : ""; }

  function showRelease(release) {
    var tag = release && release.tag_name ? release.tag_name.replace(/^v/i, "") : "";
    document.querySelectorAll("[data-version]").forEach(function (el) { el.textContent = tag ? "Version " + tag : "Coming soon"; });
    document.querySelectorAll("[data-release-page]").forEach(function (el) { el.href = (release && release.html_url) || "https://github.com/" + REPO + "/releases"; });
    ["mac", "windows"].forEach(function (kind) {
      var asset = release && release.assets ? pick(release.assets, kind) : null;
      document.querySelectorAll('[data-download="' + kind + '"]').forEach(function (el) {
        if (asset) {
          el.href = asset.browser_download_url;
          el.removeAttribute("aria-disabled");
          var size = el.querySelector("[data-size]");
          if (size) size.textContent = mb(asset.size).replace(/^ · /, "");
        } else {
          el.href = (release && release.html_url) || "https://github.com/" + REPO + "/releases";
          var s = el.querySelector("[data-size]");
          if (s) s.textContent = release ? "See the release" : "Release coming soon";
        }
      });
    });
  }

  var needs = document.querySelector("[data-download], [data-version]");
  if (needs) {
    var cached = null;
    try { cached = JSON.parse(sessionStorage.getItem("quill-release") || "null"); } catch (e) { /* private mode */ }
    if (cached) { showRelease(cached.release); }
    fetch("https://api.github.com/repos/" + REPO + "/releases/latest", { headers: { Accept: "application/vnd.github+json" } })
      .then(function (r) { return r.status === 404 ? null : r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (release) {
        try { sessionStorage.setItem("quill-release", JSON.stringify({ release: release })); } catch (e) { /* ignore */ }
        showRelease(release);
      })
      .catch(function () { if (!cached) showRelease(null); });
  }
})();

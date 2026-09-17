// Christina Sun — site behaviour.
// Three small jobs: mark images loaded so they fade in over their average
// colour, reveal elements as they scroll into view, and open PhotoSwipe.
// Everything degrades: if this script does not run, the html element keeps
// its no-js class and the CSS shows images and content at once.

document.documentElement.classList.replace("no-js", "js");

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// --- Image fade-in ---------------------------------------------------------

function markLoaded(img) {
  img.classList.add("is-loaded");
}
for (const img of document.querySelectorAll(".frame img, .cover-image img, .about-portrait img")) {
  if (img.complete && img.naturalWidth > 0) markLoaded(img);
  else img.addEventListener("load", () => markLoaded(img), { once: true });
  img.addEventListener("error", () => markLoaded(img), { once: true }); // never leave a blank box
}

// --- Reveal on scroll --------------------------------------------------------

const revealables = [...document.querySelectorAll(".reveal")];
const viewportHeight = window.innerHeight;

// Anything already on screen is revealed right away (with a short stagger),
// without waiting for an observer callback. Only elements below the fold
// are handed to IntersectionObserver.
const aboveFold = revealables.filter((el) => el.getBoundingClientRect().top < viewportHeight);
const belowFold = revealables.filter((el) => !aboveFold.includes(el));

if (reducedMotion || !("IntersectionObserver" in window)) {
  revealables.forEach((el) => el.classList.add("is-in"));
} else {
  aboveFold.forEach((el, i) => setTimeout(() => el.classList.add("is-in"), Math.min(i * 60, 240)));
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("is-in");
      observer.unobserve(entry.target);
    }
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
  belowFold.forEach((el) => observer.observe(el));
  // Print shows the whole page at once.
  window.addEventListener("beforeprint", () => belowFold.forEach((el) => el.classList.add("is-in")));
}

// --- Mobile menu -------------------------------------------------------------

const toggle = document.querySelector(".menu-toggle");
const nav = document.getElementById("site-nav");
if (toggle && nav) {
  const setMenu = (open) => {
    nav.classList.toggle("is-open", open);
    document.body.classList.toggle("menu-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector(".menu-toggle-label").textContent = open ? "Close" : "Menu";
  };
  toggle.addEventListener("click", () => setMenu(!nav.classList.contains("is-open")));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("is-open")) { setMenu(false); toggle.focus(); }
  });
}

// --- Lightbox ----------------------------------------------------------------

const gallery = document.getElementById("gallery");
if (gallery) {
  // The lightbox stylesheet and module load only on pages with a gallery,
  // and only after the page is showing.
  const sheet = document.createElement("link");
  sheet.rel = "stylesheet";
  sheet.href = "/static/vendor/photoswipe/photoswipe.css";
  document.head.appendChild(sheet);
  import("/static/vendor/photoswipe/photoswipe-lightbox.esm.min.js").then(({ default: PhotoSwipeLightbox }) => {
  const lightbox = new PhotoSwipeLightbox({
    gallery: "#gallery",
    children: "a",
    pswpModule: () => import("/static/vendor/photoswipe/photoswipe.esm.min.js"),
    bgOpacity: 1,
    showHideAnimationType: reducedMotion ? "none" : "fade",
    zoom: false,
    counter: true,
    arrowPrev: false,
    arrowNext: false,
    close: true,
    padding: { top: 48, bottom: 56, left: 24, right: 24 },
  });
  // Caption element: reads data-caption from the clicked link.
  lightbox.on("uiRegister", () => {
    lightbox.pswp.ui.registerElement({
      name: "caption",
      order: 9,
      isButton: false,
      appendTo: "root",
      onInit: (el, pswp) => {
        pswp.on("change", () => {
          const link = pswp.currSlide.data.element;
          el.textContent = (link && link.dataset.caption) || "";
        });
      },
    });
  });
  lightbox.init();
  }).catch(() => { /* no lightbox; the photographs are still on the page */ });
}

// --- Landing slideshow -------------------------------------------------------
// Crossfade through the slides on a timer. Only the first slide ships with a
// src; each next slide is loaded while the current one is showing, so the
// page never downloads a photograph it has not reached yet. The timer stops
// when the tab is hidden and under prefers-reduced-motion the first slide
// simply stays.

const hero = document.querySelector(".hero");
if (hero) {
  const slides = [...hero.querySelectorAll(".hero-slide")];
  const hold = Number(hero.dataset.hold) || 6000;
  let current = 0;
  let timer = null;

  function load(img) {
    if (!img || !img.dataset.src) return;
    img.srcset = img.dataset.srcset;
    img.src = img.dataset.src;
    delete img.dataset.src;
    delete img.dataset.srcset;
  }
  function advance() {
    const next = (current + 1) % slides.length;
    if (!slides[next].complete || !slides[next].naturalWidth) return;   // not there yet: hold this slide
    slides[current].classList.remove("is-active");
    slides[next].classList.add("is-active");
    current = next;
    load(slides[(current + 1) % slides.length]);     // stay one slide ahead
  }
  function start() {
    if (timer || slides.length < 2 || reducedMotion) return;
    timer = setInterval(advance, hold);
  }
  function stop() {
    clearInterval(timer);
    timer = null;
  }

  if (!reducedMotion) {
    load(slides[1]);
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    if (!document.hidden) start();
  }
}


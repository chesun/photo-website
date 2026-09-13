// Christina Sun — site behaviour.
// Three small jobs: mark images loaded so they fade in over their average
// colour, reveal elements as they scroll into view, and open PhotoSwipe.
// Everything degrades: with JS off the CSS shows images and content at once.

import PhotoSwipeLightbox from "/static/vendor/photoswipe/photoswipe-lightbox.esm.min.js";

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
  // Safety net: if something never intersects (odd layouts, print), show it.
  setTimeout(() => belowFold.forEach((el) => el.classList.add("is-in")), 4000);
}

// --- Mobile menu -------------------------------------------------------------

const toggle = document.querySelector(".menu-toggle");
const nav = document.getElementById("site-nav");
if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    document.body.classList.toggle("menu-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector(".menu-toggle-label").textContent = open ? "Close" : "Menu";
  });
}

// --- Lightbox ----------------------------------------------------------------

const gallery = document.getElementById("gallery");
if (gallery) {
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
          el.textContent = pswp.currSlide.data.element?.dataset.caption || "";
        });
      },
    });
  });
  lightbox.init();
}

/* Shared behaviour: nav, reveal-on-scroll, progress bar, footer bits. */
(function () {
  const cfg = window.DTS_CONFIG || {};

  // Footer year + contact email
  const y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
  const ce = document.getElementById("contact-email");
  if (ce && cfg.CONTACT_EMAIL) { ce.href = "mailto:" + cfg.CONTACT_EMAIL; ce.textContent = cfg.CONTACT_EMAIL; }

  // Sticky nav shadow + progress bar
  const nav = document.querySelector(".nav");
  const bar = document.querySelector(".scroll-progress");
  const onScroll = () => {
    const sc = window.scrollY || document.documentElement.scrollTop;
    if (nav) nav.classList.toggle("scrolled", sc > 8);
    if (bar) {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (h > 0 ? (sc / h) * 100 : 0) + "%";
    }
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Mobile menu
  const toggle = document.querySelector(".nav-toggle");
  const links = document.getElementById("navlinks");
  if (toggle && links) {
    const setOpen = (open) => {
      toggle.classList.toggle("open", open);
      links.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    };
    toggle.addEventListener("click", () => setOpen(!links.classList.contains("open")));
    links.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setOpen(false)));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  }

  // Smooth anchor scrolling with sticky-nav offset (native scroll-behavior handles the easing)
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href").slice(1);
      const el = id && document.getElementById(id);
      if (!el) return;
      e.preventDefault();
      const top = el.getBoundingClientRect().top + window.scrollY - 70;
      window.scrollTo({ top, behavior: "smooth" });
      history.replaceState(null, "", "#" + id);
    });
  });

  // Reveal on scroll
  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.12 });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("in"));
  }
})();

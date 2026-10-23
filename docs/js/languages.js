/* Keep the reader at the same section when switching between static pages. */
(() => {
  const links = document.querySelectorAll('[data-language-link]');
  const sync = () => {
    for (const link of links) {
      const next = new URL(link.getAttribute('href'), location.href);
      next.hash = location.hash;
      link.href = next.href;
    }
  };
  sync();
  window.addEventListener('hashchange', sync);
})();

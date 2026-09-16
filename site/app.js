// Progressive enhancement only. All evidence and navigation render without JS.
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', () => {
    document.querySelectorAll('nav a').forEach(item => item.removeAttribute('aria-current'));
    if (link.closest('nav')) link.setAttribute('aria-current', 'location');
  });
});

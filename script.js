const menuButton = document.querySelector('.menu-toggle');
const leafLayer = document.querySelector('.falling-leaves');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (leafLayer && !reduceMotion) {
  const leafSymbols = ['🍂', '🍁', '🍂', '🍃'];
  const leafColors = ['#d17a4d', '#b8473e', '#e3a36d', '#a95a43'];

  for (let index = 0; index < 22; index += 1) {
    const leaf = document.createElement('span');
    const random = (min, max) => Math.random() * (max - min) + min;

    leaf.className = 'falling-leaf';
    leaf.textContent = leafSymbols[index % leafSymbols.length];
    leaf.style.setProperty('--leaf-x', `${random(0, 100)}vw`);
    leaf.style.setProperty('--leaf-size', `${random(12, 25)}px`);
    leaf.style.setProperty('--leaf-duration', `${random(13, 25)}s`);
    leaf.style.setProperty('--leaf-delay', `${random(-25, 0)}s`);
    leaf.style.setProperty('--leaf-drift', `${random(-90, 90)}px`);
    leaf.style.setProperty('--leaf-color', leafColors[index % leafColors.length]);
    leaf.style.setProperty('--leaf-opacity', random(0.35, 0.75).toFixed(2));
    leaf.style.setProperty('--leaf-blur', `${random(0, 1.2).toFixed(1)}px`);
    leafLayer.append(leaf);
  }
}

const nav = document.querySelector('.nav');

menuButton?.addEventListener('click', () => {
  const isOpen = nav.classList.toggle('open');

  menuButton.setAttribute('aria-expanded', String(isOpen));
  menuButton.setAttribute(
    'aria-label',
    isOpen ? 'Close navigation' : 'Open navigation'
  );
});

document.querySelectorAll('.nav a').forEach((link) => {
  link.addEventListener('click', () => {
    nav.classList.remove('open');
    menuButton?.setAttribute('aria-expanded', 'false');
  });
});

const progressBar = document.querySelector('.progress');

function updateScrollProgress() {
  const maxScroll =
    document.documentElement.scrollHeight - window.innerHeight;

  const progress = maxScroll > 0
    ? (window.scrollY / maxScroll) * 100
    : 0;

  progressBar.style.width = `${progress}%`;
}

window.addEventListener('scroll', updateScrollProgress, { passive: true });
updateScrollProgress();

const revealTargets = document.querySelectorAll(
  '.section-kicker, .intro-grid, .section-heading, .project-card, ' +
  '.interlude p, .journey-grid, .toolkit, .contact-inner'
);

revealTargets.forEach((element) => {
  element.classList.add('reveal');
});

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  revealTargets.forEach((element) => observer.observe(element));
} else {
  revealTargets.forEach((element) => {
    element.classList.add('visible');
  });
}

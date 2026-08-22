(() => {
  const menuButton = document.querySelector('#menu-button');
  const mobileMenu = document.querySelector('#mobile-menu');
  if (menuButton && mobileMenu) {
    menuButton.addEventListener('click', () => {
      const opening = mobileMenu.classList.contains('hidden');
      mobileMenu.classList.toggle('hidden');
      menuButton.setAttribute('aria-expanded', String(opening));
    });
  }

  const search = document.querySelector('#live-search');
  const asset = document.querySelector('#asset-filter');
  const evidence = document.querySelector('#evidence-filter');
  const cards = [...document.querySelectorAll('#product-grid .product-card')];
  const count = document.querySelector('#visible-count');
  const empty = document.querySelector('#empty-state');

  const applyLiveFilters = () => {
    if (!cards.length) return;
    const query = (search?.value || '').trim().toLowerCase();
    const assetValue = asset?.value || 'all';
    const evidenceValue = evidence?.value || 'all';
    let visible = 0;
    cards.forEach((card) => {
      const matchesSearch = !query || card.dataset.search.includes(query);
      const matchesAsset = assetValue === 'all' || card.dataset.asset === assetValue;
      const matchesEvidence = evidenceValue === 'all' || card.dataset.evidence.startsWith(evidenceValue);
      const show = matchesSearch && matchesAsset && matchesEvidence;
      card.classList.toggle('hidden', !show);
      if (show) visible += 1;
    });
    if (count) count.textContent = String(visible);
    empty?.classList.toggle('hidden', visible !== 0);
  };

  search?.addEventListener('input', applyLiveFilters);
  asset?.addEventListener('change', applyLiveFilters);
  evidence?.addEventListener('change', applyLiveFilters);
})();

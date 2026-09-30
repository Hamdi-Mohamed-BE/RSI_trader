// Calyx order page: copy buttons, countdown and payment status polling.
(() => {
  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const source = document.querySelector(`[data-copy-source="${button.dataset.copy}"]`);
      if (!source) return;
      const text = source.textContent.trim();
      try {
        await navigator.clipboard.writeText(text);
      } catch (_error) {
        const range = document.createRange();
        range.selectNodeContents(source);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
      const label = button.textContent;
      button.textContent = 'Copied';
      setTimeout(() => { button.textContent = label; }, 1400);
    });
  });

  const box = document.querySelector('[data-payment-box]');
  if (!box) return;
  const countdown = box.querySelector('[data-countdown]');
  const chainStatus = box.querySelector('[data-chain-status]');
  const deadline = Date.now() + Number(box.dataset.secondsLeft || 0) * 1000;

  const tick = () => {
    const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    const minutes = Math.floor(left / 60);
    const seconds = String(left % 60).padStart(2, '0');
    if (countdown) countdown.textContent = left > 0 ? `${minutes}:${seconds}` : 'expired';
  };
  tick();
  setInterval(tick, 1000);

  const poll = async () => {
    try {
      const response = await fetch(box.dataset.statusUrl, { cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      if (data.status !== 'pending') {
        window.location.reload();
        return;
      }
      if (chainStatus) {
        chainStatus.textContent = data.detected
          ? `payment detected, ${data.confirmations}/${data.required} confirmations`
          : 'not detected yet';
      }
    } catch (_error) {
      /* network hiccup: try again on the next interval */
    }
  };
  setInterval(poll, 15000);
})();

// Progressive enhancement only; every page works without JavaScript.
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (form instanceof HTMLFormElement && form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
  }
});

const refresh = document.querySelector("[data-auto-refresh]");
if (refresh) {
  window.setInterval(() => {
    if (!document.hidden && !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
      window.location.reload();
    }
  }, Number(refresh.dataset.autoRefresh) * 1000);
}

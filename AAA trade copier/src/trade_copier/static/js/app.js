(() => {
    const indicator = document.getElementById("live-connection");
    if (!indicator) return;

    const refreshStatus = async () => {
        try {
            const response = await window.fetch("/api/status", {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            });
            if (!response.ok) throw new Error(`Status ${response.status}`);
            const status = await response.json();
            indicator.textContent = `Status connected · ${status.execution_mode} · ${status.jobs} jobs`;
            indicator.classList.add("text-green");
        } catch {
            indicator.textContent = "Status reconnecting…";
            indicator.classList.remove("text-green");
        } finally {
            window.setTimeout(refreshStatus, 5000);
        }
    };

    refreshStatus();
})();

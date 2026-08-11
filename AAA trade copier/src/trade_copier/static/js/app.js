(() => {
    const indicator = document.getElementById("live-connection");
    if (!indicator || !window.WebSocket) return;

    let reconnectTimer;
    const connect = () => {
        const scheme = window.location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${scheme}://${window.location.host}/ws/status`);
        socket.addEventListener("open", () => {
            indicator.textContent = "Live status connected";
            indicator.classList.add("text-green");
        });
        socket.addEventListener("message", (event) => {
            const message = JSON.parse(event.data);
            if (message.type === "source_event.processed") {
                indicator.textContent = `Processed ${message.job_count} follower decisions · refresh for details`;
            }
        });
        socket.addEventListener("close", () => {
            indicator.textContent = "Live status reconnecting…";
            indicator.classList.remove("text-green");
            window.clearTimeout(reconnectTimer);
            reconnectTimer = window.setTimeout(connect, 2500);
        });
    };
    connect();
})();


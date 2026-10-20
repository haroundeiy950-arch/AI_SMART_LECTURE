document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-menu-toggle]");
    const menu = document.querySelector("[data-menu]");
    if (toggle && menu) toggle.addEventListener("click", () => menu.classList.toggle("open"));

    document.querySelectorAll(".message").forEach((item) => {
        window.setTimeout(() => {
            item.style.opacity = "0";
            item.style.transition = "opacity .35s";
        }, 5000);
    });

    if (document.body.dataset.authenticated !== "true") return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/notifications/`);
    socket.addEventListener("message", (event) => {
        let payload;
        try { payload = JSON.parse(event.data); } catch { return; }
        if (payload.type !== "notification") return;
        const badge = document.querySelector("[data-notification-count]");
        if (badge) {
            const count = Number.parseInt(badge.textContent || "0", 10) + 1;
            badge.textContent = String(count);
            badge.hidden = false;
        }
        const stack = document.querySelector("[data-toast-stack]");
        if (stack) {
            const toast = document.createElement("div");
            toast.className = "toast";
            const link = document.createElement("a");
            link.href = payload.link || "/notifications/";
            link.textContent = payload.text || "New notification";
            toast.appendChild(link);
            stack.appendChild(toast);
            window.setTimeout(() => toast.remove(), 7000);
        }
    });
});

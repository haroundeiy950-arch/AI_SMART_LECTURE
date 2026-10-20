document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-chat-root]");
    if (!root) return;
    const list = root.querySelector("[data-chat-messages]");
    const form = root.querySelector("[data-chat-form]");
    const textarea = form?.querySelector("textarea");
    const conversationId = root.dataset.conversationId;
    const userId = Number.parseInt(root.dataset.userId, 10);
    if (list) list.scrollTop = list.scrollHeight;
    if (!form || !textarea) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/${conversationId}/`);
    let socketReady = false;
    socket.addEventListener("open", () => { socketReady = true; });
    socket.addEventListener("close", () => { socketReady = false; });

    const appendMessage = (payload) => {
        const article = document.createElement("article");
        article.className = `chat-bubble${payload.sender_id === userId ? " mine" : ""}`;
        const strong = document.createElement("strong");
        strong.textContent = payload.sender_name || payload.sender_username;
        const paragraph = document.createElement("p");
        paragraph.textContent = payload.body;
        const time = document.createElement("time");
        time.textContent = payload.created_at || "";
        article.append(strong, paragraph, time);
        list.appendChild(article);
        list.scrollTop = list.scrollHeight;
    };

    socket.addEventListener("message", (event) => {
        let payload;
        try { payload = JSON.parse(event.data); } catch { return; }
        if (payload.type === "message") appendMessage(payload);
        if (payload.type === "error") window.alert(payload.message);
    });

    form.addEventListener("submit", (event) => {
        const message = textarea.value.trim();
        if (!message) { event.preventDefault(); return; }
        if (!socketReady) return; // Normal POST fallback.
        event.preventDefault();
        socket.send(JSON.stringify({message}));
        textarea.value = "";
        textarea.focus();
    });
});

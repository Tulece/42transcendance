window.initChat = () => {
    let ws = null;
    const connectWsButton = document.getElementById("connect-ws");
    const wsLog = document.getElementById("ws-log");
    const wsMessageInput = document.getElementById("ws-message");
    const sendWsMessageButton = document.getElementById("send-ws-message");

    function getJWTFromCookies() {
        const name = "access_token=";
        const decodedCookie = decodeURIComponent(document.cookie);
        const ca = decodedCookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i].trim();
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }

    // Vérifie si un JWT existe et active le bouton de connexion WebSocket
    const tokenFromCookie = getJWTFromCookies();
    if (tokenFromCookie) {
        connectWsButton.disabled = false;
    }

    // Connexion au WebSocket
    connectWsButton.addEventListener("click", () => {
        const jwtToken = getJWTFromCookies();
        if (!jwtToken) {
            alert("Vous devez vous connecter pour accéder au WebSocket.");
            return;
        }

        ws = new WebSocket(`ws://localhost:8000/ws/chat/?token=${jwtToken}`);

        ws.onopen = () => {
            wsLog.textContent += "WebSocket connecté.\n";
            wsMessageInput.disabled = false;
            sendWsMessageButton.disabled = false;
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "chat_message") {
                wsLog.textContent += `${data.username}: ${data.message}\n`;
            } else if (data.type === "welcome") {
                wsLog.textContent += `${data.message}\n`;
            }
        };

        ws.onerror = (error) => {
            wsLog.textContent += `Erreur WebSocket : ${error}\n`;
        };

        ws.onclose = () => {
            wsLog.textContent += "WebSocket déconnecté.\n";
            wsMessageInput.disabled = true;
            sendWsMessageButton.disabled = true;
        };
    });

    // Envoyer un message via WebSocket
    sendWsMessageButton.addEventListener("click", () => {
        const message = wsMessageInput.value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message }));
            wsLog.textContent += `Message envoyé : ${message}\n`;
            wsMessageInput.value = "";
        } else {
            wsLog.textContent += "WebSocket non connecté.\n";
        }
    });
};

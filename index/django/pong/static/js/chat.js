window.initChat = () => {
    console.log("initChat appelé");
    let ws = null;
    const connectWsButton = document.getElementById("connect-ws");
    const wsLog = document.getElementById("ws-log");
    const wsMessageInput = document.getElementById("ws-message");
    const sendWsMessageButton = document.getElementById("send-ws-message");

    // Fonction pour vérifier si l'utilisateur est authentifié
    async function checkAuthentication() {
        try {
            const response = await fetch("/api/user_info/", {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "include", // Inclure les cookies
            });

            if (response.ok) {
                const data = await response.json();
                if (data.username) {
                    connectWsButton.disabled = false;
                    console.log("Utilisateur authentifié :", data.username);
                } else {
                    connectWsButton.disabled = true;
                }
            } else {
                connectWsButton.disabled = true;
            }
        } catch (error) {
            console.error("Erreur lors de la vérification de l'authentification :", error);
            connectWsButton.disabled = true;
        }
    }

    // Appeler la fonction de vérification au chargement
    checkAuthentication();

    // Rafraîchir l'état d'authentification lorsqu'un utilisateur se connecte ou se déconnecte
    // Vous pouvez écouter des événements personnalisés ou utiliser des mécanismes de polling si nécessaire

    // Connexion au WebSocket
    connectWsButton.addEventListener("click", () => {
        ws = new WebSocket(`ws://${window.location.host}/ws/chat/`);

        ws.onopen = () => {
            wsLog.textContent += "WebSocket connecté.\n";
            wsMessageInput.disabled = false;
            sendWsMessageButton.disabled = false;
            console.log("WebSocket connecté.");
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
            console.error("Erreur WebSocket :", error);
        };

        ws.onclose = () => {
            wsLog.textContent += "WebSocket déconnecté.\n";
            wsMessageInput.disabled = true;
            sendWsMessageButton.disabled = true;
            console.log("WebSocket déconnecté.");
        };
    });

    // Envoyer un message via WebSocket
    sendWsMessageButton.addEventListener("click", () => {
        const message = wsMessageInput.value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message }));
            wsLog.textContent += `Message envoyé : ${message}\n`;
            wsMessageInput.value = "";
            console.log(`Message envoyé : ${message}`);
        } else {
            wsLog.textContent += "WebSocket non connecté.\n";
            console.warn("WebSocket non connecté.");
        }
    });
};

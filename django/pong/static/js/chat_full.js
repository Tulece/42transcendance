window.initChat = () => {
    console.log("initChat appelé");
    const wsLog = document.getElementById("ws-log");
    const chatLog = document.getElementById("chat-log");
    const chatInput = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-button");
    const userSelect = document.getElementById("user-select");
    const blockButton = document.getElementById("block-button");
    const unblockButton = document.getElementById("unblock-button");

    let ws = null;

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
    
    checkAuthentication();
    console.log("Cookies actuels :", document.cookie);

    // Initialiser le WebSocket dès le chargement
    const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("access_token="))
        ?.split("=")[1];

    if (!token) {
        console.error("Aucun token trouvé. Impossible de se connecter au WebSocket.");
        wsLog.textContent += "Erreur : Token manquant.\n";
        return;
    }

    console.log(`Tentative de connexion WebSocket avec le token : ${token}`);
    ws = new WebSocket('ws://localhost:8000/ws/chat/');
    //socket = new WebSocket('ws://localhost:8000/ws/game/1/?player_id=player1');

    ws.onopen = () => {
        console.log("WebSocket connecté.");
        wsLog.textContent += "WebSocket connecté.\n";
        chatInput.disabled = false;
        sendButton.disabled = false;
        blockButton.disabled = false;
        unblockButton.disabled = false;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const message = data.message;
        const sender = data.sender || "Anonyme";
        const time = new Date().toLocaleTimeString();

        chatLog.innerHTML += `<div><strong>${sender}:</strong> ${message} <span style="color: gray;">[${time}]</span></div>`;
        chatLog.scrollTop = chatLog.scrollHeight;
    };

    ws.onerror = (error) => {
        wsLog.textContent += `Erreur WebSocket : ${error}\n`;
        console.error("Erreur WebSocket :", error);
    };

    ws.onclose = () => {
        console.warn("WebSocket fermé. Tentative de reconnexion dans 3 secondes...");
        wsLog.textContent += "WebSocket déconnecté. Reconnexion dans 3 secondes...\n";
        setTimeout(() => {
            console.log("Reconnexion en cours...");
            window.initChat();
        }, 3000);
        chatInput.disabled = true;
        sendButton.disabled = true;
        blockButton.disabled = true;
        unblockButton.disabled = true;
    };

    sendButton.onclick = () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.error("WebSocket non connecté.");
            wsLog.textContent += "Erreur : WebSocket non connecté.\n";
            return;
        }

        const message = chatInput.value;
        const targetUserId = userSelect.value;

        if (!message) {
            console.warn("Message vide, rien à envoyer.");
            return;
        }

        const payload = { message };
        if (targetUserId) {
            payload.target_user_id = targetUserId;
        }

        console.log("Envoi du message :", payload);
        ws.send(JSON.stringify(payload));
        chatInput.value = "";
        wsLog.textContent += `Message envoyé : ${message}\n`;
    };
};

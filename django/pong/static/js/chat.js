window.initChat = () => {
    console.log("initChat appelé");
    let ws = null;
    const connectWsButton = document.getElementById("connect-ws");
    const wsLog = document.getElementById("ws-log");
    const wsMessageInput = document.getElementById("ws-message");
    const sendWsMessageButton = document.getElementById("send-ws-message");
    const messageList = document.getElementById("message-list"); // Conteneur pour les messages
    const privateMsgBtn = document.getElementById("send-private-btn");
    const targetUsernameInput = document.getElementById("target-username");
    const blockUsernameInput = document.getElementById("block-username");
    const blockBtn = document.getElementById("block-btn");
    const unblockUsernameInput = document.getElementById("unblock-username");
    const unblockBtn = document.getElementById("unblock-btn");

    // Fonction pour vérifier si l'utilisateur est authentifié
    async function checkAuthentication() {
        try {
            const response = await fetch("/api/user_info/", {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "include",
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

    // Connexion au WebSocket
    connectWsButton.addEventListener("click", () => {
        
        if (ws) {
            console.log("Déjà connecté !");
            return;
        }
        connectWsButton.disabled = true;
        ws = new WebSocket(`ws://${window.location.host}/ws/chat/`);

        ws.onopen = () => {
            addMessageToChat("System", "WebSocket connecté.");
            wsMessageInput.disabled = false;
            sendWsMessageButton.disabled = false;
            privateMsgBtn.disabled = false;
            blockBtn.disabled = false;
            unblockBtn.disabled = false;
            console.log("WebSocket connecté.");
        };
        // Message reçu du serveur
        ws.onmessage = (event) => {
            console.log("Message WebSocket reçu :", event.data);
            const data = JSON.parse(event.data);
            if (data.type === "chat_message") {
                const UserAndTime = `[${data.timestamp}] - ${data.username}`;
                addMessageToChat(UserAndTime, data.message);
            } else if (data.type === "private_message") {
                const UserAndTime = `[${data.timestamp}] - ${data.username}`;
                addMessageToChat(UserAndTime, data.message);
            } else if (data.type === "welcome") {
                addMessageToChat("System", data.message);
            }
        };

        ws.onerror = (error) => {
            addMessageToChat("System", `Erreur WebSocket : ${error}`);
            console.error("Erreur WebSocket :", error);
        };

        ws.onclose = () => {
            addMessageToChat("System", "WebSocket déconnecté.");
            wsMessageInput.disabled = true;
            sendWsMessageButton.disabled = true;
            privateMsgBtn.disabled = true;
            console.log("WebSocket déconnecté.");
        };
    });

    // Envoyer un message via WebSocket
    sendWsMessageButton.addEventListener("click", () => {
        const message = wsMessageInput.value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message }));
            //addMessageToChat("Moi", message);
            wsMessageInput.value = "";
            console.log(`Message envoyé : ${message}`);
        } else {
            addMessageToChat("System", "WebSocket non connecté.");
            console.warn("WebSocket non connecté.");
        }
    });

    // Fonction pour ajouter un message à la liste des messages
    function addMessageToChat(username, message) {
        const messageItem = document.createElement("div");
        messageItem.classList.add("message-item");
        messageItem.innerHTML = `<strong>${username}:</strong> ${message}`;
        messageList.appendChild(messageItem);
        messageList.scrollTop = messageList.scrollHeight; // Scroller automatiquement en bas
    }

    privateMsgBtn.addEventListener("click", () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            addMessageToChat("System", "WebSocket non connecté.");
            return;
        }
        const message = wsMessageInput.value;
        const targetUsername = targetUsernameInput.value.trim();
        if (!message || !targetUsername) {
            addMessageToChat("System", "Veuillez saisir un message et le pseudo du destinaire !");
            return;
        } // Send le message JSON (avec target id)
        ws.send(JSON.stringify({
            message: message,
            target_username: targetUsername
        }));
        wsMessageInput.value = ""; // Vider le champ mess.
        console.log(`Message privé envoyé à ${targetUsername}: ${message}`);
    });

    blockBtn.addEventListener("click", () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            addMessageToChat("System", "WebSocket non connecté. Impossible de bloquer l'utilisateur.");
            return;
        }
        const userToBlock = blockUsernameInput.value.trim();
        if (!userToBlock) {
            addMessageToChat("System", "Veuillez entrer un pseudo pour bloquer un utilisateur.");
            return;
        }
        ws.send(JSON.stringify({
            action: "block_user",
            username_to_block: userToBlock
        }));
        console.log(`Requête pour bloquer l'utilisateur : ${userToBlock}`);
    });
    
    unblockBtn.addEventListener("click", () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            addMessageToChat("System", "WebSocket non connecté. Impossible de débloquer l'utilisateur.");
            return;
        }
        const userToUnblock = unblockUsernameInput.value.trim();
        if (!userToUnblock) {
            addMessageToChat("System", "Veuillez entrer un pseudo pour débloquer un utilisateur.");
            return;
        }
        ws.send(JSON.stringify({
            action: "unblock_user",
            username_to_unblock: userToUnblock
        }));
        console.log(`Requête pour débloquer l'utilisateur : ${userToUnblock}`);
    });
    
};

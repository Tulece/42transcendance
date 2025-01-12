window.initChat = () => {
    let jwtToken = null;
    let ws = null;

    const jwtForm = document.getElementById("jwt-form");
    const jwtOutput = document.getElementById("jwt-output");
    const jwtTokenDisplay = document.getElementById("jwt-token");
    const connectWsButton = document.getElementById("connect-ws");
    const wsLog = document.getElementById("ws-log");
    const wsMessageInput = document.getElementById("ws-message");
    const sendWsMessageButton = document.getElementById("send-ws-message");

    // Générer le JWT
    jwtForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        try {
            const response = await fetch("/api/token/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ username, password }),
            });

            if (response.ok) {
                const data = await response.json();
                jwtToken = data.access;
                jwtOutput.style.display = "block";
                jwtTokenDisplay.textContent = jwtToken;
                connectWsButton.disabled = false;
            } else {
                jwtOutput.style.color = "red";
                jwtOutput.textContent = "Erreur lors de la génération du JWT.";
            }
        } catch (error) {
            console.error("Erreur lors de la génération du JWT :", error);
        }
    });

    // Connexion au WebSocket
    connectWsButton.addEventListener("click", () => {
        if (!jwtToken) {
            alert("Veuillez générer un JWT avant de vous connecter au WebSocket.");
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

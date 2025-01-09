// home.js
// On évite tout code auto-exécuté au top !
// On expose deux fonctions globales : initHome() et destroyHome()

window.jwtToken = "";  // On peut stocker ça globalement si on veut
window.ws = null;

window.initHome = function() {
    console.log("initHome() called");

    const generateJwtBtn = document.getElementById("generate-jwt");
    if (generateJwtBtn) {
        generateJwtBtn.onclick = async () => {
            const username = document.getElementById("jwt-username").value;
            const password = document.getElementById("jwt-password").value;
            if (!username || !password) {
                alert("Veuillez entrer un nom d'utilisateur et un mot de passe.");
                return;
            }

            // On envoie la requête vers /api/token/
            const response = await fetch("/api/token/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            if (response.ok) {
                const data = await response.json();
                window.jwtToken = data.access; // on stocke le token
                document.getElementById("jwt-display").textContent = `JWT: ${window.jwtToken}`;
                document.getElementById("jwt-error").textContent = "";
                console.log("JWT récupéré :", window.jwtToken);
            } else {
                const errorData = await response.json();
                document.getElementById("jwt-error").textContent =
                  `Erreur d'authentification : ${errorData.detail || "Inconnue"}`;
                window.jwtToken = "";
                console.error("Erreur JWT :", errorData);
            }
        };
    }

    // WebSocket test
    const connectWsBtn = document.getElementById("connect-ws");
    if (connectWsBtn) {
        connectWsBtn.onclick = () => {
            if (!window.jwtToken) {
                alert("Erreur : JWT manquant. Générez d'abord le token.");
                return;
            }
            // Exemple de connexion WS
            window.ws = new WebSocket(`ws://localhost:8000/ws/somepath/?token=${window.jwtToken}`);

            window.ws.onopen = () => {
                console.log("WebSocket connecté.");
                document.getElementById("ws-log").textContent += "\n[WS] Connecté.";
                document.getElementById("ws-message").disabled = false;
                document.getElementById("send-ws-message").disabled = false;
            };
            window.ws.onmessage = (evt) => {
                console.log("Message reçu :", evt.data);
                document.getElementById("ws-log").textContent += `\n[Srv] ${evt.data}`;
            };
            window.ws.onerror = (err) => {
                console.error("Erreur WebSocket :", err);
            };
            window.ws.onclose = () => {
                console.log("WebSocket fermé.");
                document.getElementById("ws-log").textContent += "\n[WS] Fermé";
                document.getElementById("ws-message").disabled = true;
                document.getElementById("send-ws-message").disabled = true;
            };
        };
    }

    const sendWsMessageBtn = document.getElementById("send-ws-message");
    if (sendWsMessageBtn) {
        sendWsMessageBtn.onclick = () => {
            if (window.ws && window.ws.readyState === WebSocket.OPEN) {
                const msg = document.getElementById("ws-message").value;
                window.ws.send(msg);
                console.log("Message envoyé :", msg);
                document.getElementById("ws-log").textContent += `\n[Vous] ${msg}`;
            } else {
                alert("Erreur : WebSocket non connecté.");
            }
        };
    }
};


window.destroyHome = function() {
    console.log("destroyHome() called");

    // retirer les eventListeners si besoin
    // fermer le ws si besoin
    if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        window.ws.close();
    }
    window.ws = null;

    // ex: removeEventListener s’il y en a
    const generateJwtBtn = document.getElementById("generate-jwt");
    if (generateJwtBtn) {
        generateJwtBtn.onclick = null;
    }
    // etc.
};

window.initChat = () => {
  console.log("DEBUG: chat.js chargé");
    // Initialisation des éléments HTML
    const messageList = document.getElementById("message-list");
    const messageInput = document.getElementById("message-input");
    const sendMessageBtn = document.getElementById("send-message-btn");
    const chatToggle = document.getElementById("chat-toggle");
    const messageArea = document.getElementById("message-area");
    const userList = document.getElementById("user-list");
    const privateRecipient = document.getElementById("private-recipient");
    const sendPrivateBtn = document.getElementById("send-private-btn");
  
    let ws = null;

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
                    console.log("Utilisateur authentifié :", data.username);
                } else {
                  console.log("⚠️ Utilisateur non authentifié.");
                }
            } else {
              console.log("⚠️ Impossible de récupérer l'authentification.");
            }
        } catch (error) {
            console.error("Erreur lors de la vérification de l'authentification :", error);
        }
    }

    // Appeler la fonction de vérification au chargement
    checkAuthentication();
  
    // Étape 1 : Connexion au WebSocket
    function connectWebSocket() {
      ws = new WebSocket(`ws://${window.location.host}/ws/chat/`);
  
      // Événement : connexion ouverte
      ws.onopen = () => {
        console.log("WebSocket connecté.");
        addSystemMessage("Vous êtes connecté au chat !");
        
      };
  
      // Événement : réception d'un message
      ws.onmessage = (event) => {
        console.log("📩 Message reçu :", event.data);
        const data = JSON.parse(event.data); // Les messages sont reçus sous forme JSON
        handleMessage(data); // Gérer le message reçu
      };
  
      // Événement : erreur
      ws.onerror = (error) => {
        console.error("Erreur WebSocket :", error);
        addSystemMessage("Erreur de connexion au WebSocket.");
      };
  
      // Événement : déconnexion
      ws.onclose = () => {
        console.log("WebSocket déconnecté.");
        addSystemMessage("Connexion au chat perdue.");
      };
    }
  
    // Étape 2 : Gestion des messages reçus
    function handleMessage(data) {
      if (data.type === "chat_message") {
        addMessageToChat(data.username, data.message);
      } else if (data.type === "private_message") {
        addPrivateMessageToChat(data.username, data.message);
      } else if (data.type === "system") {
        addSystemMessage(data.message);
      } else if (data.type === "user_list") {
        updateUserList(data.users);
      }
    }
  
    // Étape 3 : Ajouter un message utilisateur
    function addMessageToChat(username, message) {
      console.log("🖊️ Ajout d'un message dans le chat :", username, message);
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message");
      messageDiv.innerHTML = `<span class="username">${username} :</span> ${message}`;
      messageList.appendChild(messageDiv);
      scrollToBottom();
    }
  
    // Étape 4 : Ajouter un message privé
    function addPrivateMessageToChat(username, message) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "private");
      messageDiv.innerHTML = `<span class="username">${username} (privé) :</span> ${message}`;
      messageList.appendChild(messageDiv);
      scrollToBottom();
    }
  
    // Étape 5 : Ajouter un message système
    function addSystemMessage(message) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "system");
      messageDiv.innerText = message;
      messageList.appendChild(messageDiv);
      scrollToBottom();
    }
  
    // Étape 6 : Scroller automatiquement vers le bas
    function scrollToBottom() {
      messageArea.scrollTop = messageArea.scrollHeight;
    }
  
    // Étape 7 : Envoi d'un message utilisateur
    sendMessageBtn.addEventListener("click", () => {
      console.log("🖱️ Bouton Envoyer cliqué !");
      const message = messageInput.value;
      if (!message) return; // Ne pas envoyer de message vide

      console.log("📤 Envoi du message :", message);
  
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message })); // Envoi du message sous forme JSON
        messageInput.value = ""; // Réinitialise le champ input
      } else {
        addSystemMessage("WebSocket non connecté.");
      }
    });
  
    // Étape 8 : Gestion du bouton "Réduire"
    chatToggle.addEventListener("click", () => {
      if (messageArea.style.display === "none") {
        messageArea.style.display = "block";
        chatToggle.innerText = "Réduire";
      } else {
        messageArea.style.display = "none";
        chatToggle.innerText = "Ouvrir";
      }
    });

    sendPrivateBtn.addEventListener("click", () => {
      const recipient = privateRecipient.value;
      const message = messageInput.value.trim();

      if (!recipient || !message) {
        addSystemMessage("Veuillez sélectiionner un destinataire et écrire un message.");
        return;
      }

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: "private_message",
            target_username: recipient,
            message: message,
          })
        );
        messageInput.value = "";
      } else {
        addSystemMessage("Websocket non connecté.");
      }
    });

    function updateUserList(users) {
      console.log("👥 Mise à jour de la liste des utilisateurs :", users);
      userList.innerHTML = "";
    
      users.forEach((user) => {
          const userItem = document.createElement("li");
          userItem.className = "list-group-item d-flex justify-content-between align-items-center";
          userItem.textContent = user.username;
    
          // Bouton de blocage/déblocage
          const blockButton = document.createElement("button");
          blockButton.className = "btn btn-sm btn-danger";
          blockButton.textContent = "Bloquer";
          blockButton.addEventListener("click", () => toggleBlockUser(user.username));
    
          userItem.appendChild(blockButton);
          userList.appendChild(userItem);
      });
    
      updatePrivateRecipientList(users);
    }
    

    function updatePrivateRecipientList(users) {
      privateRecipient.innerHTML = '<option value="" disabled selected>Choisir un destinataire</option>';
      users.forEach((user) => {
        const option = document.createElement("option");
        option.value = user.username;
        option.textContent = user.username;
        privateRecipient.appendChild(option);
      });
    }

    function toggleBlockUser(username) {
      console.log(`🔒 Tentative de blocage/déblocage de ${username}...`);
      // Check si user est déjà bloqué
      const userButton = document.querySelector(`button[data-username="${username}"]`);
      const isBlocked = userButton && userButton.classList.contains("btn-secondary");

      // Définir l'action à envoyer au WebSocket
      const action = isBlocked ? "unblock_user" : "block_user";

      ws.send(JSON.stringify({
          action: action,
          username_to_block: username
      }));

      // MAJ le btn
      if (isBlocked) {
          userButton.textContent = "Bloquer";
          userButton.classList.remove("btn-secondary");
          userButton.classList.add("btn-danger");
      } else {
          userButton.textContent = "Débloquer";
          userButton.classList.remove("btn-danger");
          userButton.classList.add("btn-secondary");
      }
    }

    console.log("🚀 Tentative de connexion WebSocket...");
    connectWebSocket();
  
  };
  
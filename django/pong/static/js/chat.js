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
    let blockedUsers = new Set(); // Stocker users bloqués

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

    checkAuthentication();
  
    function connectWebSocket() {
      ws = new WebSocket(`ws://${window.location.host}/ws/chat/`);
  
      ws.onopen = () => {
        console.log("WebSocket connecté.");
        addSystemMessage("Vous êtes connecté au chat !");
        
      };
  
      ws.onmessage = (event) => {
        console.log("📩 Message reçu :", event.data);
        const data = JSON.parse(event.data);
        handleMessage(data); // Gérer le message reçu
      };
  
      ws.onerror = (error) => {
        console.error("Erreur WebSocket :", error);
        addSystemMessage("Erreur de connexion au WebSocket.");
      };
  
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
        updateUserList(data.users, data.blocked_users || []);
      }
    }
  
    // Add un message utilisateur
    function addMessageToChat(username, message) {
      console.log("🖊️ Ajout d'un message dans le chat :", username, message);
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message");
      messageDiv.innerHTML = `<span class="username">${username} :</span> ${message}`;
      messageList.appendChild(messageDiv);
      scrollToBottom();
    }
  
    // Add un message privé
    function addPrivateMessageToChat(username, message) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "private");
      messageDiv.innerHTML = `<span class="username">${username} (privé) :</span> ${message}`;
      messageList.appendChild(messageDiv);
      scrollToBottom();
    }
  
    // Add un message système
    function addSystemMessage(message) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "system");
      messageDiv.innerText = message;
      messageList.appendChild(messageDiv);
      scrollToBottom();
    }
  
    // Scroller automatiquement vers le bas
    function scrollToBottom() {
      messageArea.scrollTop = messageArea.scrollHeight;
    }
  
    // Envoi d'un message user
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
  
    // Bouton "Réduire"
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
    // Check chq user de la liste et crée un élément html pour le display
    function updateUserList(users) {
      console.log("👥 Mise à jour de la liste des utilisateurs :", users);
      //blockedUsers = new Set(blockedList.map(user => user.username)); // Mettre à jour la liste locale

      userList.innerHTML = ""; // On réinitialise la liste
  
      users.forEach((user) => {
          const userItem = document.createElement("li");
          userItem.className = "list-group-item d-flex justify-content-between align-items-center";
          userItem.textContent = user.username;
  
          // Vérifier si l'utilisateur est bloqué
          const isBlocked = blockedUsers.has(user.username);
  
          // Création du bouton de blocage/déblocage
          const blockButton = document.createElement("button");
          blockButton.className = isBlocked ? "btn btn-sm btn-secondary" : "btn btn-sm btn-danger";
          blockButton.textContent = isBlocked ? "Débloquer" : "Bloquer";
          blockButton.setAttribute("data-username", user.username); // Ajout de l'attribut pour le retrouver
          blockButton.addEventListener("click", () => toggleBlockUser(user.username));
  
          userItem.appendChild(blockButton);
          userList.appendChild(userItem);
      });
  
      updatePrivateRecipientList(users);
    }
    

    function updatePrivateRecipientList(users) {
      privateRecipient.innerHTML = '<option value="" disabled selected>Choisir un destinataire</option>';
      
      if (users.length === 0) {
          privateRecipient.setAttribute("disabled", "true");
          return;
      }
      privateRecipient.removeAttribute("disabled");
  
      users.forEach((user) => {
          const option = document.createElement("option");
          option.value = user.username;
          option.textContent = user.username;
          privateRecipient.appendChild(option);
      });
    }

    function toggleBlockUser(username) {
      console.log(`🔒 Tentative de blocage/déblocage de ${username}...`);
  
      // Trouver le bon bouton
      const userButton = document.querySelector(`button[data-username="${username}"]`);
      if (!userButton) return; // Si le bouton n'existe pas, on arrête
  
      // Déterminer l'action à envoyer au serveur
      const isBlocked = blockedUsers.has(username);
      const action = isBlocked ? "unblock_user" : "block_user";
  
      ws.send(JSON.stringify({
          action: action,
          username_to_unblock: isBlocked ? username : undefined,
          username_to_block: isBlocked ? undefined : username
      }));
  
      // Mettre à jour la liste des utilisateurs bloqués
      if (isBlocked) {
          blockedUsers.delete(username);
          userButton.textContent = "Bloquer";
          userButton.classList.remove("btn-secondary");
          userButton.classList.add("btn-danger");
      } else {
          blockedUsers.add(username);
          userButton.textContent = "Débloquer";
          userButton.classList.remove("btn-danger");
          userButton.classList.add("btn-secondary");
      }
    }

    console.log("🚀 Tentative de connexion WebSocket...");
    connectWebSocket();
  
  };
  
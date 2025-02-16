window.initChat = () => {

    if (window.chatInitialized) return; 
    window.chatInitialized = true;

    loadChatHistory();
    const chatWrapper = document.getElementById("chat-wrapper");
    if (chatWrapper) chatWrapper.style.display = "block"; // Display if connected

    // Init éléments HTML
    const messageList = document.getElementById("message-list");
    const messageInput = document.getElementById("message-input");
    const sendMessageBtn = document.getElementById("send-message-btn");
    const chatToggle = document.getElementById("chat-toggle");
    const chatFooter = document.querySelector("#chat-container .card-footer");
    const chatContainer = document.getElementById("chat-container");
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
      window.chatWebSocket = ws; // Stock to close later
  
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
        saveChatHistory();
      } else if (data.type === "private_message") {
        addPrivateMessageToChat(data.username, data.message);
        saveChatHistory();
      } else if (data.type === "error") {
        console.warn("Erreur reçue - Non affichée sur la page chat :", data.message);
      } else if ( data.type === "error_private") {
        addErrorMessage(data.message);
      } else if (data.type === "system") {
        addSystemMessage(data.message);
        saveChatHistory();
      } else if (data.type === "user_list") {
        updateUserList(data.users, data.blocked_users || []);
      }
    }
  
    // Add un message utilisateur
    function addMessageToChat(username, message) {
      console.log("🖊️ Ajout d'un message dans le chat :", username, message);
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message");

      const usernameLink = document.createElement("a");
      usernameLink.href = `/account/${username}`;
      usernameLink.textContent = username;
      usernameLink.classList.add("chat-username");
      usernameLink.style.cursor = "pointer";
      usernameLink.style.fontWeight = "bold";
      usernameLink.addEventListener("click", (event) => {
        event.preventDefault(); // Skip rechargement page
        navigateTo('/account/${username}');
      });

      messageDiv.appendChild(usernameLink);
      messageDiv.innerHTML += ` : ${message}`;
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

    // Error management
    function addErrorMessage(message) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "error-message"); // Classe spé. pour la mise en forme
        messageDiv.innerHTML = `⚠️ <strong>Erreur :</strong> ${message}`;        messageList.appendChild(messageDiv);
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
        messageInput.value = "";
      } else {
        addSystemMessage("WebSocket non connecté.");
      }
    });
  
    // Bouton "Réduire"
    chatToggle.addEventListener("click", function () {
        const isCollapsed = chatContainer.classList.contains("collapsed");

        if (isCollapsed) {
            // Réouvrir le chat
            chatContainer.classList.remove("collapsed");
            chatToggle.innerText = "Réduire";
        } else {
            // Réduire le chat
            chatContainer.classList.add("collapsed");
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

      userList.innerHTML = ""; // On réinitialise la liste
  
      users.forEach((user) => {
          const userItem = document.createElement("li");
          userItem.className = "list-group-item d-flex justify-content-between align-items-center";
  
           // Crée un lien cliquable vers le profil
          const usernameLink = document.createElement("a"); // lien vers le user profile
          usernameLink.href = `/account/${user.username}`;
          usernameLink.textContent = user.username;
          usernameLink.classList.add("chat-username");
          usernameLink.style.cursor = "pointer";
          usernameLink.style.fontWeight = "bold";
          usernameLink.addEventListener("click", (event) => {
            event.preventDefault(); // Empêche le rechargement de la page
            navigateTo(`/account/${user.username}`);
          });

          userItem.appendChild(usernameLink); // Insert element in the <ul>

          // Check si user est bloqué
          const isBlocked = blockedUsers.has(user.username);
  
          // Create bouton de blocage/déblocage
          const blockButton = document.createElement("button");
          blockButton.className = isBlocked ? "btn btn-sm btn-secondary" : "btn btn-sm btn-danger";
          blockButton.textContent = isBlocked ? "Débloquer" : "Bloquer";
          blockButton.classList.add("custom-padding");
          blockButton.setAttribute("data-username", user.username); // Ajout de l'attribut pour le retrouver
          blockButton.addEventListener("click", () => toggleBlockUser(user.username));
  
          userItem.appendChild(blockButton);
          userList.appendChild(userItem); // Exp.
      });
  
      updatePrivateRecipientList(users);
    }

    function navigateTo(url) {
      history.pushState(null, "", url); // Change l'URL sans recharger
      fetch(url)
        .then((response) => response.text())
        .then((html) => {
          document.body.innerHTML = html; // Remplace le contenu de la page
          window.initChat(); // Recharge le chat après le changement de page
        })
        .catch((error) => console.error("Erreur de navigation :", error));
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

    function saveChatHistory() {
      const messageList = document.getElementById("message-list");
      if (!messageList) return;
  
      const messages = [];
      messageList.childNodes.forEach(node => {
          messages.push(node.outerHTML);
      });
  
      localStorage.setItem("chatHistory", JSON.stringify(messages));
    }
  
    function loadChatHistory() {
      const messageList = document.getElementById("message-list");
      if (!messageList) return;
  
      const savedMessages = localStorage.getItem("chatHistory");
      if (savedMessages) {
          const messages = JSON.parse(savedMessages);
          messages.forEach(msg => {
              messageList.innerHTML += msg;
          });
      }
    }
  

    console.log("🚀 Tentative de connexion WebSocket...");
    connectWebSocket();
  
  };

  window.hideChat = () => {
    console.log("👋 Déconnexion détectée, fermeture du chat.");

    // Fermer proprement le WebSocket s'il est encore ouvert
    if (window.chatWebSocket) {
        window.chatWebSocket.close();
        window.chatWebSocket = null;
    }

    const chatWrapper = document.getElementById("chat-wrapper");
    if (chatWrapper) {
      chatWrapper.style.display = "none";
      chatWrapper.innerHTML = ""; // Effacer le contenu
    }

    localStorage.removeItem("chatHistory");

    // Réinitialiser la variable pour autoriser une future réouverture
    window.chatInitialized = false;
};

  
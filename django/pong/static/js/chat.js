
let myFriends = new Set(); // To stock friends
let unreadMessageCount = 0;
async function fetchMyFriends() {

  if (!window.currentUsername) return;

  try {
    // On appelle /account/monUsername/ en JSON, comme on l'a fait pour loadProfileInfo
    const res = await fetch(`/account/${window.currentUsername}`, {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json"
      },
      credentials: "include"
    });
    if (!res.ok) {
      console.warn("Impossible de récupérer la liste d'amis.");
      return;
    }
    const data = await res.json();

    if (data.friend_list) {
      // tableau d'objets
      myFriends = new Set(data.friend_list.map(friend => friend.username));
      console.log("Liste de mes amis :", myFriends);
    }
  } catch (err) {
    console.error("Erreur lors du fetch de mes amis :", err);
  }
}

window.initChat = async () => {

    if (window.chatInitialized) return;
    window.chatInitialized = true;
    console.log("Chargement du chat ...", document.getElementById("chat-wrapper"));

    loadChatHistory();

    await fetchMyFriends(); // Await > To wait until we get our resp. (friends list) from our server.

    const chatWrapper = document.getElementById("chat-wrapper");
    if (chatWrapper) chatWrapper.style.display = "block"; // Display if connected

    // Init éléments HTML
    const messageArea = document.getElementById("message-area");
    const messageList = document.getElementById("message-list");
    const messageInput = document.getElementById("message-input");
    const sendMessageBtn = document.getElementById("send-message-btn");
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault(); //Pas saut de ligne
          sendMessageBtn.click();
      }
    });
    const chatToggle = document.getElementById("chat-toggle");
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
      if (window.chatWebSocket && window.chatWebSocket.readyState === WebSocket.OPEN) {
        console.warn("🔄 WebSocket déjà connecté, on ne réouvre pas !");
        return;
      }
      ws = new WebSocket(`wss://${window.location.host}/ws/chat/`);
      window.chatWebSocket = ws; // Stock to close later

      ws.onopen = () => {
		console.log("WebSocket connecté.");
        if (!sessionStorage.getItem("chatConnectedMessageShown")) {
  		    addSystemMessage("Vous êtes connecté au chat !");
          sessionStorage.setItem("chatConnectedMessageShown", "true");
        }
		if (window.currentProfileUsername && window.currentProfileUsername === window.currentUsername) {
		  // S'assurer que loadProfileInfo est bien accessible (depuis account.js)
		  if (typeof window.loadProfileInfo === "function") {
			  console.log("[chat.js] Re-fetch du profil pour mettre à jour l'indicateur en ligne...");
			  window.loadProfileInfo(window.currentProfileUsername);
		  }
		}
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
        // sessionStorage.removeItem("chatConnectedMessageShown");
      };
    }

    // Étape 2 : Gestion des messages reçus
    function handleMessage(data) {
      if (data.type === "chat_message") {
        addMessageToChat(data.username, data.message);
      } else if (data.type === "private_message") {
          addPrivateMessageToChat(data.username, data.message, data.target_username);
      } else if (data.type === "error") {
        console.warn("Erreur reçue - Non affichée sur la page chat :", data.message);
      } else if ( data.type === "error_private") {
        addErrorMessage(data.message);
      } else if (data.type === "system") {
        addSystemMessage(data.message, data.invite_id);
      } else if (data.type === "user_list") {
        if (data.action === "removed") {
          myFriends.delete(data.username);
        } else if (data.action === "added") {
            myFriends.add(data.username)
        }
	if (data.users) {
            updateUserList(data.users, data.blocked_users || []);
	}
      } else if (data.type === "game_invitation") {
        showGameInvitation(data);
      } else if (data.type === "invitation_expired") {
        removeInvitation(data.invite_id);
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
        window.navigateTo(`/account/${username}`); // Appel spa global function (app.js)
      });

      messageDiv.appendChild(usernameLink);
      messageDiv.innerHTML += ` : ${message}`;
      messageList.appendChild(messageDiv);

      saveChatHistory();
      scrollToBottom();

      if (chatWrapper.classList.contains("collapsed")) {
        unreadMessageCount++;
        updateNotificationBadge();
      }
    }

    // Add un message privé
    function addPrivateMessageToChat(username, message, targetUsername) {
      if (message.length === 0)
        return;
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "private");
      messageDiv.innerHTML = `<span class="username">${username} (privé) :</span> ${message}`;
      messageList.appendChild(messageDiv);

      saveChatHistory();
      scrollToBottom();

      if (chatWrapper.classList.contains("collapsed")) {
        unreadMessageCount++;
        updateNotificationBadge();
      }
    }

    // Add un message système
    function addSystemMessage(message, inviteId) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "system");

      if (inviteId) {
        messageDiv.setAttribute("data-invite-id", inviteId); // Ajout du data attribute
      }

      if (message.toLowerCase().includes("tournoi")) {
        messageDiv.style.color = "red";
	    }
      messageDiv.innerHTML = message;
      messageList.appendChild(messageDiv);

      saveChatHistory();
      scrollToBottom();
    }

    // Error management
    function addErrorMessage(message) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "error-message"); // Classe spé. pour la mise en forme
        messageDiv.innerHTML = `⚠️ <strong>Erreur :</strong> ${message}`;
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
        const isCollapsed = chatWrapper.classList.contains("collapsed");

        if (isCollapsed) {
            // Réouvrir le chat
            chatWrapper.style.pointerEvents = "auto";
            chatWrapper.classList.remove("collapsed");
            chatToggle.innerText = "Réduire";

            unreadMessageCount = 0;
            updateNotificationBadge();
          } else {
            chatWrapper.style.pointerEvents = "none";
            chatWrapper.classList.add("collapsed");
            chatToggle.style.pointerEvents = "auto";
            updateNotificationBadge();
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

    const inviteToGameBtn = document.getElementById("invite-to-game-btn");
    inviteToGameBtn.addEventListener("click", () => {
      const recipient = privateRecipient.value; // le <select>

      if (!recipient) {
        addSystemMessage("Veuillez sélectionner un destinataire pour l'invitation.");
        return;
      }
      

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            action: "invite_to_game",
            target_username: recipient
          })
        );
      } else {
        addSystemMessage("WebSocket non connecté.");
      }
    });

    // Check chq user de la liste et crée un élément html pour le display
    function updateUserList(users, blocked) {
      console.log("👥 Mise à jour de la liste des utilisateurs :", users);
      if (!users) {
        users = [];
      }
      if (!blocked) {
        blocked = [];
      }

      const friendsList = document.getElementById("friends-connected");
      const userList = document.getElementById("others-connected");

      userList.innerHTML = ""; // On réinitialise la liste
      friendsList.innerHTML = "";

      users.forEach((user) => {

        if (user.username === window.currentUsername)
          return;

        const userItem = document.createElement("li"); // List element : représente each user connecté
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
          window.navigateTo(`/account/${user.username}`);
        });

        userItem.appendChild(usernameLink); // Insert element in the <ul>

        // Check si user est bloqué
        const isBlocked = blockedUsers.has(user.username);

        // Create bouton de blocage/déblocage
        const blockButton = document.createElement("button");
        blockButton.className = isBlocked ? "btn btn-sm btn-secondary" : "btn btn-sm btn-danger";
        blockButton.textContent = isBlocked ? "Débloquer" : "Bloquer";
        blockButton.style.maxWidth = "180px";
        // blockButton.classList.add("custom-padding", "w-100"); // w-100 : take all the width
        blockButton.setAttribute("data-username", user.username); // Ajout de l'attribut pour le retrouver
        blockButton.addEventListener("click", () => toggleBlockUser(user.username));

        userItem.appendChild(blockButton);

        if (myFriends.has(user.username))
          friendsList.appendChild(userItem);
        else
          userList.appendChild(userItem); // Exp.
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
      console.log("users.username: ", users.username);
      console.log("window.currentUsername: ", window.currentUsername);

      users.forEach((user) => {
        if (user.username === window.currentUsername)
          return;
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

    function showGameInvitation(inviteData) {

        const now = Date.now() / 1000;
        if (inviteData.expires_at < now) {
          console.warn(`Invitation de ${inviteData.from} expirée, non affichée.`);
          return;
        }

      const invitationDiv = document.createElement("div");
      invitationDiv.classList.add("message", "system");// Style system message
      invitationDiv.id = "invite_" + inviteData.invite_id;

      const textNode = document.createTextNode(`${inviteData.from} vous invite à jouer à Pong ! `);
      invitationDiv.appendChild(textNode);

      const link = document.createElement("a");
      link.href = `/game?game_id=${inviteData.game_id}&mode=private&invite_id=${inviteData.invite_id}&role=player2`;
      link.innerText = "Vers le jeu Pong";
      link.target = "_blank";
      link.classList.add("spa-link");

      invitationDiv.appendChild(document.createElement("br")); //Saut de ligne
      invitationDiv.appendChild(link);

      const messageList = document.getElementById("message-list");
      if (messageList)
        messageList.appendChild(invitationDiv);

      if (chatWrapper.classList.contains("collapsed")) {
        unreadMessageCount++;
        updateNotificationBadge();
      }

    }

    function removeInvitation(inviteId) {
      const invitation = document.getElementById("invite_" + inviteId);
      if (invitation) {
        invitation.remove();
      }

      const senderMessage = document.querySelector(`[data-invite-id="${inviteId}"]`);
      if (senderMessage) {
        senderMessage.remove();
      }
    }

    function updateNotificationBadge() {
      const chatToggle = document.getElementById("chat-toggle");

      if (unreadMessageCount > 0) {
        chatToggle.innerHTML = `Ouvrir <span class="badge bg-danger">${unreadMessageCount}</span>`;
      } else {
        chatToggle.innerHTML = "Ouvrir";
      }
    }

    console.log("🚀 Tentative de connexion WebSocket...");
    connectWebSocket();

  };

  window.hideChat = () => {

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

    if (!window.chatInitialized) { // Check also if user has been deconnected
      localStorage.removeItem("chatHistory");
      sessionStorage.removeItem("chatConnectedMessageShown");
    }

    // Réinitialiser la variable pour autoriser une future réouverture
    window.chatInitialized = false;
};


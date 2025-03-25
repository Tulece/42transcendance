
let myFriends = new Set();
let unreadMessageCount = 0;
async function fetchMyFriends() {

  if (!window.currentUsername) return;

  try {
    const res = await fetch(`/account/${window.currentUsername}`, {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
      },
      credentials: "include"
    });
    if (!res.ok) {
      console.warn("Impossible de récupérer la liste d'amis.");
      return;
    }
    const data = await res.json();

    if (data.friend_list) {
      // tab d'objets
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

    loadChatHistory();

    await fetchMyFriends();

    const chatWrapper = document.getElementById("chat-wrapper");
    if (chatWrapper) chatWrapper.style.display = "block";

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
    let blockedUsers = new Set();

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
        return;
      }
      ws = new WebSocket(`wss://${window.location.host}/ws/chat/`);
      window.chatWebSocket = ws;

      ws.onopen = () => {
		console.log("WebSocket connecté.");
        if (!sessionStorage.getItem("chatConnectedMessageShown")) {
  		    addSystemMessage("Vous êtes connecté au chat !");
          sessionStorage.setItem("chatConnectedMessageShown", "true");
        }
		if (window.currentProfileUsername && window.currentProfileUsername === window.currentUsername) {
		  if (typeof window.loadProfileInfo === "function") {
			  window.loadProfileInfo(window.currentProfileUsername);
		  }
		}
	  };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
      };

      ws.onerror = (error) => {
        console.error("Erreur WebSocket :", error);
        addSystemMessage("Erreur de connexion au WebSocket.");
      };

      ws.onclose = () => {
        addSystemMessage("Connexion au chat perdue.");
      };
    }

    //Gestion des messages reçus
    function handleMessage(data) {
      if (data.type === "chat_message") {
        addMessageToChat(data.username, data.message);
      } else if (data.type === "private_message") {
          if (data.message && data.message.length > 0) {
            addPrivateMessageToChat(data.username, data.message);
          }
      } else if (data.type === "error") {
        console.warn("Erreur reçue - Non affichée sur la page chat :", data.message);
      } else if ( data.type === "error_private") {
        addErrorMessage(data.message);
      } else if (data.type === "system") {
        addSystemMessage(data.message, data.invite_id);
      } else if (data.type === "user_list") {
        if (data.action === "removed") {
          myFriends.delete(data.username);
        }
        if (data.action === "added") {
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

    function addMessageToChat(username, message) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message");

      const usernameLink = document.createElement("a");
      usernameLink.href = `/account/${username}`;
      usernameLink.textContent = username;
      usernameLink.classList.add("chat-username");
      usernameLink.style.cursor = "pointer";
      usernameLink.style.fontWeight = "bold";
      usernameLink.addEventListener("click", (event) => {
        event.preventDefault(); // Skip reload page
        window.navigateTo(`/account/${username}`);
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

    function addPrivateMessageToChat(username, message) {
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

    function addSystemMessage(message, inviteId) {
      const messageDiv = document.createElement("div");
      messageDiv.classList.add("message", "system");

      if (inviteId) {
        messageDiv.setAttribute("data-invite-id", inviteId);
      }

      if (message.toLowerCase().includes("tournoi")) {
        messageDiv.style.color = "red";
	    }
      messageDiv.innerHTML = message;
      messageList.appendChild(messageDiv);

      saveChatHistory();
      scrollToBottom();
    }

    function addErrorMessage(message) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "error-message");
        messageDiv.innerHTML = `⚠️ <strong>Erreur :</strong> ${message}`;
        messageList.appendChild(messageDiv);
        scrollToBottom();
    }


    function scrollToBottom() {
      messageArea.scrollTop = messageArea.scrollHeight;
    }

    sendMessageBtn.addEventListener("click", () => {
      const message = messageInput.value;
      if (!message) return;


      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message }));
        messageInput.value = "";
      } else {
        addSystemMessage("WebSocket non connecté.");
      }
    });

    chatToggle.addEventListener("click", function () {
        const isCollapsed = chatWrapper.classList.contains("collapsed");

        if (isCollapsed) {
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
      const recipient = privateRecipient.value;

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

    function updateUserList(users, blocked) {
      if (!users) {
        users = [];
      }
      if (!blocked) {
        blocked = [];
      }

      const friendsList = document.getElementById("friends-connected");
      const userList = document.getElementById("others-connected");

      userList.innerHTML = "";
      friendsList.innerHTML = "";

      users.forEach((user) => {

        if (user.username === window.currentUsername)
          return;

        const userItem = document.createElement("li");
        userItem.className = "list-group-item d-flex justify-content-between align-items-center";

        const usernameLink = document.createElement("a");
        usernameLink.href = `/account/${user.username}`;
        usernameLink.textContent = user.username;
        usernameLink.classList.add("chat-username");
        usernameLink.style.cursor = "pointer";
        usernameLink.style.fontWeight = "bold";
        usernameLink.addEventListener("click", (event) => {
          event.preventDefault(); // Empêche le rechargement de la page
          window.navigateTo(`/account/${user.username}`);
        });

        userItem.appendChild(usernameLink);

        const isBlocked = blockedUsers.has(user.username);

        const blockButton = document.createElement("button");
        blockButton.className = isBlocked ? "btn btn-sm btn-secondary" : "btn btn-sm btn-danger";
        blockButton.textContent = isBlocked ? "Débloquer" : "Bloquer";
        blockButton.style.maxWidth = "180px";
        blockButton.setAttribute("data-username", user.username);
        blockButton.addEventListener("click", () => toggleBlockUser(user.username));

        userItem.appendChild(blockButton);

        if (myFriends.has(user.username))
          friendsList.appendChild(userItem);
        else
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
        if (user.username === window.currentUsername)
          return;
        const option = document.createElement("option");
        option.value = user.username;
        option.textContent = user.username;
        privateRecipient.appendChild(option);
      });
    }

    function toggleBlockUser(username) {

      const userButton = document.querySelector(`button[data-username="${username}"]`);
      if (!userButton) return;

      const isBlocked = blockedUsers.has(username);
      const action = isBlocked ? "unblock_user" : "block_user";

      ws.send(JSON.stringify({
          action: action,
          username_to_unblock: isBlocked ? username : undefined,
          username_to_block: isBlocked ? undefined : username
      }));

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
      invitationDiv.classList.add("message", "system");
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

    connectWebSocket();

  };

  window.hideChat = () => {

    if (window.chatWebSocket) {
        window.chatWebSocket.close();
        window.chatWebSocket = null;
    }

    const chatWrapper = document.getElementById("chat-wrapper");
    if (chatWrapper) {
      chatWrapper.style.display = "none";
      chatWrapper.innerHTML = "";
    }

    if (!window.chatInitialized) {
      localStorage.removeItem("chatHistory");
      sessionStorage.removeItem("chatConnectedMessageShown");
    }
    window.chatInitialized = false;
};


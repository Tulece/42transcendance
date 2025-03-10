window.initFriendshipActions = initFriendshipActions; 

function loadReceivedFriendRequests() {

    fetch(`/api/friends/received/`, {
        method: "GET",
        credentials: "include",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json"
        }
    })
    .then(response => response.json())
    .then(data => {
        const listContainer = document.getElementById("friend-requests-list");
        if (!listContainer) return;
        listContainer.innerHTML = "";
        data.forEach(request => {
            const item = document.createElement("div");
            item.className = "friend-request-item";
            item.dataset.requestId = request.id;
            item.innerHTML = `<span>${request.sender_username}</span>
                              <button class="accept-request btn btn-success btn-sm">Accepter</button>
                              <button class="decline-request btn btn-danger btn-sm">Refuser</button>`;
            listContainer.appendChild(item);
        });
        attachRequestEventListeners();
    })
    .catch(error => console.error("Erreur lors du chargement des demandes reçues :", error));
}

function initFriendshipActions() {

    const pathParts = window.location.pathname.split("/").filter(part => part !== "");

    window.currentProfileUsername;
    let profileUsername = null;

    if (pathParts.length === 1 && pathParts[0] === "account") {
        profileUsername = window.currentUsername;
    } else if (pathParts.length >= 2 && pathParts[0] === "account") {
        profileUsername = pathParts[1];
    }
    
    console.log("CurrentUser: ", window.currentUsername);

    console.log("ProfileUsername: ", profileUsername);
    console.log("PathParts[0]: ", pathParts[0]);
    if (pathParts[1])
        console.log("PathParts[1]: ", pathParts[1]);
    
    if (!profileUsername)
        return;

    window.currentProfileUsername = profileUsername;

    loadProfileInfo(window.currentProfileUsername);
    
    const currentUser = window.currentUsername || null;
    
    if (currentUser && profileUsername === currentUser) {
        console.log("PASSED INIT TO LOAD !!");
        loadReceivedFriendRequests();
        return;
    }
    
    // Else, c'est le profil d'un autre user
    const sendBtn = document.getElementById("send-friend-request");
    const cancelBtn = document.getElementById("cancel-friend-request");
    let currentRequestId = null;
    
    function fetchFriendshipStatus() {
        fetch(`/api/friends/status/${profileUsername}/`, {
            method: "GET",
            credentials: "include",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",

            }
        })
        .then(response => response.json())
        .then(data => {
            console.log("Friendship status data:", data);
            if (sendBtn) sendBtn.style.display = "none";
            if (cancelBtn) cancelBtn.style.display = "none";
            
            if (data.is_friend) {
                console.log("Déjà amis");
            } else if (data.request_sent) {
                currentRequestId = data.friend_request_id;
                if (cancelBtn) cancelBtn.style.display = "inline-block";
            } else if (data.request_received) {
                console.log("Une demande vous a été envoyée sur ce profil");
            } else {
                if (sendBtn) sendBtn.style.display = "inline-block";
            }
        })
        .catch(error => console.error("Erreur lors de la récupération du statut d'amitié :", error));
    }
    
    if (sendBtn) {
        sendBtn.addEventListener("click", function () {
            fetch(`/api/friends/send/${profileUsername}/`, {
                method: "POST",
                credentials: "include",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken()  // Ajout du CSRF token ici
                }
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                fetchFriendshipStatus();
            })
            .catch(error => console.error("Erreur lors de l'envoi de la demande :", error));
        });
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            if (!currentRequestId) return;
            fetch(`/api/friends/cancel/${currentRequestId}/`, {
                method: "POST",
                credentials: "include",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken() 
                }
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                fetchFriendshipStatus();
            })
            .catch(error => console.error("Erreur lors de l'annulation de la demande :", error));
        });
    }
    fetchFriendshipStatus();
}
    

function attachRequestEventListeners() {
    const requestItems = document.querySelectorAll(".friend-request-item");
    requestItems.forEach(item => {
        const requestId = item.dataset.requestId;
        const acceptBtn = item.querySelector(".accept-request");
        const declineBtn = item.querySelector(".decline-request");
        
        if (acceptBtn) {
            acceptBtn.addEventListener("click", function () {
                fetch(`/api/friends/accept/${requestId}/`, {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken() 
                    }
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    loadReceivedFriendRequests();
                    loadProfileInfo(window.currentProfileUsername);
                })
                .catch(error => console.error("Erreur lors de l'acceptation de la demande :", error));
            });
        }
        if (declineBtn) {
            declineBtn.addEventListener("click", function () {
                fetch(`/api/friends/decline/${requestId}/`, {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken() 
                    }
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    loadReceivedFriendRequests();
                    loadProfileInfo(window.currentProfileUsername);
                })
                .catch(error => console.error("Erreur lors du refus de la demande :", error));
            });
        }

    });
}

function loadProfileInfo(profileUsername) {
    fetch(`/account/${profileUsername}/`, {
        method: "GET",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
        },
        credentials: "include"
    })
    .then(res => res.json())
    .then(data => {
        console.log("🔄 Rechargement du profil avec :", data);
        const status = document.getElementById("online-status");
        if (status) {
            status.style.display = "inline-block";
            if (data.online_status) {
                status.style.backgroundColor = "green";
                status.title = "Utilisateur en ligne"; // Tooltip when on button
            } else {
                status.style.backgroundColor = "red";
                status.title = "Utilisateur hors-ligne";
            }
        }

        const friendList = document.getElementById("friend-list");
        if (friendList) {
            if (data.friend_list && data.friend_list.length > 0) {
                friendList.innerHTML = "";

                data.friend_list.forEach(friend => {
                    const li = document.createElement("li"); // Element in list (li)
                    li.classList.add("list-group-item");

                    const avatar = document.createElement("img");
                    avatar.src = friend.avatar_url;
                    avatar.classList.add("rounded-circle", "me-2");
                    avatar.style.height = "30px";
                    avatar.style.width = "30px";

                    const circle = document.createElement("span");
                    circle.style.display = "inline-block";
                    circle.style.width = "10px";
                    circle.style.height = "10px";
                    circle.style.borderRadius = "50%";
                    circle.style.marginRight = "8px";
                    circle.style.marginLeft = "2px";
                    circle.style.backgroundColor = friend.online_status ? "green" : "red";

                    const friendLink = document.createElement("a");
                    friendLink.textContent = friend.username;
                    friendLink.href = `/account/${friend.username}`;
                    friendLink.addEventListener("click", (e) => {
                        e.preventDefault(); // To block a reload
                        window.navigateTo(friendLink.href);
                    });

                    const friendInfoDiv = document.createElement("div");
                    friendInfoDiv.appendChild(avatar);
                    friendInfoDiv.appendChild(friendLink);
                    friendInfoDiv.appendChild(circle);

                    if (profileUsername === window.currentUsername) {
                        console.log("BUTTON PASSED");
                        const deleteBtn = document.createElement("button");
                        deleteBtn.classList.add("btn", "btn-danger", "btn-sm", "delete-friend-btn");
                        deleteBtn.textContent = "❌";
                        deleteBtn.dataset.username = friend.username; // TO CHECK
                        friendInfoDiv.appendChild(deleteBtn);
                    }    

                    li.appendChild(friendInfoDiv);
                    friendList.appendChild(li);
                });
                if (profileUsername === window.currentUsername)
                    attachDeleteFriendEventListeners();
            }
            else {
                friendList.innerHTML = "<p class='text-muted'>Vous n'avez pas encore d'amis.</p>";
            }
        }
    })
    .catch(err => {
        console.error("Erreur loadProfileInfo:", err);
    });
}


function attachDeleteFriendEventListeners() {
    const deleteButtons = document.querySelectorAll(".delete-friend-btn"); // In order to get all the delete btns (from each friend user)

    deleteButtons.forEach(button => {
        button.addEventListener("click", function () {
            const usernameToRemove = this.dataset.username;
            console.log("UsernameToRemove: ", usernameToRemove);

            if (confirm(`Voulez-vous vraiment supprimer ${usernameToRemove} de votre liste d'amis ?`)) {
                fetch(`/api/friends/delete/${usernameToRemove}/`, {
                    method: "DELETE",
                    credentials: "include",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken()
                    }
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    console.log("🔄 Rafraîchissement de la liste des amis après suppression...");
                    loadProfileInfo(window.currentProfileUsername); // Pour refresh la liste
                    console.log("✅ Rafraîchissement effectué !");
                })
                .catch(error => console.error("Erreur lors de la suppression de l'ami :", error));
            }
        });
    });
}



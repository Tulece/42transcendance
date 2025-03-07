// document.addEventListener("DOMContentLoaded", function () {
//     window.initFriendshipActions = initFriendshipActions;
//     // // Appeler fetchFriendshipStatus dès le chargement de la page pour un profil d'autre utilisateur
//     // ??!! Pas au chargement de la page car le site est en SPA et le DOM n'est pas rechargé
//     // ===> 
//     // fetchFriendshipStatus();

// });

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

function loadPlayerMatches(profileUsername) {
    fetch(`/api/matches/${profileUsername}/`, {
        method: "GET",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
        },
        credentials: "include"
    })
    .then(res => res.json())
    .then(data => {
        console.log("Matches info:", data);
        const matchesContainer = document.getElementById("matches-list");
        if (!matchesContainer) return;
    
        matchesContainer.innerHTML = "";
    
        if (data.stats && data.stats.length > 0) {
            const stats = data.stats[0];
            const statsItem = document.createElement("div");
            statsItem.className = "card shadow-sm p-3 mb-4";
            statsItem.innerHTML = `<h4 class=\"text-center\">Statistiques du joueur</h4>
                                   <p><strong>Total de matchs joués :</strong> ${stats.total_matches}</p>
                                   <p><strong>Total de victoires :</strong> ${stats.total_wins}</p>`;
            matchesContainer.appendChild(statsItem);
        }
    
        if (data.matches && data.matches.length > 0) {
            const table = document.createElement("table");
            table.className = "table table-striped table-bordered table-hover shadow-sm";
    
            const thead = document.createElement("thead");
            thead.className = "table-dark";
            const headerRow = document.createElement("tr");
            const headers = ["Match ID", "Joueur 1", "Joueur 2", "Gagnant", "Créé le"];
            headers.forEach(headerText => {
                const header = document.createElement("th");
                header.scope = "col";
                header.innerText = headerText;
                headerRow.appendChild(header);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);
    
            const tbody = document.createElement("tbody");
    
            data.matches.forEach(match => {
                const row = document.createElement("tr");
    
                const cells = [
                    match.id,
                    match.player1_username,
                    match.player2_username || 'N/A',
                    match.winner || 'N/A',
                    new Date(match.created_at).toLocaleString()
                ];
    
                cells.forEach(cellText => {
                    const cell = document.createElement("td");
                    cell.innerText = cellText;
                    row.appendChild(cell);
                });
    
                tbody.appendChild(row);
            });
    
            table.appendChild(tbody);
            matchesContainer.appendChild(table);
        } else {
            const noMatches = document.createElement("p");
            noMatches.className = "text-muted text-center";
            noMatches.innerText = "Aucun match trouvé.";
            matchesContainer.appendChild(noMatches);
        }
    })
    .catch(err => {
        console.error("Erreur loadPlayerMatches:", err);
    });
}

function initFriendshipActions() {

    const pathParts = window.location.pathname.split("/").filter(part => part !== "");

    let profileUsername = null;

    if (pathParts.length === 1 && pathParts[0] === "account") {
        profileUsername = window.currentUsername;
    } else if (pathParts.length >= 2 && pathParts[0] === "account") {
        profileUsername = pathParts[1];
    }
    
    console.log("CurrentUser: ", window.currentUsername);

    console.log("ProfileUsername: ", profileUsername);
    
    if (!profileUsername)
        return;

    loadProfileInfo(profileUsername);
    loadPlayerMatches(profileUsername); 
    
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
        console.log("Profil info:", data);
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
        if (friendList && data.friend_list && data.friend_list.length > 0) {
            friendList.innerHTML = "";

            data.friend_list.forEach(friend => {
                const li = document.createElement("li"); // Element in list (li)
                li.classList.add("list-group-item");

                const circle = document.createElement("span");
                circle.style.display = "inline-block";
                circle.style.width = "10px";
                circle.style.height = "10px";
                circle.style.borderRadius = "50%";
                circle.style.marginRight = "8px";
                circle.style.backgroundColor = friend.online_status ? "green" : "red";

                const friendLink = document.createElement("a");
                friendLink.textContent = friend.username;
                friendLink.href = `/account/${friend.username}`;
                friendLink.addEventListener("click", (e) => {
                    e.preventDefault();
                    window.navigateTo(friendLink.href);
                });

                li.appendChild(circle);
                li.appendChild(friendLink);
                friendList.appendChild(li);
            });
        }
    })
    .catch(err => {
        console.error("Erreur loadProfileInfo:", err);
    });
}

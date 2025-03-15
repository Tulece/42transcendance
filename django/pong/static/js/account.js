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
                                   <p><strong>Nombre de victoires :</strong> ${stats.total_wins}</p>
                                   <p><strong>Nombre de défaites :</strong> ${stats.total_loses}</p>`;
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


function toggleA2F() {
    const checkbox = document.getElementById('a2f');
    const statusText = document.getElementById('a2f-status');

    if (checkbox.checked) {
        statusText.textContent = 'Activé';
    } else {
        statusText.textContent = 'Désactivé';
    }
}
window.toggleA2F = toggleA2F;

function saveChanges() {
    const isA2FEnabled = document.getElementById('a2f').checked;

    fetch('/api/account/update_a2f/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')  // Assure-toi d'avoir un token CSRF valide
        },
        body: JSON.stringify({
            is_a2f_enabled: isA2FEnabled
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Paramètres mis à jour avec succès !');
        } else {
            alert('Erreur lors de la mise à jour des paramètres.');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur lors de la mise à jour des paramètres.');
    });
}
window.saveChanges = saveChanges;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
window.getCookie = getCookie;

// Fonction pour uploader l'avatar
function uploadAvatar(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('avatar', file);
    fetch('/update-avatar/', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(response => response.ok ? response.json() : Promise.reject('Upload failed'))
    .then(data => {
        if (data.success) {
			// 1) Mettre à jour la balise <img> pour pointer vers le nouvel avatar
			const profileAvatar = document.getElementById('profile-avatar');
			if (profileAvatar) {
				profileAvatar.src = data.avatar_url + '?' + new Date().getTime();
				// Le petit '?timestamp' aide à forcer le rafraîchissement si cache agressif
			}
			alert("Avatar mis à jour !");
		} else {
            alert('Failed to update avatar: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred during upload');
    });
}
window.uploadAvatar = uploadAvatar;

// Ouvre la modal pour modifier le nom d'utilisateur
function openUsernameModal() {
    const usernameModal = new bootstrap.Modal(document.getElementById('usernameModal'));
    document.getElementById('username-form').reset();
    document.getElementById('username-error').style.display = 'none';
    const viewedUsername = document.querySelector('[data-viewed-username]');
    if (viewedUsername) {
        document.getElementById('new-username').value = viewedUsername.getAttribute('data-viewed-username');
    }
    usernameModal.show();
}
window.openUsernameModal = openUsernameModal;

// Valide et soumet le changement de nom d'utilisateur
function changeUsername() {
    const newUsername = document.getElementById('new-username').value.trim();
    if (!newUsername) {
        document.getElementById('username-error').textContent = 'Le nom d\'utilisateur ne peut pas être vide.';
        document.getElementById('username-error').style.display = 'block';
        return;
    }
    document.getElementById('username-error').style.display = 'none';
    fetch('/change-username/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ new_username: newUsername })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
			// Mettre à jour l'affichage du nom d'utilisateur dans la page
			// ex: on a <span data-viewed-username="...">
			const viewedUsernameEl = document.querySelector('[data-viewed-username]');
			if (viewedUsernameEl) {
				viewedUsernameEl.textContent = data.username; // nouveau username
				viewedUsernameEl.setAttribute('data-viewed-username', data.username);
			}
			alert('Nom d’utilisateur mis à jour !');
			// Fermer la modal
			const usernameModalEl = document.getElementById('usernameModal');
			if (usernameModalEl) {
				bootstrap.Modal.getInstance(usernameModalEl).hide();
			}
		} else {
            document.getElementById('username-error').textContent = data.error || 'Échec du changement de nom d\'utilisateur.';
            document.getElementById('username-error').style.display = 'block';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Une erreur est survenue lors du changement de nom d\'utilisateur.');
    });
}
window.changeUsername = changeUsername;

// Ouvre la modal de changement de mot de passe
function openPasswordModal() {
    const passwordModal = new bootstrap.Modal(document.getElementById('passwordModal'));
    document.getElementById('password-form').reset();
    document.getElementById('password-mismatch').style.display = 'none';
    passwordModal.show();
}
window.openPasswordModal = openPasswordModal;

// Valide et soumet le changement de mot de passe
function changePassword() {
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    if (!currentPassword || !newPassword || !confirmPassword) {
        alert('Veuillez remplir tous les champs.');
        return;
    }
    if (newPassword !== confirmPassword) {
        document.getElementById('password-mismatch').style.display = 'block';
        return;
    }
    document.getElementById('password-mismatch').style.display = 'none';
    const formData = new FormData();
    formData.append('current_password', currentPassword);
    formData.append('new_password', newPassword);
    fetch('/change-password/', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Mot de passe changé avec succès!');
            bootstrap.Modal.getInstance(document.getElementById('passwordModal')).hide();
        } else {
            alert(data.error || 'Échec du changement de mot de passe.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Une erreur est survenue lors du changement de mot de passe.');
    });
}
window.changePassword = changePassword;

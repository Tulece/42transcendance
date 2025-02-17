function toggleA2F() {
    const checkbox = document.getElementById('a2f');
    const statusText = document.getElementById('a2f-status');

    if (checkbox.checked) {
        statusText.textContent = 'Activé';
    } else {
        statusText.textContent = 'Désactivé';
    }
}

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

document.addEventListener("DOMContentLoaded", async function () {
    const username = window.location.pathname.split("/").pop(); // Take le pseudo de l'URL

    try {
        const response = await fetch(`/api/user_profile/${username}/`, {
            method: "GET",
            credentials: "include",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        if (response.ok) {
            const data = await response.json(); // Récup' via l'API le statut de co + is_friend.
            const statusIndicator = document.getElementById("online-status");

            if (data.is_friend) {
                statusIndicator.style.display = "inline-block";
                statusIndicator.style.width = "10px";
                statusIndicator.style.height = "10px";
                statusIndicator.style.borderRadius = "50%";
                statusIndicator.style.marginLeft = "5px";
                statusIndicator.style.backgroundColor = data.online_status ? "green" : "red";
            }
        }
    } catch (error) {
        console.error("Erreur lors de la récupération du statut :", error);
    }
});


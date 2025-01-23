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

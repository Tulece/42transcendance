document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour gérer l'A2F
    function toggleA2F() {
        const checkbox = document.getElementById('a2f');
        const statusText = document.getElementById('a2f-status');
        
        if (checkbox) {
            if (checkbox.checked) {
                statusText.textContent = 'Activé';
            } else {
                statusText.textContent = 'Désactivé';
            }
        }
    }

    // Fonction pour sauvegarder les changements
    function saveChanges() {
        const isA2FEnabled = document.getElementById('a2f').checked;
        
        fetch('/api/account/update_a2f/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.getCSRFToken()
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
                alert(data.error || 'Erreur lors de la mise à jour des paramètres.');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour des paramètres.');
        });
    }

    // Écouter les événements
    const a2fCheckbox = document.getElementById('a2f');
    if (a2fCheckbox) {
        a2fCheckbox.addEventListener('change', toggleA2F);
    }

    const saveButton = document.getElementById('save-btn');
    if (saveButton) {
        saveButton.addEventListener('click', saveChanges);
    }
});
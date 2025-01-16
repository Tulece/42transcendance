// register.js
(function() {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
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

    const form = document.getElementById("register-form");
    if (!form) return;

    form.addEventListener("submit", async function(event) {
        event.preventDefault();

        const emailInput = document.getElementById("email");
        if (!emailInput.value) {
            alert("Veuillez entrer un email.");
            return;
        }

        const formData = new FormData(form);

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCookie("csrftoken")  // Ajout du token CSRF
                },
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    navigateTo(result.redirect);
                } else {
                    displayError(result.error || "Une erreur est survenue.");
                }
            } else {
                let result = {};
                try {
                    const text = await response.text();
                    console.log("Response text:", text);
                    result = JSON.parse(text);
                } catch(e) {
                    console.error("Erreur lors du parsing de la réponse :", e);
                    result.error = "Une erreur est survenue lors de la soumission.";
                }
                displayError(result.error || "Une erreur est survenue.");
            }
        } catch (error) {
            console.error("Erreur lors de la soumission du formulaire:", error);
            displayError("Une erreur réseau est survenue.");
        }
    });

    function displayError(message) {
        alert(message);
    }
})();

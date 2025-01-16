(function () {
    const form = document.getElementById("login-form");
    if (!form) return;

    form.addEventListener("submit", async function (event) {
        event.preventDefault(); // Pas de form HTML classique

        const formData = new FormData(form);
        const username = formData.get("username");
        const password = formData.get("password");
        const nextUrl = formData.get("next") || "/";

        try {
            const response = await fetch("/login/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken()
                },
                body: JSON.stringify({ username, password, next: nextUrl })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    alert("Connexion réussie !");
                    await updateUserInfo();
                    window.location.href = data.redirect || "/";
                } else {
                    alert(data.error || "Erreur inconnue");
                }
            } else {
                let errorMessage = "Erreur de connexion.";
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    console.error("Réponse non JSON :", e);
                }
                alert(errorMessage);
            }
        } catch (error) {
            console.error("Erreur réseau :", error);
            alert("Erreur réseau. Impossible de se connecter.");
        }
    });
})();
// login.js
(function () {
    const form = document.getElementById("login-form");
    if (!form) return;

    let waitingForOTP = false;
    const otpContainer = document.getElementById("otp-container");
    const loginError = document.getElementById("login-error");

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(form);
        const username = formData.get("username");
        const password = formData.get("password");
        const otpCode = formData.get("otp_code");
        const nextUrl = formData.get("next") || "/";

        try {
            const response = await fetch("/login/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken()
                },
                body: JSON.stringify({
                    username,
                    password,
                    otp_code: otpCode,
                    next: nextUrl
                })
            });

            const data = await response.json();

            if (response.ok) {
                if (data.requires_otp) {
                    waitingForOTP = true;
                    otpContainer.style.display = "block";
                    loginError.textContent = data.message;
                    loginError.style.color = "green";
                    loginError.style.display = "block";
                } else if (data.success) {
                    alert("Connexion réussie !");
                    await updateUserInfo();
                    window.location.href = data.redirect || "/";
                }
            } else {
                loginError.textContent = data.error || "Erreur inconnue";
                loginError.style.color = "red";
                loginError.style.display = "block";
                if (data.error.includes("Code de vérification")) {
                    document.getElementById("otp_code").value = "";
                }
            }
        } catch (error) {
            console.error("Erreur réseau :", error);
            loginError.textContent = "Erreur réseau. Impossible de se connecter.";
            loginError.style.color = "red";
            loginError.style.display = "block";
        }
    });
})();

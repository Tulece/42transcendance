// app.js
(function(){
    let currentPage = null;
    let initialHomeHtml = "";  // Va contenir le HTML initial de la home

    document.addEventListener("click", function(event) {
        const link = event.target.closest(".spa-link");
        if (!link) return;

        event.preventDefault();
        const url = link.getAttribute("href");
        navigateTo(url);
    });

    window.addEventListener("popstate", function() {
        navigateTo(location.pathname, false);
    });

    async function navigateTo(url, pushState = true) {
        console.log("[navigateTo]", url);

        // Vérifie si l'URL cible est déjà la page actuelle pour éviter les doublons
        if (pushState && location.pathname === url) {
            console.log("[navigateTo] Déjà sur l'URL:", url);
            return;
        }

        destroyCurrentPage();

        if (pushState) {
            // Évite de créer un nouvel état si on est déjà sur /register
            if (url.startsWith("/register") && location.pathname.startsWith("/register")) {
                console.log("[navigateTo] Déjà sur la page d'inscription, pas de nouvel historique.");
            } else {
                history.pushState(null, "", url);
            }
        }

        const appDiv = document.getElementById("app");
        try {
            const resp = await fetch(url, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (resp.ok) {
                const htmlSnippet = await resp.text();
                appDiv.innerHTML = htmlSnippet;

                // Initialisation spécifique selon l'URL
                if (url.includes("/game")) {
                    currentPage = "game";
                    const script = document.createElement("script");
                    script.src = "/static/js/pong.js";
                    script.onload = () => {
                        if (window.initPong) {
                            window.initPong();
                        } else {
                            console.error("initPong n'est pas défini après le chargement de pong.js.");
                        }
                    };
                    document.body.appendChild(script);
                } else if (url === "/") {
                    currentPage = "home";
                    loadScriptOnce("/static/js/home.js");
                    if (window.initHome) { window.initHome(); }
                } else if (url.includes("/chat")) {
                    currentPage = "chat";
                    const script = document.createElement("script");
                    script.src = "/static/js/chat.js";
                    script.onload = () => {
                         if (window.initChat) {
                             window.initChat();
                         } else {
                             console.error("initChat n'est pas défini après le chargement de chat.js.");
                         }
                    };
                    document.body.appendChild(script);
                } else {
                    currentPage = "register";

                    // Désactiver temporairement le bouton de soumission
                    const form = document.getElementById("register-form");
                    if (form) {
                        const submitBtn = form.querySelector('button[type="submit"]');
                        if (submitBtn) submitBtn.disabled = true;
                    }

                    const script = document.createElement("script");
                    script.src = "/static/js/register.js";
                    script.onload = () => {
                        // Réactiver le bouton une fois le script chargé
                        const form = document.getElementById("register-form");
                        if (form) {
                            const submitBtn = form.querySelector('button[type="submit"]');
                            if (submitBtn) submitBtn.disabled = false;
                        }
                    };
                    document.body.appendChild(script);
                }
            } else {
                console.error("Erreur lors du fetch de", url);
            }
        } catch (e) {
            console.error(e);
        }
    }
    window.navigateTo = navigateTo;  // Exposer navigateTo globalement

    function destroyCurrentPage() {
        const appDiv = document.getElementById("app");

        if (currentPage === "home") {
            if (window.destroyHome) {
                window.destroyHome();
            }
        } else if (currentPage === "game") {
            if (window.destroyPong) {
                window.destroyPong();
            }
        }

        // Effacer le contenu actuel
        appDiv.innerHTML = "";
        currentPage = null;
    }


    document.addEventListener("DOMContentLoaded", async function () {
        const appDiv = document.getElementById("app");

        if (appDiv.innerHTML.trim() !== "") {
            return;
        }

        // Charger la page initiale via AJAX
        if (location.pathname === "/" || location.pathname === "") {
            currentPage = "home";

            try {
                const resp = await fetch("/", {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });

                if (resp.ok) {
                    const htmlSnippet = await resp.text();
                    appDiv.innerHTML = htmlSnippet;

                    if (window.initHome) {
                        window.initHome();
                    }
                } else {
                    console.error("Erreur lors du fetch initial de /");
                }
            } catch (e) {
                console.error("Erreur lors du chargement initial :", e);
            }
        } else {
            navigateTo(location.pathname, false);
        }
    });

    function loadScriptOnce(src) {
        // Vérifie si un script avec ce src est déjà chargé
        if (!document.querySelector(`script[src="${src}"]`)) {
            const script = document.createElement("script");
            script.src = src;
            document.body.appendChild(script);
        }
    }
})();

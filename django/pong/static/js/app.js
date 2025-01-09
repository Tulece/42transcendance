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

        // On détruit la page précédente (Pong, Home, etc.)
        destroyCurrentPage();

        // Gère l'historique (pushState ou non)
        if (pushState) {
            history.pushState(null, "", url);
        }

        // Si c'est '/' (ou ''), on ne fetch pas, on restaure la home initiale
        if (url === "/" || url === "") {
            currentPage = "home";
            // On ré-injecte le HTML initial dans #app
            const appDiv = document.getElementById("app");
            appDiv.innerHTML = initialHomeHtml;

            // Puis on relance initHome() pour que les écouteurs fonctionnent
            if (window.initHome) {
                window.initHome();
            }
            return;
        }

        // Sinon, on fait la requête AJAX (ex: /game, /register, etc.)
        try {
            const resp = await fetch(url, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });
            if (resp.ok) {
                const htmlSnippet = await resp.text();
                const appDiv = document.getElementById("app");
                appDiv.innerHTML = htmlSnippet;

                if (url.includes("/game")) {
                    currentPage = "game";
                    if (window.initPong) {
                        window.initPong();
                    }
                } else if (url.includes("/register")) {
                    currentPage = "register";
                    // initRegister() si besoin
                } else {
                    currentPage = "unknown";
                }
            } else {
                console.error("Error fetching", url);
            }
        } catch (e) {
            console.error(e);
        }
    }

    function destroyCurrentPage() {
        if (currentPage === "home") {
            if (window.destroyHome) {
                window.destroyHome();
            }
        } else if (currentPage === "game") {
            if (window.destroyPong) {
                window.destroyPong();
            }
        }
        // S'il y a d'autres pages (register?), on pourrait faire pareil
        currentPage = null;
    }

    document.addEventListener("DOMContentLoaded", function() {
        // On stocke le HTML initial de la home :
        const appDiv = document.getElementById("app");
        initialHomeHtml = appDiv.innerHTML;

        // Au démarrage, si on est sur '/', on reste tel quel
        if (location.pathname === "/" || location.pathname === "") {
            currentPage = "home";
            if (window.initHome) {
                window.initHome();
            }
        } else {
            // Sinon (ex: /game), c’est un accès direct =>
            // la page "shell" (home.html) est chargée,
            // on fetch le fragment pour la vue en cours
            navigateTo(location.pathname, false);
        }
    });

})();

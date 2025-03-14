// app.js
(function () {
    let currentPage = null;

    // Gérer les clics sur les liens de navigation SPA
    document.addEventListener("click", function (event) {
        const link = event.target.closest(".spa-link");
        if (!link) return;

        event.preventDefault();
        const url = link.getAttribute("href");
        navigateTo(url);
    });

    // Gérer la navigation par les boutons Précédent/Suivant du navigateur
    window.addEventListener("popstate", function () {
        navigateTo(location.pathname, false);
    });

    async function navigateTo(url, pushState = true) {
        console.log("[navigateTo]", url, " From : ", location.pathname);

        if (location.pathname === url.split("?")[0] && pushState) {
            console.log("[navigateTo] Déjà sur l'URL:", url);
            return;
        }

        handlePageUnload(location.pathname);

        if (pushState) {
            history.pushState(null, "", url);
        }

        try {
            const response = await fetch(url, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "include",
            });

            if (response.status === 403) {
                alert("Vous devez être connecté pour accéder à cette page !");
                // Optionnel : rediriger vers la page d'accueil ou effectuer une autre action
                // navigateTo("/");
                return;
            }


            if (!response.ok) {
                console.error("Erreur fetch URL:", url, "status =", response.status);
                return;
            }

            const htmlSnippet = await response.text();
            const appDiv = document.getElementById("app");
            appDiv.innerHTML = htmlSnippet;

            handlePageSpecificScripts(url);

        } catch (error) {
            console.error("Erreur réseau :", error);
        }
    }

    function handlePageUnload(oldUrl) {
        if (!oldUrl) return;

        if (oldUrl.includes("/game")) {
            if (typeof window.destroyPong === "function") {
                window.destroyPong();
            }
            let oldScript = document.querySelector('script[src="/static/js/pong.js"]');
            if (oldScript) {
                console.log("old script removed");
                oldScript.remove();
            }
        }
    }

    function handlePageSpecificScripts(url) {
        if (url.includes("/game")) {
            loadScriptOnce("/static/js/pong.js", () => {
                if (window.initPong) window.initPong();
            });
        } else if (url.includes("/chat")) {
            // Check si le chat était déjà init => Réinitialisation to go on /chat/ page
            if (window.chatInitialized) {
                console.warn("Chat déjà initialisé, réinitialisation...");
                window.hideChat(); // Nettoie le chat avant de le réinitialiser
            }

            loadScriptOnce("/static/js/chat.js", () => {
                if (window.initChat) {
                    window.initChat();
                }
            });
        } else if (url.includes("/login")) {
            loadScriptOnce("/static/js/login.js", () => {
                console.log("Script de connexion chargé.");
            });
        } else if (url.includes("/account")) {
            loadScriptOnce("/static/js/account.js", () => {
                console.log("Script de la page compte chargé.");
                if (window.initFriendshipActions) {
                    console.log("PASSED APP.JS !!");
                    window.initFriendshipActions();
                }
            });
        }
    }

    function loadScriptOnce(src, callback) {
        if (!document.querySelector(`script[src="${src}"]`)) {
            const script = document.createElement("script");
            script.src = src;
            script.onload = callback;
            document.body.appendChild(script);
        } else if (callback) {
            callback();
        }
    }

    // Charger la page initiale lors du chargement du DOM
    document.addEventListener("DOMContentLoaded", async function () {
        await updateUserInfo(); // Check authentification + chat

        if (location.pathname === "/" || location.pathname === "") {
            navigateTo("/", false);
        } else {
            navigateTo(location.pathname, false);
        }
    });

    // Exposer navigateTo pour un accès global (optionnel)
    window.navigateTo = navigateTo;
})();


// ----- En-dessous, les fonctions globales -----

async function fetchUserInfo() {
    try {
        const response = await fetch("/api/user_info/", {
            method: "GET",
            credentials: "include",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        if (response.ok) {
            const userInfo = await response.json();
            updateHeaderUserInfo(userInfo);
        } else {
            console.warn("Utilisateur non connecté ou erreur :", response.status);
            updateHeaderUserInfo(null);
        }
    } catch (error) {
        console.error("Erreur lors de la récupération des infos utilisateur :", error);
        updateHeaderUserInfo(null);
    }
}

function updateHeaderUserInfo(userInfo) {
    const userDisplay = document.getElementById("user-display");
    const loginLink = document.getElementById("login-link");
    const logoutBtn = document.getElementById("logout-btn");
    let registerItem = document.getElementById("register-link");

    const navbar = document.querySelector(".navbar-nav"); // Récupère la liste des liens de navigation

    if (userInfo) {
        // Utilisateur connecté
        userDisplay.textContent = `Bonjour, ${userInfo.username}`;
        loginLink.style.display = "none"; // Cache "Connexion"
        logoutBtn.style.display = "inline"; // Affiche "Déconnexion"

        if (registerItem) {
            registerItem.style.display = "none";  // Cache "S'inscrire" au lieu de le supprimer
        }

        logoutBtn.onclick = async () => {
            try {
                const csrfToken = getCSRFToken();
                const response = await fetch("/api/logout/", {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": csrfToken,
                    },
                    credentials: "include",
                });
                if (response.ok) {
                    console.log("Déconnexion réussie.");
                    updateHeaderUserInfo(null);
                    await updateUserInfo();
                } else {
                    console.error("Erreur lors de la déconnexion :", response.status);
                }
            } catch (error) {
                console.error("Erreur réseau lors de la déconnexion :", error);
            }
        };
    } else {
        // Utilisateur déconnecté
        userDisplay.textContent = "Non connecté";
        loginLink.style.display = "inline";
        logoutBtn.style.display = "none";

        if (!registerItem) {
            // Recrée "S'inscrire" dynamiquement en le plaçant au bon endroit
            registerItem = document.createElement("li");
            registerItem.className = "nav-item";
            registerItem.id = "register-link";
            registerItem.innerHTML = `<a href="/register" class="nav-link spa-link">S'inscrire</a>`;

            // Trouver "Mon compte" pour insérer "S'inscrire" juste avant
            const accountItem = document.querySelector("a[href='/account']")?.parentElement;
            if (navbar && accountItem) {
                navbar.insertBefore(registerItem, accountItem);
            }
        } else {
            registerItem.style.display = "block"; // Réaffiche "S'inscrire"
        }
    }
}


async function updateUserInfo() {
    try {
        const response = await fetch("/api/user_info/", {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Authorization": `Bearer ${getAccessToken()}`, // Inclure le token d'accès si besoin
            },
            credentials: "include", // Inclure les cookies
        });

        if (response.ok) {
            const data = await response.json();
            updateHeaderUserInfo(data);

            const chatWrapper = document.getElementById("chat-wrapper");
            if (chatWrapper) chatWrapper.style.display = "block";

            if (window.initChat && !window.chatInitialized) {
                console.log("Initialisation du chat ...");
                window.initChat();
            }
        }
        // else if (response.status === 403) {
        //     console.info("Utilisateur non connecté.");
        //     updateHeaderUserInfo(null);
        //     if (window.hideChat) window.hideChat();
        // }
        else {
            console.info("Utilisateur non connecté.");
            updateHeaderUserInfo(null);
            if (window.hideChat) window.hideChat(); // Désactive if user déconnecté.
        }
    } catch (error) {
        console.error("Erreur réseau lors de la récupération des informations utilisateur :", error);
        updateHeaderUserInfo(null);
        if (window.hideChat) window.hideChat();
    }
}

function getAccessToken() {
    const cookieValue = document.cookie
        .split("; ")
        .find(row => row.startsWith("access_token="))
        ?.split("=")[1];
    return cookieValue || null;
}

// Exposer updateUserInfo globalement
function getCSRFToken() {
    const csrfMetaTag = document.querySelector('meta[name="csrf-token"]');
    if (csrfMetaTag) {
        return csrfMetaTag.getAttribute("content");
    }
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

window.getCSRFToken = getCSRFToken;

// app.js
(function () {
    let currentPage = window.location.pathname;

    document.addEventListener("click", function (event) {
        const link = event.target.closest(".spa-link");
        if (!link) return;

        event.preventDefault();
        const url = link.getAttribute("href");
        navigateTo(url);
    });

    window.addEventListener("popstate", function () {
        if (currentPage.includes("/game") && typeof window.destroyPong === "function") {
            window.destroyPong();
        }
        currentPage = location.pathname;
        navigateTo(location.pathname, false);
    });

    async function navigateTo(url, pushState = true) {
        if (currentPage.includes("/game") && typeof window.destroyPong === "function") {
            window.destroyPong();
        }
        currentPage = url;

        try {
            handlePageUnload(currentPage);

            const ajaxUrl = url.includes('?') ? `${url}&fragment=1` : `${url}?fragment=1`;

            const response = await fetch(ajaxUrl, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "include"
            });

            if (response.status === 403) {
                alert("Vous devez être connecté pour accéder à cette page !");
                return;
            }
            if (!response.ok) {
                console.error("Erreur fetch URL:", ajaxUrl, "status =", response.status);
                return;
            }

            if (pushState) {
                history.pushState(null, "", url);
            }

            const htmlSnippet = await response.text();

            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlSnippet, "text/html");
            const newContent = doc.getElementById("content");
            if (newContent) {
                document.getElementById("content").innerHTML = newContent.innerHTML;
            } else {
                document.getElementById("app").innerHTML = htmlSnippet;
            }

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
            if (window.chatInitialized) {
                console.warn("Chat déjà initialisé, réinitialisation...");
                window.hideChat();
            }
            loadScriptOnce("/static/js/chat.js", () => {
                if (window.initChat) {
                    window.initChat();
                }
            });
        } else if (url.includes("/login")) {
            loadScriptOnce("/static/js/login.js", () => {});
        } else if (url.includes("/account")) {
            loadScriptOnce("/static/js/account.js", () => {
                if (window.initAccount) {
                    window.initAccount();
                }
            });
        } else if (url.includes("/tournaments/blockchain")) {
            loadScriptOnce("/static/js/blockchain_tournaments.js", () => {
                if (window.initBlockchainTournamentPage) {
                    window.initBlockchainTournamentPage();
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

    document.addEventListener("DOMContentLoaded", async function () {
        await updateUserInfo();

        if (location.pathname === "/" || location.pathname === "") {
            navigateTo("/", false);
        } else {
            navigateTo(location.pathname, false);
        }
    });

    window.navigateTo = navigateTo;
})();


// ----- Fonctions globales -----

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

    const navbar = document.querySelector(".navbar-nav");

    if (userInfo) {
        userDisplay.textContent = `Bonjour, ${userInfo.username}`;
        loginLink.style.display = "none";
        logoutBtn.style.display = "inline";

        if (registerItem) {
            registerItem.style.display = "none";
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
                    updateHeaderUserInfo(null);
                    await updateUserInfo();
                    if (window.hideChat) window.hideChat();
                } else {
                    console.error("Erreur lors de la déconnexion :", response.status);
                }
            } catch (error) {
                console.error("Erreur réseau lors de la déconnexion :", error);
            }
        };
    } else {
        userDisplay.textContent = "Non connecté";
        loginLink.style.display = "inline";
        logoutBtn.style.display = "none";

        if (!registerItem) {
            registerItem = document.createElement("li");
            registerItem.className = "nav-item";
            registerItem.id = "register-link";
            registerItem.innerHTML = `<a href="/register" class="nav-link spa-link">S'inscrire</a>`;

            const accountItem = document.querySelector("a[href='/account']")?.parentElement;
            if (navbar && accountItem) {
                navbar.insertBefore(registerItem, accountItem);
            }
        } else {
            registerItem.style.display = "block";
        }
    }
}

async function updateUserInfo() {
    try {
        const response = await fetch("/api/user_info/", {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Authorization": `Bearer ${getAccessToken()}`,
            },
            credentials: "include",
        });

        if (response.ok) {
            const data = await response.json();
            updateHeaderUserInfo(data);

            const chatWrapper = document.getElementById("chat-wrapper");
            if (chatWrapper) chatWrapper.style.display = "block";

            if (window.initChat && !window.chatInitialized) {
                window.initChat();
            }
        }
        else {
            updateHeaderUserInfo(null);
            if (window.hideChat) window.hideChat();
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

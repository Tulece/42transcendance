// static/js/tournaments.js

// let lobbySocket;

document.addEventListener("DOMContentLoaded", () => {
  // --- Gestion du formulaire de création de tournoi ---
  const createForm = document.getElementById("createTournamentForm");
  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(createForm);
      try {
        const response = await fetch("/tournaments/create/", {
          method: "POST",
          body: formData,
          credentials: "include",
        });
        const data = await response.json();
        if (response.ok && data.success) {
          alert(data.message);
          // Redirige l'utilisateur vers la page de liste des tournois
          window.location.href = "/tournaments/list/";
        } else {
          console.error("Erreur:", data.error);
          alert("Erreur lors de la création du tournoi.");
        }
      } catch (error) {
        console.error("Network error:", error);
      }
    });
  }

 // --- Gestion du clic sur le bouton "Rejoindre" ---
  const joinButtons = document.querySelectorAll(".join-tournament");
  joinButtons.forEach((button) => {
    button.addEventListener("click", async (e) => {
      e.preventDefault();
      const url = button.getAttribute("href");
      try {
        const response = await fetch(url, {
          method: "POST",
          credentials: "include",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            // Utilisation de la fonction getCSRFToken définie dans app.js :
            "X-CSRFToken": getCSRFToken(),
          },
        });
        const data = await response.json();
        if (response.ok && data.success) {
          alert(data.message);
          // Une fois l'utilisateur inscrit, redirigez (via votre navigation SPA) vers le détail du tournoi :
          navigateTo(`/tournaments/${data.tournament_id}/`);
        } else {
          alert(data.error || "Erreur lors de la jointure.");
        }
      } catch (error) {
        console.error("Erreur lors de la requête de jointure :", error);
      }
    });
  });

  // --- Gestion d'une connexion WebSocket pour les mises à jour du tournoi ---
  // Si vous souhaitez utiliser le WebSocket pour rafraîchir automatiquement un tournoi
  const tournamentContainer = document.getElementById("tournamentContainer");
  if (tournamentContainer && tournamentContainer.dataset.tournamentId) {
    const tournamentId = tournamentContainer.dataset.tournamentId;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const tournamentSocket = new WebSocket(
      protocol + "://" + window.location.host + "/ws/tournament/" + tournamentId + "/"
    );
    tournamentSocket.onopen = function (event) {
      console.log("WS connecté pour le tournoi", tournamentId);
    };
    tournamentSocket.onmessage = function (event) {
      const data = JSON.parse(event.data);
      console.log("Mise à jour WS:", data);
      loadTournamentDetail(tournamentId);
    };
    tournamentSocket.onerror = function (error) {
      console.error("Erreur WS:", error);
    };
    tournamentSocket.onclose = function (event) {
      console.log("WS déconnecté pour le tournoi", tournamentId);
    };
  }
});

// --- Fonction pour charger le détail d’un tournoi en AJAX ---
async function loadTournamentDetail(tournamentId) {
  try {
    const resp = await fetch(`/tournaments/${tournamentId}/`, {
      method: "GET",
      credentials: "include",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const contentType = resp.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
      // La réponse est au format JSON
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        console.error("Erreur:", data.error);
        return;
      }
      displayTournament(data.tournament);
    } else {
      // Sinon, on considère que le serveur a renvoyé du HTML
      const html = await resp.text();
      const container = document.getElementById("tournamentContainer");
      if (container) {
        container.innerHTML = html;
      }
    }
  } catch (err) {
    console.error(err);
  }
}

// --- Fonction pour afficher le tournoi et ses matchs ---
function displayTournament(tournamentData) {
  const container = document.getElementById("tournamentContainer");
  if (!container) return;
  container.innerHTML = `
    <h2>Tournoi : ${tournamentData.name}</h2>
    <ul id="matchList"></ul>
  `;
  const matchList = container.querySelector("#matchList");
  tournamentData.matches.forEach((match) => {
    const li = document.createElement("li");
    li.innerHTML = `
      Round ${match.round_number} : ${match.player1} vs ${match.player2 ? match.player2 : "Bye"}
      ${match.winner ? "(Gagnant : " + match.winner + ")" : `<button onclick="startMatch(${match.match_id}, ${tournamentData.id})">Lancer la partie</button>`}
    `;
    matchList.appendChild(li);
  });
}

// --- Fonction pour lancer la partie de Pong pour un match de tournoi ---
async function startMatch(matchId, tournamentId) {
  try {
    const resp = await fetch(`/tournaments/match/${matchId}/start_game/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({})  // Envoi d'un objet JSON vide
    });
    const data = await resp.json();
    if (resp.ok && data.success) {
      // Redirige vers la page du jeu Pong avec le game_id reçu
      window.location.href = `/game/?game_id=${data.game_id}`;
    } else {
      console.error("Erreur:", data.error);
    }
  } catch (err) {
    console.error("Erreur réseau :", err);
  }
}

window.startMatch = startMatch;

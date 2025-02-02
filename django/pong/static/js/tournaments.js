// static/js/tournaments.js

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
            // Charge le détail du tournoi créé
            loadTournamentDetail(data.tournament_id);
          } else {
            console.error("Erreur:", data.error);
            alert("Erreur lors de la création du tournoi.");
          }
        } catch (error) {
          console.error("Network error:", error);
        }
      });
    }

    // --- Connexion WebSocket pour suivre les mises à jour du tournoi ---
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
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        console.error("Erreur:", data.error);
        return;
      }
      displayTournament(data.tournament);
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
      console.error(err);
    }
  }



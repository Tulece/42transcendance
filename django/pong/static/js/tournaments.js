// static/js/tournaments.js
document.addEventListener("DOMContentLoaded", () => {
    const createForm = document.getElementById("createTournamentForm");
    if (createForm) {
        createForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(createForm);

            try {
                const response = await fetch("/tournaments/create/", {
                    method: "POST",
                    body: formData,
                    credentials: "include", // si tu utilises CSRF / cookies
                });
                const data = await response.json();

                if (response.ok && data.success) {
                    alert(data.message);
                    // On peut par exemple naviguer vers le détail du tournoi en AJAX
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
});

// Fonction pour charger le détail d’un tournoi et l’afficher
async function loadTournamentDetail(tournamentId) {
    try {
        const resp = await fetch(`/tournaments/${tournamentId}/`, {
            method: "GET",
            credentials: "include",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        const data = await resp.json();

        if (!resp.ok || !data.success) {
            console.error("Erreur:", data.error);
            return;
        }

        // On a data.tournament.matches
        displayTournament(data.tournament);
    } catch (err) {
        console.error(err);
    }
}

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
        ${match.winner ? "(Gagnant : " + match.winner + ")" : ""}
        ${
          !match.winner && match.player2
            ? `
              <button onclick="reportMatch(${match.match_id}, ${match.player1_id}, ${tournamentData.id})">
                Gagnant: ${match.player1}
              </button>
              <button onclick="reportMatch(${match.match_id}, ${match.player2_id}, ${tournamentData.id})">
                Gagnant: ${match.player2}
              </button>`
            : ""
        }
      `;
      matchList.appendChild(li);
    });
  }


// Fonction pour reporter le vainqueur d’un match
async function reportMatch(matchId, winnerId, tournamentId) {
    const formData = new FormData();
    formData.append("winner_id", winnerId);

    try {
        const resp = await fetch(`/tournaments/match/${matchId}/report/`, {
            method: "POST",
            body: formData,
            credentials: "include"
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            alert(data.message);
            // <-- Ici, on recharge l’affichage du tournoi
            loadTournamentDetail(tournamentId);
        } else {
            console.error("Erreur:", data.error);
        }
    } catch (err) {
        console.error(err);
    }
}


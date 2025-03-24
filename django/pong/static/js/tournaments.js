// static/js/tournaments.js
document.addEventListener("submit", async (e) => {
	const form = e.target;
	if (form && form.id === "createTournamentForm") {
	  e.preventDefault();
	  const formData = new FormData(form);
	  try {
		const response = await fetch("/tournaments/create/", {
		  method: "POST",
		  body: formData,
		  credentials: "include",
		  headers: {
			"X-Requested-With": "XMLHttpRequest"
		  }
		});
		const data = await response.json();
		if (response.ok && data.success) {
		  alert(data.message);
		  navigateTo("/tournaments/list/");
		} else {
		  console.error("Erreur:", data.error);
		  alert(data.error || "Erreur lors de la création du tournoi.");
		}
	  } catch (error) {
		console.error("Network error:", error);
	  }
	}
  });

  document.addEventListener("DOMContentLoaded", () => {
	// Gestion du clic sur le bouton "Rejoindre"
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
			  "X-CSRFToken": getCSRFToken(),
			},
		  });
		  const data = await response.json();
		  if (response.ok && data.success) {
			alert(data.message);
			navigateTo(`/tournaments/${data.tournament_id}/`);
		  } else {
			alert(data.error || "Erreur lors de la jointure.");
		  }
		} catch (error) {
		  console.error("Erreur lors de la requête de jointure :", error);
		}
	  });
	});

	// (ADDED) Vérifier si on est sur la page "list_tournaments"
	// en regardant si on a #tournament-list-container
	const listContainer = document.getElementById("tournament-list-container");
	if (listContainer) {
	  initGlobalTournamentsWS(); // On connecte le WebSocket global des tournois
	}

	// Initialisation du canal WebSocket pour le détail d'un tournoi
	const tournamentContainer = document.getElementById("tournamentContainer");
	if (tournamentContainer && tournamentContainer.dataset.tournamentId) {
	  const tournamentId = tournamentContainer.dataset.tournamentId;
	  initTournamentSocket(tournamentId);
	}
  });

  // (ADDED) Connecte la page "Liste des tournois" au WS global
  function initGlobalTournamentsWS() {
	const protocol = window.location.protocol === "https:" ? "wss" : "ws";
	const ws = new WebSocket(`${protocol}://${window.location.host}/ws/tournamentsGlobal/`);

	ws.onopen = () => {
	  console.log("[TournamentsGlobalWS] Connecté");
	};

	ws.onmessage = (event) => {
	  const data = JSON.parse(event.data);
	  console.log("[TournamentsGlobalWS] Reçu:", data);
	  if (data.action === "new_tournament") {
		console.log("Nouveau tournoi détecté:", data.tournament_name);
		// On rafraîchit la liste via AJAX
		refreshTournamentList();
	  }
	};

	ws.onclose = () => {
	  console.log("[TournamentsGlobalWS] Fermé");
	};

	ws.onerror = (err) => {
	  console.error("[TournamentsGlobalWS] Erreur:", err);
	};
  }

  // (ADDED) Rafraîchit la liste via un fetch AJAX
  async function refreshTournamentList() {
	try {
	  const resp = await fetch("/tournaments/list/", {
		method: "GET",
		headers: { "X-Requested-With": "XMLHttpRequest" },
		credentials: "include"
	  });
	  if (!resp.ok) {
		throw new Error(`Erreur fetch: ${resp.status}`);
	  }
	  const htmlSnippet = await resp.text();

	  // On remplace tout le bloc #tournament-list-container
	  const container = document.getElementById("tournament-list-container");
	  if (container) {
		container.innerHTML = htmlSnippet;
	  }
	} catch (err) {
	  console.error("Erreur refreshTournamentList:", err);
	}
  }

  // Initialise le WebSocket pour recevoir les mises à jour du tournoi (détail)
  function initTournamentSocket(tournamentId) {
	const protocol = window.location.protocol === "https:" ? "wss" : "ws";
	const tournamentSocket = new WebSocket(
	  `${protocol}://${window.location.host}/ws/tournament/${tournamentId}/`
	);
	tournamentSocket.onopen = function () {
	  console.log("WS connecté pour le tournoi", tournamentId);
	};
	tournamentSocket.onmessage = function (event) {
	  const data = JSON.parse(event.data);
	  console.log("WebSocket - Mise à jour reçue :", data);
	  if (data.success) {
		console.log("Rafraîchissement du tournoi...");
		loadTournamentDetail(tournamentId);
	  } else {
		console.warn("Mise à jour non valide reçue :", data);
	  }
	};
	tournamentSocket.onerror = function (error) {
	  console.error("Erreur WS:", error);
	};
	tournamentSocket.onclose = function () {
	  console.log("WS déconnecté pour le tournoi", tournamentId);
	};
  }

  // Charge le détail du tournoi via AJAX
  async function loadTournamentDetail(tournamentId) {
	try {
	  const resp = await fetch(`/tournaments/${tournamentId}/`, {
		method: "GET",
		credentials: "include",
		headers: { "X-Requested-With": "XMLHttpRequest" },
	  });
	  if (!resp.ok) {
		throw new Error(`Erreur serveur : ${resp.status}`);
	  }
	  const contentType = resp.headers.get("content-type");
	  if (contentType && contentType.indexOf("application/json") !== -1) {
		const data = await resp.json();
		if (!data.success) {
		  throw new Error(data.error || "Réponse invalide");
		}
		displayTournament(data.tournament);
	  } else {
		const html = await resp.text();
		const container = document.getElementById("tournamentContainer");
		if (container) {
		  container.innerHTML = html;
		}
	  }
	} catch (err) {
	  console.error("Erreur lors du chargement du tournoi :", err);
	}
  }

  // Affiche la liste des matchs du tournoi
  function displayTournament(tournamentData) {
	const container = document.getElementById("tournamentContainer");
	if (!container) return;
	container.innerHTML = `<h2>Tournoi : ${tournamentData.name}</h2>
	  <ul id="matchList" class="list-group"></ul>`;
	const matchList = container.querySelector("#matchList");
	matchList.innerHTML = "";
	tournamentData.matches.forEach((match) => {
	  const li = document.createElement("li");
	  li.classList.add("list-group-item");
	  let content = `Round ${match.round_number} : ${match.player1} vs ${
		match.player2 ? match.player2 : "Bye"
	  }`;
	  if (match.game_id) {
		if (match.winner) {
		  content += ` — Gagnant : ${match.winner}`;
		} else {
		  content += " — Partie lancée";
		}
	  } else {
		content += ` <button class="start-match-btn" data-match-id="${match.match_id}" data-tournament-id="${tournamentData.id}">Lancer la partie</button>`;
	  }
	  li.innerHTML = content;
	  matchList.appendChild(li);
	});
	// Activation des boutons
	document.querySelectorAll(".start-match-btn").forEach((btn) => {
	  btn.addEventListener("click", () => {
		const matchId = btn.dataset.matchId;
		const tournamentId = btn.dataset.tournamentId;
		startMatch(matchId, tournamentId);
	  });
	});
  }

  // Lance une partie en appelant la vue start_match_game_view
  async function startMatch(matchId, tournamentId) {
	try {
	  const resp = await fetch(`/tournaments/match/${matchId}/start_game/`, {
		method: "POST",
		credentials: "include",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({})
	  });
	  const data = await resp.json();
	  if (resp.ok && data.success) {
		if (data.game_id) {
		  navigateTo(`/game/?game_id=${data.game_id}&mode=tournament&role=${data.role}&match_id=${matchId}&tournament_id=${tournamentId}&player1_id=${data.player1_id}&player2_id=${data.player2_id}`);
		} else if (data.message) {
		  alert(data.message);
		}
	  } else {
		if (data.error && data.error.toLowerCase().includes("match terminé")) {
		  const btn = document.querySelector(`button.start-match-btn[data-match-id="${matchId}"]`);
		  if (btn) {
			btn.disabled = true;
			btn.innerText = "Match terminé";
		  }
		  alert("Ce match a déjà été joué.");
		  loadTournamentDetail(tournamentId);
		} else {
		  console.error("Erreur:", data.error);
		  alert("Erreur lors du lancement du match.");
		}
	  }
	} catch (err) {
	  console.error("Erreur réseau :", err);
	}
  }

  window.startMatch = startMatch;

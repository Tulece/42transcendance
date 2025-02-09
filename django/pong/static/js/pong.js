// static/js/pong.js

let canvas, ctx;
let lobbySocket = null;
let gameSocket = null;
let game_running = false;
let key_pressed = {};
let host = "";
let role = "";
let matchId = null; // On stockera le match_id pour le report

const ball = { x: 0, y: 0, radius: 5 };
const player1 = { x: 0, y: 0, hp: 5 };
const player2 = { x: 0, y: 0, hp: 5 };

window.initPong = function () {
  console.log("Initialisation du jeu Pong...");
  setupCanvas();
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  if (mode === "tournament") {
    const gameId = params.get("game_id");
    role = params.get("role");
    matchId = params.get("match_id"); // récupérer le match_id
    if (gameId && role) {
      connectToGame(gameId, role);
    } else {
      console.error("Game ID ou rôle manquant en mode tournoi.");
    }
  } else {
    connectToLobby();
  }
};

function setupCanvas() {
  canvas = document.getElementById("pong");
  if (!canvas) {
    console.error("Canvas non trouvé !");
    return;
  }
  ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "20px Arial";
  ctx.fillText("Connexion au lobby en cours...", canvas.width / 2 - 100, canvas.height / 2);
}

function connectToLobby() {
  host = window.location.hostname;
  lobbySocket = new WebSocket(`ws://${host}:8000/ws/matchmaking/`);
  let dots = 0;
  lobbySocket.onopen = () => {
    console.log("Connexion au lobby établie.");
    const params = new URLSearchParams(window.location.search);
    const mode = params.get("mode");
    lobbySocket.send(JSON.stringify({ action: "find_game", mode: mode }));
  };
  lobbySocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "game_found") {
      console.log(`Partie trouvée : ${data.game_id}`);
      lobbySocket.close();
      role = data.role;
      connectToGame(data.game_id, data.role);
    } else if (data.type === "waiting") {
      displayWaitingMessage(data.message, -1);
    }
  };
  lobbySocket.onclose = () => {
    console.log("Connexion au lobby fermée.");
  };
  lobbySocket.onerror = (error) => {
    console.error("Erreur lors de la connexion au lobby :", error);
  };
}

function displayWaitingMessage(message, dots) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "20px Arial";
  ctx.fillStyle = "white";
  const textMetrics = ctx.measureText(message);
  const textWidth = textMetrics.width;
  let x_pos = (canvas.width / 2) - (textWidth / 2);
  ctx.fillText(message, x_pos, canvas.height / 2);
  for (let i = 0; i <= dots; ++i) {
    ctx.fillText(".", x_pos + textWidth + (i * 10), canvas.height / 2);
  }
}

function connectToGame(gameId, roleParam) {
  role = roleParam;
  host = window.location.hostname;
  gameSocket = new WebSocket(`ws://${host}:8000/ws/game/${gameId}/?player_id=${roleParam}`);
  gameSocket.onopen = () => {
    console.log(`Connecté à la partie : ${gameId}, rôle : ${roleParam}`);
    initializeGameControls();
    game_running = true;
  };
  gameSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleGameMessage(data, role);
  };
  gameSocket.onclose = () => {
    console.log("Connexion à la partie fermée.");
    game_running = false;
  };
  gameSocket.onerror = (error) => {
    console.error("Erreur lors de la connexion au jeu :", error);
  };
}

function handleGameMessage(data, role) {
  console.log("Message received: ", data);
  if (data.type === "position_update") {
    ball.x = data.ball_position.x;
    ball.y = data.ball_position.y;
    player1.x = data.player1_state.x;
    player1.y = data.player1_state.y;
    player1.hp = data.player1_state.lifepoints;
    player2.x = data.player2_state.x;
    player2.y = data.player2_state.y;
    player2.hp = data.player2_state.lifepoints;
    updateCanvas();
  } else if (data.type === "game_over") {
    let msg = "";
    if (data.message.includes(role)) {
      msg = "You Lose...";
      if (data.message.includes("lifepoints"))
        msg += " You're out of lifepoints.";
      else
        msg += " You disconnected.";
    } else {
      msg = "You Won !";
      if (data.message.includes("lifepoints"))
        msg += " Your opponent is out of lifepoints.";
      else
        msg += " Opponent disconnected.";
    }
    alert(msg);
    game_running = false;
    // En mode tournoi, on reporte le résultat via l'API
    const params = new URLSearchParams(window.location.search);
    if (params.get("mode") === "tournament" && matchId) {
      // Pour que le report fonctionne, l'URL de la partie doit inclure aussi player1_id et player2_id.
      const player1_id = params.get("player1_id");
      const player2_id = params.get("player2_id");
      let winner;
      if (data.message.includes(role)) {
        // Vous avez perdu, donc le vainqueur est l'autre joueur
        winner = (role === "player1") ? player2_id : player1_id;
      } else {
        // Vous avez gagné, donc vous êtes le vainqueur
        winner = (role === "player1") ? player1_id : player2_id;
      }
      fetch(`/tournaments/match/${matchId}/report_result/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ "winner_id": winner })
      })
        .then(response => response.json())
        .then(result => {
          console.log("Résultat du report:", result);
          const tournamentId = params.get("tournament_id");
          if (tournamentId) {
            navigateTo(`/tournaments/${tournamentId}/`);
          } else {
            navigateTo("/");
          }
        })
        .catch(err => {
          console.error("Erreur lors du report du match:", err);
          navigateTo("/");
        });
    } else {
      navigateTo("/");
    }
  } else if (data.type === "waiting") {
    displayWaitingMessage(data.message, -1);
  }
}

function initializeGameControls() {
  document.addEventListener("keydown", onKeyDown);
  document.addEventListener("keyup", onKeyUp);
  console.log("Écouteurs d'événements ajoutés.");
}

function destroyGameControls() {
  document.removeEventListener("keydown", onKeyDown);
  document.removeEventListener("keyup", onKeyUp);
  console.log("Écouteurs d'événements supprimés.");
}

function destroyGameSocket() {
  if (gameSocket) {
    gameSocket.close();
    gameSocket = null;
  }
  console.log("GameSocket détruit.");
}

function destroyLobbySocket() {
  if (lobbySocket) {
    lobbySocket.close();
    lobbySocket = null;
  }
  console.log("LobbySocket détruit.");
}

function onKeyDown(e) {
  if (!key_pressed[e.key] && game_running) {
    key_pressed[e.key] = true;
    if (e.key === "ArrowUp") sendAction("move_up");
    if (e.key === "ArrowDown") sendAction("move_down");
    if (e.key === "Escape") sendAction("pause_game");
  }
}

function onKeyUp(e) {
  if (key_pressed[e.key]) {
    delete key_pressed[e.key];
    if (e.key === "ArrowUp") sendAction("stop_move_up");
    if (e.key === "ArrowDown") sendAction("stop_move_down");
  }
}

function sendAction(action) {
  if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
    gameSocket.send(JSON.stringify({ action }));
  } else {
    console.error("WebSocket pour le jeu non ouvert !");
  }
}

function updateCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBall();
  drawPlayer();
  drawOpponent();
}

function drawPlayer() {
  let color = role === "player1" ? "blue" : "red";
  ctx.font = "20px Arial";
  ctx.fillStyle = color;
  ctx.fillText("hp:", 10, 20);
  for (let i = 0; i < player1.hp; ++i) {
    drawHeart(50 + i * 15, 10, 10);
  }
  ctx.fillStyle = color;
  ctx.fillRect(player1.x, player1.y, 10, 70);
}

function drawOpponent() {
  let color = role === "player2" ? "blue" : "red";
  ctx.font = "20px Arial";
  ctx.fillStyle = color;
  ctx.fillText("hp:", canvas.width - 115, 20);
  for (let i = 0; i < player2.hp; ++i) {
    drawHeart(canvas.width - (5 - i) * 15, 10, 10);
  }
  ctx.fillStyle = color;
  ctx.fillRect(player2.x, player2.y, 10, 70);
}

function drawBall() {
  ctx.beginPath();
  ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
  ctx.fillStyle = "white";
  ctx.fill();
}

function drawHeart(x, y, size) {
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.bezierCurveTo(x - size / 2, y - size / 2, x - size, y + size / 3, x, y + size);
  ctx.bezierCurveTo(x + size, y + size / 3, x + size / 2, y - size / 2, x, y);
  ctx.closePath();
  ctx.fillStyle = "red";
  ctx.fill();
}

window.destroyPong = function () {
  console.log("destroyPong() called.");
  destroyGameControls();
  destroyLobbySocket();
  destroyGameSocket();
  if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
    gameSocket.send(JSON.stringify({ action: "quit_game" }));
    gameSocket.close();
  }
  gameSocket = null;
  game_running = false;
};

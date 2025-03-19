window.initPong = function () {
  if (window.pongInitialized) return;
  window.pongInitialized = true;
  console.log("Initialisation du jeu Pong...");

  let canvas, ctx;
  let lobbySocket = null;
  let gameSocket = null;
  let game_running = false;
  let key_pressed = {};
  let host = window.location.hostname || "localhost";
  let role = "";
  let matchId = null;

  const ball = { x: 0, y: 0, radius: 5 };
  const player1 = { x: 0, y: 0, hp: 5 };
  const player2 = { x: 0, y: 0, hp: 5 };

  function setupCanvas() {
    canvas = document.getElementById("pong");
    if (!canvas) {
        console.error("setupCanvas : Canvas non trouvé !");
        return;
    }
    ctx = canvas.getContext("2d");
    console.log("setupCanvas : ctx initialisé avec succès :", ctx);

    // Rendre ctx et canvas accessibles globalement
    window.ctx = ctx;
    window.canvas = canvas;
  }


  function connectToLobby() {
      host = window.location.hostname;
      lobbySocket = new WebSocket(`wss://${host}/ws/matchmaking/`);

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

      lobbySocket.onclose = () => console.log("Connexion au lobby fermée.");
      lobbySocket.onerror = (error) => console.error("Erreur WebSocket (lobby) :", error);
  }

  function connectToGame(gameId, role) {
      gameSocket = new WebSocket(`wss://${host}/ws/game/${gameId}/?player_id=${role}&mode=solo`);
      gameSocket.onopen = () => {
          console.log(`Connecté à la partie : ${gameId}, rôle : ${role}`);
          game_running = true;
          if (role === "local") initializeGameControls(role);
          else initializeGameControls();
      };

      gameSocket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          handleGameMessage(data, role);
      };

      gameSocket.onclose = () => {
          console.log("Connexion à la partie fermée.");
          game_running = false;
      };

      gameSocket.onerror = (error) => console.error("Erreur WebSocket (jeu) :", error);
  }

  function handleGameMessage(data, role) {
      console.log("Message reçu :", data);

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
          alert(`Game Over : ${data.message}`);
          game_running = false;

          // Gestion spécifique du mode tournoi
          const params = new URLSearchParams(window.location.search);
          if (params.get("mode") === "tournament" && matchId) {
              const player1_id = params.get("player1_id");
              const player2_id = params.get("player2_id");
              let winner = data.message.includes(role)
                  ? (role === "player1" ? player2_id : player1_id)
                  : (role === "player1" ? player1_id : player2_id);

              fetch(`/tournaments/match/${matchId}/report_result/`, {
                  method: "POST",
                  credentials: "include",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ "winner_id": winner })
              }).then(response => response.json())
                  .then(result => {
                      console.log("Résultat du report:", result);
                      const tournamentId = params.get("tournament_id");
                      navigateTo(tournamentId ? `/tournaments/${tournamentId}/` : "/");
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

  function initializeGameControls(role = undefined) {
      if (role) {
          document.addEventListener("keydown", localOnKeyDown);
          document.addEventListener("keyup", localOnKeyUp);
      } else {
          document.addEventListener("keydown", onKeyDown);
          document.addEventListener("keyup", onKeyUp);
      }
      console.log("Écouteurs d'événements ajoutés.");
  }

  function destroyGameControls() {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup", onKeyUp);
      document.removeEventListener("keydown", localOnKeyDown);
      document.removeEventListener("keyup", localOnKeyUp);
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

  function resetCanvas() {
      if (!canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillText("Jeu arrêté", canvas.width / 2 - 50, canvas.height / 2);
  }

  window.destroyPong = function () {
      console.log("destroyPong() appelé.");
      destroyGameControls();
      destroyLobbySocket();
      destroyGameSocket();
      resetCanvas();
      game_running = false;
      window.pongInitialized = false;
  };

  setupCanvas();
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  const gameId = params.get("game_id");
  const roleParam = params.get("role");
  if (mode === "tournament") {
    console.log("tournament mode detected");
    role = params.get("role");
    matchId = params.get("match_id"); // récupérer le match_id
    if (gameId && role) {
      connectToGame(gameId, role);
    } else {
      console.error("Game ID ou rôle manquant en mode tournoi.");
    }
  } else if (mode === 'private' && gameId) {
      console.log("private mode detected");
      role = params.get("role");
      connectToGame(gameId, roleParam);
  } else {
    console.log("no mode detected");
    connectToLobby();
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
    console.log("event up")
    if (key_pressed[e.key]) {
      delete key_pressed[e.key];
      if (e.key === "ArrowUp") sendAction("stop_move_up");
      if (e.key === "ArrowDown") sendAction("stop_move_down");
    }
  }

  function localOnKeyDown(e) {
      if (!key_pressed[e.key] && game_running) {
          key_pressed[e.key] = true;

          if (e.code === "KeyW") sendAction("move_up", "player1");
          if (e.code === "KeyS") sendAction("move_down", "player1");
          if (e.key === "ArrowUp") sendAction("move_up", "player2");
          if (e.key === "ArrowDown") sendAction("move_down", "player2");
          if (e.key === "Escape") sendAction("pause_game");
      }
  }

  function localOnKeyUp(e) {
      if (key_pressed[e.key]) {
          delete key_pressed[e.key];

          if (e.code === "KeyW") sendAction("stop_move_up", "player1");
          if (e.code === "KeyS") sendAction("stop_move_down", "player1");
          if (e.key === "ArrowUp") sendAction("stop_move_up", "player2");
          if (e.key === "ArrowDown") sendAction("stop_move_down", "player2");
      }
  }

  function sendAction(action, player = undefined) {
      if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
          gameSocket.send(JSON.stringify({ action, player }));
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


  function displayWaitingMessage(message, dots) {
    if (!window.ctx || !window.canvas) {
        console.error("displayWaitingMessage : ctx ou canvas est undefined.");
        return;
    }

    window.ctx.clearRect(0, 0, window.canvas.width, window.canvas.height);
    window.ctx.font = "20px Arial";
    window.ctx.fillStyle = "white";
    const textMetrics = window.ctx.measureText(message);
    const textWidth = textMetrics.width;
    let x_pos = (window.canvas.width / 2) - (textWidth / 2);
    window.ctx.fillText(message, x_pos, window.canvas.height / 2);

    for (let i = 0; i <= dots; ++i) {
        window.ctx.fillText(".", x_pos + textWidth + (i * 10), window.canvas.height / 2);
    }
  }

};


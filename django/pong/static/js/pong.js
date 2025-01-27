let canvas, ctx;
let lobbySocket = null;
let gameSocket = null;
let game_running = false;
let key_pressed = {};
let host = ""

const ball = { x: 0, y: 0, radius: 5 };
const player = { x: 0, y: 0, hp: 5 };
const opponent = { x: 0, y: 0, hp: 5 };

window.initPong = function () {
    console.log("Initialisation du jeu Pong...");
    setupCanvas();
    connectToLobby();
};

function setupCanvas() {
    canvas = document.getElementById('pong');
    if (!canvas) {
        console.error("Canvas non trouvé !");
        return;
    }
    ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "20px Arial";
    ctx.fillText("Connexion au lobby en cours...", canvas.width / 2 - 100, canvas.height / 2);   
}

function connectToLobby() {
	host = window.location.hostname;
    lobbySocket = new WebSocket(`ws://${host}:8000/ws/matchmaking/`);

    lobbySocket.onopen = () => {
        console.log("Connexion au lobby établie.");
		//?? Here I have to developp the message to tell the llobby either to add me to  the waiting queue or ton launch an AI bot and launch a game with it 
        //?? For this, i meed to get the query part of the url that lead me here, can window.location helps ?
		// Try :
		const queryString = window.location.search;
        const params = new URLSearchParams(queryString);
        const mode = params.get("mode");
		console.log(mode);
		console.log(mode);
		lobbySocket.send(JSON.stringify({ action: "find_game", mode: mode }));
    };

    lobbySocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "game_found") {
            console.log(`Partie trouvée : ${data.game_id}`);
            lobbySocket.close();
            connectToGame(data.game_id, data.role);
        } else if (data.type === "waiting") {
            displayWaitingMessage(data.message || "En attente d'un adversaire...");
        }
    };

    lobbySocket.onclose = () => {
        console.log("Connexion au lobby fermée.");
    };

    lobbySocket.onerror = (error) => {
        console.error("Erreur lors de la connexion au lobby :", error);
    };
}

function displayWaitingMessage(message) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "20px Arial";
    ctx.fillText(message, canvas.width / 2 - 100, canvas.height / 2);
}

function connectToGame(gameId, role) {
    gameSocket = new WebSocket(`ws://${host}:8000/ws/game/${gameId}/?player_id=${role}`);

    gameSocket.onopen = () => {
        console.log(`Connecté à la partie : ${gameId}, rôle : ${role}`);
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
	player_tmp = (role == "player1" ? data.player1_state : data.player2_state);
	opponent_tmp = (role == "player1" ? data.player2_state : data.player1_state);
    if (data.type === "position_update") {
        ball.x = data.ball_position.x;
        ball.y = data.ball_position.y;
        player.x = player_tmp.x;
        player.y = player_tmp.y;
        player.hp = player_tmp.lifepoints;
        opponent.x = opponent_tmp.x;
        opponent.y = opponent_tmp.y;
        opponent.hp = opponent_tmp.lifepoints;
        updateCanvas();
    } else if (data.type === "game_over") {
        alert(data.message);
        game_running = false;
    }
}

function initializeGameControls() {
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);
    console.log("Écouteurs d'événements ajoutés.");
}

function destroyGameControls() {
    document.removeEventListener('keydown', onKeyDown);
    document.removeEventListener('keyup', onKeyUp);
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
    ctx.font = "20px Arial";
    ctx.fillText("hp:", 10, 20);
    for (let i = 0; i < player.hp; ++i) {
        drawHeart(50 + i * 15, 10, 10);
    }
    ctx.fillStyle = "blue";
    ctx.fillRect(player.x, player.y, 10, 70);
}

function drawOpponent() {
    ctx.font = "20px Arial";
    ctx.fillText("hp:", canvas.width - 115, 20);
    for (let i = 0; i < opponent.hp; ++i) {
        drawHeart(canvas.width - (5 - i) * 15, 10, 10);
    }
    ctx.fillStyle = "red";
    ctx.fillRect(opponent.x, opponent.y, 10, 70);
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

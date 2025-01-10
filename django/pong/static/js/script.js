const canvas = document.getElementById('pong');
const ctx = canvas.getContext('2d');

// Dimensions et position initiale de la barre
const barWidth = 10;
const barHeight = 100;

let game_running = false;

const ball = {
    x: 0,
    y: 0,
    radius: 10
};

const key_pressed = {};

const player = {
    x: 0,
    y: 0,
	hp: 0
};

const opponent = {
    x: 0,
    y: 0,
	hp: 0
};

let isResetting = false; // Flag pour éviter des conflits pendant la réinitialisation
let paused = false;
// Propriétés de la balle

socket = new WebSocket('ws://localhost:8000/ws/game/1/?player_id=player1');

socket.onopen = function(event) {
	console.log("WebSocket connection established.");
};

window.addEventListener('beforeunload', function() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
});

socket.onmessage = function(event) {
	const data = JSON.parse(event.data);
	if (data.type === "position_update") {
		ball.x = data.ball_position.x;
		ball.y = data.ball_position.y;
		player.x = data.player_state.x;
		player.y = data.player_state.y;
		player.hp = data.player_state.lifepoints;
		opponent.x = data.opponent_state.x;
		opponent.y = data.opponent_state.y;
		opponent.hp = data.opponent_state.lifepoints;
		updateCanvas();
	} else if (data.type === "game_over") {
        alert(data.message);
        game_running = false;
    }
};

function drawPlayer() {
	ctx.font = "20px Arial";
	ctx.fillText("hp: ", 10, 20);
	for (i = 0; i < player.hp; ++i) {
		drawHeart (50 + (i * 15), 10, 10);
	}
    ctx.beginPath();
    ctx.rect(player.x, player.y, barWidth, barHeight); // Barre sur la gauche
    ctx.fillStyle = 'white';
    ctx.fill();
    ctx.closePath();
}

function drawOpponent() {
	ctx.font = "20px Arial";
	ctx.fillText("hp: ", canvas.width - 115, 20);
	for (i = 0; i < opponent.hp; ++i) {
		x = canvas.width - ((5 - i) * 15) 
		drawHeart (x, 10, 10);
	}
    ctx.beginPath();
    ctx.rect(opponent.x, opponent.y, barWidth, barHeight); // Barre sur la gauche
    ctx.fillStyle = 'white';
    ctx.fill();
    ctx.closePath();
}

function drawBall() {
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'white';
    ctx.fill();
    ctx.closePath();
}

function drawHeart(x, y, size) {
    ctx.beginPath();    
    ctx.moveTo(x, y);
    ctx.bezierCurveTo(
        x - size / 2, y - size / 2,
        x - size, y + size / 3,
        x, y + size
    );

    ctx.bezierCurveTo(
        x + size, y + size / 3,
        x + size / 2, y - size / 2,
        x, y
    );

    ctx.closePath();
    ctx.fillStyle = 'red';
    ctx.fill();
}

function updateCanvas() {
	// console.log("Player state:", player);
    // console.log("Opponent state:", opponent);
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Effacer le canvas\
    drawBall();
    drawPlayer();
	drawOpponent();
}

function sendAction(action) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log(`Envoi de l'action : ${action}`);
        socket.send(JSON.stringify({ action: action }));
    } else {
        console.error("WebSocket non ouvert !");
    }
}

// Websocket version
// Envoyer une action joueur
document.addEventListener('keydown', function(event) {
	if (!key_pressed[event.key]) {
		if (!game_running)
			return;
		console.log("Key pressed :" + event.key);
		key_pressed[event.key] = true;
		if (event.key === "ArrowUp") {
			sendAction("move_up");
		}
		if (event.key === "ArrowDown") {
			sendAction("move_down");
		}
		if (event.key === "Escape") {
			sendAction("pause_game");
		}
	}
});

document.addEventListener('keyup', function(event) {
	delete key_pressed[event.key];
	if (!game_running)
		return;
	if (event.key === "ArrowUp") {
		sendAction("stop_move_up");
	}
	if (event.key === "ArrowDown") {
		sendAction("stop_move_down");
	}
});

function resetGame() {
    if (socket && socket.readyState === WebSocket.OPEN)
		sendAction("reset_game");
}

function pauseGame() {
    if (socket && socket.readyState === WebSocket.OPEN)
		sendAction("pause_game");
}

function startGame() {
	game_running = true;
	const message = {
		action: "start_game",
		mode: "solo",
		width: canvas.width,
		height: canvas.height
	};
	// Envoyer le message au serveur
	socket.send(JSON.stringify(message));
}

// Gérer le bouton de réinitialisation
const resetButton = document.getElementById('reset-button');
resetButton.addEventListener('click', resetGame);

const launchButton = document.getElementById('launch-button');
launchButton.addEventListener('click', startGame);

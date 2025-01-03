const canvas = document.getElementById('pong');
const ctx = canvas.getContext('2d');

// Dimensions et position initiale de la barre
const barWidth = 10;
const barHeight = 60;

const ball = {
    x: 0,
    y: 0,
    radius: 10
};

const player = {
    x: 0,
    y: 0 
};

let socket = null;

let isResetting = false; // Flag pour éviter des conflits pendant la réinitialisation
let paused = false;
// Propriétés de la balle

// Dessiner la barre
function drawBar() {
    ctx.beginPath();
    ctx.rect(player.x, player.y, barWidth, barHeight); // Barre sur la gauche
    ctx.fillStyle = 'white';
    ctx.fill();
    ctx.closePath();
}

// Dessiner la balle
function drawBall() {
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'white';
    ctx.fill();
    ctx.closePath();
}

// Mettre à jour le canvas
function updateCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Effacer le canvas
    drawBall();
    drawBar();
}

//Websocket version
// Envoyer une action joueur
document.addEventListener('keydown', function(event) {
    if (event.key === "ArrowUp") {
        socket.send(JSON.stringify({ action: "move_up" }));
    }
    if (event.key === "ArrowDown") {
        socket.send(JSON.stringify({ action: "move_down" }));
    }
});


function resetGame() {
    if (socket && socket.readyState === WebSocket.OPEN)
		socket.send(JSON.stringify({ action: "reset_game" }))
}

function pauseGame() {
    fetch('/pause_game/').catch(error => {
        console.error('Erreur reseau :', error);
    });
    paused = !paused;
    if (!paused) {
        requestAnimationFrame(update);
    }
}

function startGame() {
    socket = new WebSocket('ws://localhost:8000/ws/game/1/');

    socket.onopen = function(event) {
        const message = {
            action: "start_game",
            width: canvas.width,
            height: canvas.height
        };
        // Envoyer le message au serveur
        socket.send(JSON.stringify(message));
		console.log("WebSocket connection established.");
    };
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === "position_update") {
            ball.x = data.ball_position.x;
            ball.y = data.ball_position.y;
            player.x = data.player_position.x;
            player.y = data.player_position.y;
        }
		updateCanvas();
    };
}


// Gérer le bouton de réinitialisation
const resetButton = document.getElementById('reset-button');
resetButton.addEventListener('click', resetGame);

const launchButton = document.getElementById('launch-button');
launchButton.addEventListener('click', startGame);

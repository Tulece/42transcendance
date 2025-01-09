// pong.js
(function() {

	let canvas, ctx;
	let socket = null;
	let game_running = false;
	let key_pressed = {};

	const ball = { x: 0, y: 0, radius: 10 };
	const player = { x: 0, y: 0, hp: 0 };
	const opponent = { x: 0, y: 0, hp: 0 };

	// Exposer en global (sans ES module)
	window.initPong = function() {
	  console.log("initPong() called");

	  canvas = document.getElementById('pong');
	  if (!canvas) {
		console.error("Canvas not found!");
		return;
	  }
	  ctx = canvas.getContext('2d');

	  // WebSocket
	  socket = new WebSocket('ws://localhost:8000/ws/game/1/?player_id=player1');
	  socket.onopen = () => {
		console.log("WebSocket connection established.");
	  };
	  socket.onmessage = (event) => {
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

	  document.addEventListener('keydown', onKeyDown);
	  document.addEventListener('keyup', onKeyUp);

	  const resetButton = document.getElementById('reset-button');
	  if (resetButton) {
		resetButton.addEventListener('click', resetGame);
	  }

	  const launchButton = document.getElementById('launch-button');
	  if (launchButton) {
		launchButton.addEventListener('click', startGame);
	  }
	}

	window.destroyPong = function() {
	  console.log("destroyPong() called");
	  // fermer la socket
	  if (socket && socket.readyState === WebSocket.OPEN) {
		socket.send(JSON.stringify({ action: "quit_game" }));
		socket.close();
	  }
	  socket = null;

	  // enlever events
	  document.removeEventListener('keydown', onKeyDown);
	  document.removeEventListener('keyup', onKeyUp);
	  const resetButton = document.getElementById('reset-button');
	  if (resetButton) {
		resetButton.removeEventListener('click', resetGame);
	  }
	  const launchButton = document.getElementById('launch-button');
	  if (launchButton) {
		launchButton.removeEventListener('click', startGame);
	  }

	  // reset variables
	  key_pressed = {};
	  game_running = false;
	}

	function onKeyDown(e) {
	  if (!key_pressed[e.key]) {
		if (!game_running) return;
		key_pressed[e.key] = true;
		if (e.key === "ArrowUp") {
		  sendAction("move_up");
		}
		if (e.key === "ArrowDown") {
		  sendAction("move_down");
		}
		if (e.key === "Escape") {
		  sendAction("pause_game");
		}
	  }
	}

	function onKeyUp(e) {
	  delete key_pressed[e.key];
	  if (!game_running) return;
	  if (e.key === "ArrowUp") {
		sendAction("stop_move_up");
	  }
	  if (e.key === "ArrowDown") {
		sendAction("stop_move_down");
	  }
	}

	function sendAction(action) {
	  if (socket && socket.readyState === WebSocket.OPEN) {
		socket.send(JSON.stringify({ action }));
	  } else {
		console.error("WebSocket not open!");
	  }
	}

	function resetGame() {
	  if (socket && socket.readyState === WebSocket.OPEN) {
		sendAction("reset_game");
	  }
	}

	function startGame() {
	  game_running = true;
	  if (socket && socket.readyState === WebSocket.OPEN) {
		socket.send(JSON.stringify({
		  action: "start_game",
		  width: canvas.width,
		  height: canvas.height
		}));
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
	  ctx.fillText("hp: ", 10, 20);
	  for (let i = 0; i < player.hp; ++i) {
		drawHeart(50 + (i * 15), 10, 10);
	  }
	  ctx.beginPath();
	  ctx.rect(player.x, player.y, 10, 100);
	  ctx.fillStyle = 'white';
	  ctx.fill();
	  ctx.closePath();
	}

	function drawOpponent() {
	  ctx.font = "20px Arial";
	  ctx.fillText("hp: ", canvas.width - 115, 20);
	  for (let i = 0; i < opponent.hp; ++i) {
		let x = canvas.width - ((5 - i) * 15);
		drawHeart(x, 10, 10);
	  }
	  ctx.beginPath();
	  ctx.rect(opponent.x, opponent.y, 10, 100);
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

  })();

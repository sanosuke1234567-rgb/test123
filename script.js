const board = document.getElementById("board");
const ctx = board.getContext("2d");
const scoreEl = document.getElementById("score");
const bestEl = document.getElementById("best");
const toggleBtn = document.getElementById("toggle");
const restartBtn = document.getElementById("restart");
const statusEl = document.getElementById("status");

const gridSize = 20;
const cellCount = board.width / gridSize;
const speedLevels = [170, 150, 130, 110, 95, 85];
const storageKey = "snake-best-score";

let snake;
let direction;
let pendingDirection;
let food;
let score;
let bestScore = 0;
let gameLoopId;
let isRunning = false;
let isGameOver = false;

const drawRoundedRect = (x, y, size, color) => {
  const radius = 6;
  ctx.fillStyle = color;
  ctx.beginPath();

  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, size, size, radius);
  } else {
    const right = x + size;
    const bottom = y + size;
    ctx.moveTo(x + radius, y);
    ctx.lineTo(right - radius, y);
    ctx.quadraticCurveTo(right, y, right, y + radius);
    ctx.lineTo(right, bottom - radius);
    ctx.quadraticCurveTo(right, bottom, right - radius, bottom);
    ctx.lineTo(x + radius, bottom);
    ctx.quadraticCurveTo(x, bottom, x, bottom - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
  }

  ctx.fill();
};

const resetGame = () => {
  snake = [
    { x: 8, y: 10 },
    { x: 7, y: 10 },
    { x: 6, y: 10 },
  ];
  direction = { x: 1, y: 0 };
  pendingDirection = direction;
  score = 0;
  isGameOver = false;
  spawnFood();
  updateScore();
  statusEl.textContent = "等待开始";
};

const updateScore = () => {
  scoreEl.textContent = score;
  bestEl.textContent = bestScore;
};

const spawnFood = () => {
  let position;
  do {
    position = {
      x: Math.floor(Math.random() * cellCount),
      y: Math.floor(Math.random() * cellCount),
    };
  } while (snake.some((segment) => segment.x === position.x && segment.y === position.y));
  food = position;
};

const setDirection = (next) => {
  if (!isRunning && !isGameOver) {
    startGame();
  }
  if (next.x + direction.x === 0 && next.y + direction.y === 0) {
    return;
  }
  pendingDirection = next;
};

const handleKeydown = (event) => {
  switch (event.key) {
    case "ArrowUp":
      setDirection({ x: 0, y: -1 });
      break;
    case "ArrowDown":
      setDirection({ x: 0, y: 1 });
      break;
    case "ArrowLeft":
      setDirection({ x: -1, y: 0 });
      break;
    case "ArrowRight":
      setDirection({ x: 1, y: 0 });
      break;
    case " ":
      toggleGame();
      break;
    case "r":
    case "R":
      restartGame();
      break;
    default:
      break;
  }
};

const update = () => {
  direction = pendingDirection;
  const nextHead = {
    x: snake[0].x + direction.x,
    y: snake[0].y + direction.y,
  };

  const hitWall =
    nextHead.x < 0 ||
    nextHead.y < 0 ||
    nextHead.x >= cellCount ||
    nextHead.y >= cellCount;
  const hitSelf = snake.some((segment) => segment.x === nextHead.x && segment.y === nextHead.y);

  if (hitWall || hitSelf) {
    gameOver();
    return;
  }

  snake.unshift(nextHead);

  if (nextHead.x === food.x && nextHead.y === food.y) {
    score += 10;
    if (score > bestScore) {
      bestScore = score;
      localStorage.setItem(storageKey, bestScore.toString());
    }
    spawnFood();
    updateScore();
  } else {
    snake.pop();
  }

  draw();
};

const drawGrid = () => {
  ctx.strokeStyle = "#1d2235";
  ctx.lineWidth = 1;

  for (let i = 0; i <= cellCount; i += 1) {
    const pos = i * gridSize;
    ctx.beginPath();
    ctx.moveTo(pos, 0);
    ctx.lineTo(pos, board.height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, pos);
    ctx.lineTo(board.width, pos);
    ctx.stroke();
  }
};

const draw = () => {
  ctx.clearRect(0, 0, board.width, board.height);
  ctx.fillStyle = "#151924";
  ctx.fillRect(0, 0, board.width, board.height);
  drawGrid();

  drawRoundedRect(food.x * gridSize + 2, food.y * gridSize + 2, gridSize - 4, "#ff7a90");

  snake.forEach((segment, index) => {
    const color = index === 0 ? "#7bffb0" : "#2ed573";
    drawRoundedRect(segment.x * gridSize + 2, segment.y * gridSize + 2, gridSize - 4, color);
  });
};

const startGame = () => {
  if (isRunning || isGameOver) {
    return;
  }
  isRunning = true;
  statusEl.textContent = "游戏进行中";
  toggleBtn.textContent = "暂停";
  runLoop();
};

const pauseGame = () => {
  isRunning = false;
  toggleBtn.textContent = "继续";
  statusEl.textContent = "已暂停";
  clearTimeout(gameLoopId);
};

const toggleGame = () => {
  if (isGameOver) {
    restartGame();
    return;
  }
  if (isRunning) {
    pauseGame();
  } else {
    startGame();
  }
};

const gameOver = () => {
  isGameOver = true;
  isRunning = false;
  toggleBtn.textContent = "重新开始";
  statusEl.textContent = "游戏结束";
  clearTimeout(gameLoopId);
  draw();
};

const restartGame = () => {
  clearTimeout(gameLoopId);
  resetGame();
  draw();
  if (isRunning) {
    startGame();
  }
};

const runLoop = () => {
  if (!isRunning) {
    return;
  }
  update();
  const speedIndex = Math.min(Math.floor(score / 50), speedLevels.length - 1);
  const delay = speedLevels[speedIndex];
  gameLoopId = setTimeout(runLoop, delay);
};

const initialize = () => {
  const storedBest = Number.parseInt(localStorage.getItem(storageKey) || "0", 10);
  bestScore = Number.isNaN(storedBest) ? 0 : storedBest;
  resetGame();
  draw();
  toggleBtn.addEventListener("click", toggleGame);
  restartBtn.addEventListener("click", restartGame);
  window.addEventListener("keydown", handleKeydown);
};

initialize();

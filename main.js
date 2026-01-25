const COLS = 10;
const ROWS = 20;
const BLOCK = 30;

const SHAPES = {
  I: [
    [0, 0, 0, 0],
    [1, 1, 1, 1],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ],
  J: [
    [1, 0, 0],
    [1, 1, 1],
    [0, 0, 0],
  ],
  L: [
    [0, 0, 1],
    [1, 1, 1],
    [0, 0, 0],
  ],
  O: [
    [1, 1],
    [1, 1],
  ],
  S: [
    [0, 1, 1],
    [1, 1, 0],
    [0, 0, 0],
  ],
  T: [
    [0, 1, 0],
    [1, 1, 1],
    [0, 0, 0],
  ],
  Z: [
    [1, 1, 0],
    [0, 1, 1],
    [0, 0, 0],
  ],
};

const COLORS = {
  I: "#62d4ff",
  J: "#5f7dff",
  L: "#ffb04f",
  O: "#ffd95c",
  S: "#6dd56b",
  T: "#c573ff",
  Z: "#ff6b6b",
};

const boardCanvas = document.getElementById("board");
const nextCanvas = document.getElementById("next");
const scoreEl = document.getElementById("score");
const linesEl = document.getElementById("lines");
const boardCtx = boardCanvas.getContext("2d");
const nextCtx = nextCanvas.getContext("2d");

boardCanvas.width = COLS * BLOCK;
boardCanvas.height = ROWS * BLOCK;

let board = createMatrix(ROWS, COLS);
let current = null;
let next = generatePiece();
let score = 0;
let lines = 0;
let dropCounter = 0;
let lastTime = 0;
let dropInterval = 800;
let fastDrop = false;
let swapUsed = false;
let clearFlash = 0;

function createMatrix(rows, cols) {
  return Array.from({ length: rows }, () => Array(cols).fill(0));
}

function generatePiece() {
  const keys = Object.keys(SHAPES);
  const type = keys[Math.floor(Math.random() * keys.length)];
  return {
    type,
    shape: SHAPES[type].map((row) => row.slice()),
    color: COLORS[type],
    pos: { x: 0, y: 0 },
  };
}

function spawnPiece() {
  current = next;
  current.pos.y = 0;
  current.pos.x = Math.floor((COLS - current.shape[0].length) / 2);
  next = generatePiece();
  swapUsed = false;
  if (collide(board, current)) {
    board = createMatrix(ROWS, COLS);
    score = 0;
    lines = 0;
  }
}

function rotate(matrix) {
  return matrix[0].map((_, i) => matrix.map((row) => row[i]).reverse());
}

function collide(matrix, piece) {
  for (let y = 0; y < piece.shape.length; y += 1) {
    for (let x = 0; x < piece.shape[y].length; x += 1) {
      if (piece.shape[y][x]) {
        const newY = y + piece.pos.y;
        const newX = x + piece.pos.x;
        if (
          newY >= ROWS ||
          newX < 0 ||
          newX >= COLS ||
          matrix[newY][newX]
        ) {
          return true;
        }
      }
    }
  }
  return false;
}

function merge(matrix, piece) {
  piece.shape.forEach((row, y) => {
    row.forEach((value, x) => {
      if (value) {
        matrix[y + piece.pos.y][x + piece.pos.x] = piece.color;
      }
    });
  });
}

function clearLines() {
  let cleared = 0;
  outer: for (let y = ROWS - 1; y >= 0; y -= 1) {
    for (let x = 0; x < COLS; x += 1) {
      if (!board[y][x]) {
        continue outer;
      }
    }
    const row = board.splice(y, 1)[0].fill(0);
    board.unshift(row);
    cleared += 1;
    y += 1;
  }

  if (cleared > 0) {
    const points = [0, 100, 300, 500, 800][cleared] || cleared * 200;
    score += points;
    lines += cleared;
    clearFlash = 8;
    boardCanvas.classList.remove("flash");
    void boardCanvas.offsetWidth;
    boardCanvas.classList.add("flash");
  }
}

function drawCell(ctx, x, y, color, size = BLOCK) {
  ctx.fillStyle = color;
  ctx.fillRect(x * size, y * size, size, size);
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.strokeRect(x * size, y * size, size, size);
}

function drawMatrix(ctx, matrix, offset, size = BLOCK) {
  matrix.forEach((row, y) => {
    row.forEach((value, x) => {
      if (value) {
        drawCell(ctx, x + offset.x, y + offset.y, value, size);
      }
    });
  });
}

function drawBoard() {
  boardCtx.clearRect(0, 0, boardCanvas.width, boardCanvas.height);
  drawMatrix(boardCtx, board, { x: 0, y: 0 });
  if (current) {
    drawMatrix(boardCtx, current.shape.map((row) => row.map((v) => (v ? current.color : 0))), current.pos);
  }
  if (clearFlash > 0) {
    boardCtx.fillStyle = `rgba(255,255,255,${0.08 * clearFlash})`;
    boardCtx.fillRect(0, 0, boardCanvas.width, boardCanvas.height);
    clearFlash -= 1;
  }
}

function drawNext() {
  nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
  const size = 24;
  const shape = next.shape;
  const offsetX = Math.floor((nextCanvas.width / size - shape[0].length) / 2);
  const offsetY = Math.floor((nextCanvas.height / size - shape.length) / 2);
  shape.forEach((row, y) => {
    row.forEach((value, x) => {
      if (value) {
        drawCell(nextCtx, x + offsetX, y + offsetY, next.color, size);
      }
    });
  });
}

function drop() {
  current.pos.y += 1;
  if (collide(board, current)) {
    current.pos.y -= 1;
    merge(board, current);
    clearLines();
    spawnPiece();
  }
  dropCounter = 0;
}

function update(time = 0) {
  const deltaTime = time - lastTime;
  lastTime = time;
  dropCounter += deltaTime;
  const interval = fastDrop ? 50 : dropInterval;
  if (dropCounter > interval) {
    drop();
  }
  drawBoard();
  drawNext();
  scoreEl.textContent = score;
  linesEl.textContent = lines;
  requestAnimationFrame(update);
}

function move(offset) {
  current.pos.x += offset;
  if (collide(board, current)) {
    current.pos.x -= offset;
  }
}

function hardRotate() {
  const rotated = rotate(current.shape);
  const oldX = current.pos.x;
  let offset = 1;
  current.shape = rotated;
  while (collide(board, current)) {
    current.pos.x += offset;
    offset = -(offset + (offset > 0 ? 1 : -1));
    if (Math.abs(offset) > current.shape[0].length) {
      current.shape = rotate(rotate(rotate(rotated)));
      current.pos.x = oldX;
      return;
    }
  }
}

function swapWithNext() {
  if (swapUsed) return;
  const temp = current;
  current = next;
  next = temp;
  current.pos = { x: Math.floor((COLS - current.shape[0].length) / 2), y: 0 };
  swapUsed = true;
  if (collide(board, current)) {
    current = temp;
    next = generatePiece();
    swapUsed = true;
  }
}

document.addEventListener("keydown", (event) => {
  if (!current) return;
  switch (event.key) {
    case "ArrowLeft":
      move(-1);
      break;
    case "ArrowRight":
      move(1);
      break;
    case "ArrowDown":
      fastDrop = true;
      break;
    case "ArrowUp":
      hardRotate();
      break;
    case " ":
      while (!collide(board, current)) {
        current.pos.y += 1;
      }
      current.pos.y -= 1;
      merge(board, current);
      clearLines();
      spawnPiece();
      break;
    case "c":
    case "C":
      swapWithNext();
      break;
    default:
      break;
  }
});

document.addEventListener("keyup", (event) => {
  if (event.key === "ArrowDown") {
    fastDrop = false;
  }
});

spawnPiece();
update();

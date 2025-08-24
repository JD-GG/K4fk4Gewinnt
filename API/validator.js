const WebSocket = require("ws");

const PORT = 14314;

// --- SERVER STATE ---
let currentBoard = Array.from({ length: 6 }, () => Array(7).fill(0));
let currentPlayer = 1;

// --- WINNER STATE ---
function check_winner(board, player) {
  // Horizontal
  for (let r = 0; r < 6; r++) {
    for (let c = 0; c < 4; c++) {
      if (
        board[r][c] === player &&
        board[r][c + 1] === player &&
        board[r][c + 2] === player &&
        board[r][c + 3] === player
      ) return true;
    }
  }
  // Vertikal
  for (let c = 0; c < 7; c++) {
    for (let r = 0; r < 3; r++) {
      if (
        board[r][c] === player &&
        board[r + 1][c] === player &&
        board[r + 2][c] === player &&
        board[r + 3][c] === player
      ) return true;
    }
  }
  // Diagonal /
  for (let r = 3; r < 6; r++) {
    for (let c = 0; c < 4; c++) {
      if (
        board[r][c] === player &&
        board[r - 1][c + 1] === player &&
        board[r - 2][c + 2] === player &&
        board[r - 3][c + 3] === player
      ) return true;
    }
  }
  // Diagonal \
  for (let r = 3; r < 6; r++) {
    for (let c = 3; c < 7; c++) {
      if (
        board[r][c] === player &&
        board[r - 1][c - 1] === player &&
        board[r - 2][c - 2] === player &&
        board[r - 3][c - 3] === player
      ) return true;
    }
  }
  return false;
}

function reset_game() {
  currentBoard = Array.from({ length: 6 }, () => Array(7).fill(0));
  currentPlayer = 1;
}

// --- HELPERS ---
function dropDisc(column, player) {
  for (let row = 5; row >= 0; row--) {
    if (currentBoard[row][column] === 0) {
      currentBoard[row][column] = player;
      return true;
    }
  }
  return false; // Spalte voll
}

function broadcastBoard() {
  const msg = JSON.stringify({ board: currentBoard, yourTurn: currentPlayer });
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(msg);
    }
  });
}

// --- WEBSOCKET SERVER ---
const wss = new WebSocket.Server({ port: PORT }, () => {
  console.log(`WebSocket Server läuft auf Port ${PORT}`);
});

// --- HANDLE MESSAGES ---
wss.on("connection", (ws) => {
  ws.send(JSON.stringify({ board: currentBoard, yourTurn: currentPlayer }));

  ws.on("message", (msg) => {
    try {
      const data = JSON.parse(msg);
      if (typeof data.column === "number" && data.player === currentPlayer) {
        if (dropDisc(data.column, currentPlayer)) {
          // Gewinner-Check
          if (check_winner(currentBoard, currentPlayer)) {
            broadcastBoard();
            wss.clients.forEach((client) => {
              if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({
                  winner: currentPlayer,
                  board: currentBoard
                }));
              }
            });
            setTimeout(() => {
              reset_game();
              broadcastBoard();
            }, 3000); // 3 Sekunden warten, dann neues Spiel
            return;
          }
          currentPlayer = currentPlayer === 1 ? 2 : 1;
          broadcastBoard();
        } else {
          ws.send(JSON.stringify({ error: "Spalte voll", board: currentBoard, yourTurn: currentPlayer }));
        }
      }
    } catch (e) {
      ws.send(JSON.stringify({ error: "Ungültige Nachricht" }));
    }
  });
});
const WebSocket = require("ws");

const PORT = 14314;

// --- SERVER STATE ---
let currentBoard = Array.from({ length: 6 }, () => Array(7).fill(0));
let currentPlayer = 1;

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
  // Sende initiales Board
  ws.send(JSON.stringify({ board: currentBoard, yourTurn: currentPlayer }));

  ws.on("message", (msg) => {
    try {
      const data = JSON.parse(msg);
      if (typeof data.column === "number" && data.player === currentPlayer) {
        if (dropDisc(data.column, currentPlayer)) {
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
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

// --- WEBSOCKET SERVER ---
const activeLobbies = {}; 
/*
activeLobbies = {
  14315: {
      board: [...],           // 6x7 Board
      currentPlayer: 1,       // aktuell am Zug
      clients: []             // verbundenen WebSocket Clients
  }
}
*/

const mainWss = new WebSocket.Server({ port: PORT }, () => {
  console.log(`WebSocket Server läuft auf Port ${PORT}`);
});

mainWss.on("connection", (ws) => {
  ws.on("message", (msg) => {
    try {
      const data = JSON.parse(msg);
      if (typeof data.Lobby !== "number") throw new Error("Ungültige Lobby-ID");

      // --- LOBBY ERSTELLEN ---
      if (data.Lobby === 0) {
        let lobbyPort = 0;
        for (let i = 1; i <= 4; i++) {
          const candidatePort = PORT + i;
          if (!activeLobbies[candidatePort]) {
            lobbyPort = candidatePort;
            break;
          }
        }
        if (!lobbyPort) {
          ws.send(JSON.stringify({ error: "Keine freien Lobby-Ports verfügbar" }));
          return;
        }

        const lobbyWss = new WebSocket.Server({ port: lobbyPort }, () => {
          console.log(`Lobby WebSocket Server läuft auf Port ${lobbyPort}`);

          // Lobby initialisieren
          activeLobbies[lobbyPort] = {
            board: Array.from({ length: 6 }, () => Array(7).fill(0)),
            currentPlayer: 1,
            clients: []
          };

          ws.send(JSON.stringify({ port: lobbyPort }));
        });

        lobbyWss.on("connection", (clientWs) => handleLobbyConnection(lobbyPort, clientWs));

        // Lobby Cleanup
        lobbyWss.on("close", () => delete activeLobbies[lobbyPort]);
        lobbyWss.kill = () => lobbyWss.close();

      } 
      // --- LOBBY JOINEN ---
      else {
        const joinPort = PORT + data.Lobby;
        if (!activeLobbies[joinPort]) {
          ws.send(JSON.stringify({ error: "Lobby existiert nicht" }));
        } else {
          ws.send(JSON.stringify({ port: joinPort }));
        }
      }

    } catch (e) {
      ws.send(JSON.stringify({ error: "Ungültige Nachricht" }));
    }
  });
});

function handleLobbyConnection(lobbyPort, ws) {
  const lobby = activeLobbies[lobbyPort];
  
  // Spieler-ID zuweisen
  ws.playerID = lobby.clients.length + 1;
  lobby.clients.push(ws);

  // Aktuelles Board + Turn senden
  ws.send(JSON.stringify({ 
    board: lobby.board, 
    yourTurn: ws.playerID === lobby.currentPlayer 
  }));

  ws.on("message", (msg) => {
    try {
      const data = JSON.parse(msg);

      if (typeof data.column === "number" && data.player === lobby.currentPlayer) {

        // Disc setzen
        if (!dropDiscLobby(lobby, data.column, data.player)) {
          ws.send(JSON.stringify({ error: "Spalte voll", board: lobby.board, yourTurn: true }));
          return;
        }

        // Gewinner prüfen für den Spieler, der gezogen hat
        if (check_winner(lobby.board, data.player)) {
          // Gewinner broadcasten
          lobby.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
              client.send(JSON.stringify({ 
                board: lobby.board,
                winner: data.player,
                yourTurn: false // Spiel ist vorbei
              }));
            }
          });

          // Reset nach kurzer Zeit
          setTimeout(() => {
            resetLobby(lobby);
            broadcastLobby(lobby);
          }, 3000);
          return;
        }

        // Spieler wechseln
        lobby.currentPlayer = lobby.currentPlayer === 1 ? 2 : 1;

        // Broadcast für alle Spieler, Turn korrekt setzen
        broadcastLobby(lobby);

      }
    } catch (e) {
      ws.send(JSON.stringify({ error: "Ungültige Nachricht" }));
    }
  });

  ws.on("close", () => {
    lobby.clients = lobby.clients.filter(c => c !== ws);
  });
}

function broadcastLobby(lobby) {
  // Jeder Spieler bekommt aktuelle Board-Ansicht und Turn
  lobby.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({
        board: lobby.board,
        yourTurn: client.playerID === lobby.currentPlayer
      }));
    }
  });
}

function dropDiscLobby(lobby, column, player) {
  for (let row = 5; row >= 0; row--) {
    if (lobby.board[row][column] === 0) {
      lobby.board[row][column] = player;
      return true;
    }
  }
  return false;
}

function resetLobby(lobby) {
  lobby.board = Array.from({ length: 6 }, () => Array(7).fill(0));
  lobby.currentPlayer = 1;
}


// --- HANDLE LOBBY MESSAGES ---
/*
lobbyWss.on("connection", (ws) => {
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
});*/

const shutdown = async () => {
  console.log('🛑 Shutting down API service...');

  try {
    await writeApi.close();
    console.log('✅ Influx write API closed.');
  } catch (e) {
    console.warn('⚠️ Error closing write API:', e.message);
  }

  process.exit(0);
};

process.on('SIGTERM', shutdown);
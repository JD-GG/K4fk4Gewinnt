const express = require("express");
const bodyParser = require("body-parser");
const { KafkaClient, Producer, Consumer } = require("kafka-node");
const WebSocket = require("ws");

// --- CONFIG ---
const PORT = 14314;
const KAFKA_HOST = "localhost:14314"; // Kafka Broker
const TOPIC = "viergewinnt-board";

// --- SERVER STATE ---
let currentBoard = Array.from({ length: 6 }, () => Array(7).fill(0));
let currentPlayer = 1;

// --- INIT EXPRESS ---
const app = express();
app.use(bodyParser.json());

// --- KAFKA SETUP ---
const client = new KafkaClient({ kafkaHost: KAFKA_HOST });
const producer = new Producer(client);
const consumer = new Consumer(
  client,
  [{ topic: TOPIC, partition: 0 }],
  { autoCommit: true }
);

// init board in Kafka if empty
producer.on("ready", () => {
  console.log("Kafka Producer ready.");
  publishBoard();
});

producer.on("error", (err) => console.error("Kafka Producer error:", err));

consumer.on("message", (msg) => {
  try {
    const data = JSON.parse(msg.value);
    currentBoard = data.board;
    currentPlayer = data.currentPlayer;
    broadcastBoard();
  } catch (err) {
    console.error("Kafka parse error:", err);
  }
});

// --- HELPERS ---
function publishBoard() {
  const payloads = [
    {
      topic: TOPIC,
      messages: JSON.stringify({ board: currentBoard, currentPlayer }),
    },
  ];
  producer.send(payloads, (err) => {
    if (err) console.error("Kafka publish error:", err);
  });
}

function dropDisc(column, player) {
  for (let row = 5; row >= 0; row--) {
    if (currentBoard[row][column] === 0) {
      currentBoard[row][column] = player;
      return true;
    }
  }
  return false; // Spalte voll
}

// --- REST API ---
app.post("/move", (req, res) => {
  const { column } = req.body;

  if (typeof column !== "number" || column < 0 || column > 6) {
    return res.json({ board: currentBoard, yourTurn: true, error: "Ungültige Spalte" });
  }

  if (!dropDisc(column, currentPlayer)) {
    return res.json({ board: currentBoard, yourTurn: true, error: "Spalte voll" });
  }

  // Spieler gewechselt
  currentPlayer = currentPlayer === 1 ? 2 : 1;

  publishBoard();

  return res.json({ board: currentBoard, yourTurn: false });
});

// --- WEBSOCKET ---
const server = app.listen(PORT, () => {
  console.log(`Validator läuft auf Port ${PORT}`);
});

const wss = new WebSocket.Server({ server });

function broadcastBoard() {
  const msg = JSON.stringify({ board: currentBoard, yourTurn: currentPlayer });
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(msg);
    }
  });
}

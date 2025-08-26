import websocket
import threading
import json
import os
import time
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
MAIN_WS_URL = os.getenv("WS_URL")  # z.B. ws://localhost:14314/ws
SCHEME, rest = MAIN_WS_URL.split("://")  # 'ws', 'localhost:14314/ws'
# /ws entfernen, falls vorhanden
rest = rest.split("/")[0]  # 'localhost:14314'
HOST, MAIN_PORT_STR = rest.split(":")  # HOST='localhost', MAIN_PORT_STR='14314'
PORT = int(MAIN_PORT_STR)              # PORT = 14314 als int
LOBBY = int(input("Lobby erstellen oder beitreten? (0 oder LobbyID): "))
PLAYER = None


# --- GLOBAL ---
current_board = [[0]*7 for _ in range(6)]
your_turn = False
ws = None
game_over = False
lobby_ws_url = None
lobby_id = None

# --- HELPER ---
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_board(board, lobby_id):
    symbols = {0: " ", 1: "O", 2: "X"}
    clear_console()
    print(f"Lobby-ID: {lobby_id}\n")
    print("    " + "   ".join(str(i) for i in range(7)))
    print("  ┌───" + "┬───" * 6 + "┐")
    for r, row in enumerate(board):
        print("  │ " + " │ ".join(symbols[cell] for cell in row) + " │")
        if r < len(board) - 1:
            print("  ├───" + "┼───" * 6 + "┤")
        else:
            print("  └───" + "┴───" * 6 + "┘")
    print()

    # Status nur anzeigen, wenn Spiel noch läuft
    if not game_over:
        if your_turn:
            print("👉 Dein Zug!")
        else:
            print("⏳ Warte auf den Zug des anderen Spielers...")

def send_move(column):
    global ws
    try:
        msg = json.dumps({"column": column, "player": PLAYER})
        ws.send(msg)
    except Exception as e:
        print(f"WebSocket send error: {e}")


# --- LOBBY HANDLING ---
def join_main_server():
    """Verbindet sich mit dem Hauptserver und holt Lobby-Infos."""
    main_ws = websocket.create_connection(MAIN_WS_URL)
    main_ws.send(json.dumps({"Lobby": LOBBY}))
    resp = main_ws.recv()
    data = json.loads(resp)
    main_ws.close()

    if "port" in data:
        port = data["port"]
        url = f"ws://{HOST}:{port}"  # kein /ws
        print(f"Verbinde mit Lobby auf {url}")
        return url
    else:
        print(f"Fehler: {data.get('error', 'unbekannt')}")
        return None

# --- GAME HANDLING ---
def on_message(ws_, message):
    global current_board, your_turn, game_over, PLAYER
    try:
        data = json.loads(message)
        print(f"[Client] Nachricht erhalten: {data}")  # LOGGING

        if "winner" in data:  # zuerst Sieger behandeln!
            current_board = data["board"]
            game_over = True
            render_board(current_board, lobby_id)
            if data["winner"] == PLAYER:
                print("\n🎉 DU HAST GEWONNEN! 🎉\n")
            else:
                print("\n😢 Leider verloren! 😢\n")
            again = input("Nochmal spielen? (j/n): ")
            if again.lower().startswith("j"):
                game_over = False
            else:
                os._exit(0)

        elif "draw" in data:  # --- Unentschieden korrekt prüfen ---
            current_board = data["board"]
            game_over = True
            render_board(current_board, lobby_id)
            print("\n🤝 Unentschieden! 🤝\n")
            again = input("Nochmal spielen? (j/n): ")
            if again.lower().startswith("j"):
                game_over = False
            else:
                os._exit(0)

        elif "board" in data:   # erst danach normales Board-Update
            current_board = data["board"]
            your_turn = data.get("yourTurn", False)
            if "playerID" in data:
                PLAYER = data["playerID"]
            render_board(current_board, lobby_id)
            game_over = False

        elif "error" in data:
            print(f"[Client] Fehler: {data['error']}")

    except Exception as e:
        print(f"[Client] WS parse error: {e}")

def on_error(ws_, error):
    print(f"WebSocket error: {error}")

def on_close(ws_, close_status_code, close_msg):
    print("WebSocket connection closed")

def ws_thread():
    global ws, lobby_ws_url
    ws = websocket.WebSocketApp(
        lobby_ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()


# --- MAIN LOOP ---
def main():
    global your_turn, game_over, lobby_ws_url, lobby_id
    print("Vier Gewinnt Client gestartet.\n")

    # Schritt 1: Hole Lobby-URL
    lobby_ws_url = join_main_server()
    if not lobby_ws_url:
        print("Fehler: Keine Lobby-URL erhalten. Beende Client.")
        return

    # Lobby-ID aus der URL ableiten
    port_str = lobby_ws_url.split(":")[-1]   # "14316/ws"
    port_only = port_str.split("/")[0]       # "14316"
    lobby_id = int(port_only) - int(PORT)    # jetzt global

    # Schritt 2: Starte Verbindung mit der Lobby
    t = threading.Thread(target=ws_thread, daemon=True)
    t.start()

    # Schritt 3: Eingabeloop
    while True:
        if your_turn and not game_over:
            move = input("Deine Spalte (0-6): ")
            if not move.isdigit() or not (0 <= int(move) <= 6):
                print("Ungültige Eingabe. Bitte 0-6 eingeben.")
                continue
            send_move(int(move))
            your_turn = False
        else:
            time.sleep(0.2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSpiel beendet.")

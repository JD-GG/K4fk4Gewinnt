import websocket
import threading
import json
import os
import time
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
MAIN_WS_URL = os.getenv("WS_URL")  # z.B. ws://localhost:14314
SHEME, rest = MAIN_WS_URL.split("://")  # scheme='ws', rest='localhost:14314'
HOST, PORT = rest.split(":")  # host='localhost', port='14314'
LOBBY = int(input("Lobby erstellen oder beitreten? (0 oder LobbyID): "))
PLAYER = int(input("Spieler-Nummer (1 oder 2): "))

# --- GLOBAL ---
current_board = [[0]*7 for _ in range(6)]
your_turn = False
ws = None
game_over = False
lobby_ws_url = None


# --- HELPER ---
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_board(board):
    symbols = {0: " ", 1: "O", 2: "X"}
    clear_console()
    print("    " + "   ".join(str(i) for i in range(7)))
    print("  ┌───" + "┬───" * 6 + "┐")
    for r, row in enumerate(board):
        print("  │ " + " │ ".join(symbols[cell] for cell in row) + " │")
        if r < len(board) - 1:
            print("  ├───" + "┼───" * 6 + "┤")
        else:
            print("  └───" + "┴───" * 6 + "┘")
    print()

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
    global current_board, your_turn, game_over
    try:
        data = json.loads(message)

        if "board" in data and "winner" not in data:
            current_board = data["board"]
            your_turn = (data.get("yourTurn", 0) == PLAYER)
            render_board(current_board)
            print("Dein Zug!" if your_turn else "Warte auf den anderen Spieler...")
            game_over = False

        elif "winner" in data:
            current_board = data["board"]
            render_board(current_board)
            game_over = True
            if data["winner"] == PLAYER:
                print("\n🎉 DU HAST GEWONNEN! 🎉\n")
            else:
                print("\n😢 Leider verloren! 😢\n")

            again = input("Nochmal spielen? (j/n): ")
            if again.lower().startswith("j"):
                print("Warte auf Neustart...")
                game_over = False
            else:
                print("Spiel beendet.")
                os._exit(0)

        elif "error" in data:
            print(f"Fehler: {data['error']}")

    except Exception as e:
        print(f"WS parse error: {e}")

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
    global your_turn, game_over, lobby_ws_url
    print("Vier Gewinnt Client gestartet.\n")
    render_board(current_board)

    # Schritt 1: Hole Lobby-URL
    lobby_ws_url = join_main_server()

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

import websocket
import threading
import json
import os
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
WS_URL = os.getenv("WS_URL")
PLAYER = int(input("Spieler-Nummer (1 oder 2): "))

# --- GLOBAL ---
current_board = [[0]*7 for _ in range(6)]
your_turn = False
ws = None
game_over = False

# --- HELPER ---
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_board(board):
    symbols = {
        0: " ",   # leer
        1: "O",   # Spieler 1
        2: "X"    # Spieler 2
    }
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

# --- WEBSOCKET HANDLING ---
def on_message(ws_, message):
    global current_board, your_turn, game_over
    try:
        data = json.loads(message)

        # normaler Board-Update
        if "board" in data and "winner" not in data:
            current_board = data["board"]
            your_turn = (data.get("yourTurn", 0) == PLAYER)
            render_board(current_board)
            if your_turn:
                print("Dein Zug!")
            else:
                print("Warte auf den anderen Spieler...")
            game_over = False

        # Spielende
        elif "winner" in data:
            current_board = data["board"]
            render_board(current_board)
            game_over = True
            if data["winner"] == PLAYER:
                print("\n🎉🎉🎉 DU HAST GEWONNEN! 🎉🎉🎉\n")
            else:
                print("\n😢 Leider verloren! 😢\n")

            # jetzt direkt fragen
            again = input("Nochmal spielen? (j/n): ")
            if again.lower().startswith("j"):
                print("Warte auf Neustart...")
                game_over = False  # zurücksetzen, bis Server neues Spiel pusht
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
    global ws
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# --- MAIN LOOP ---
def main():
    global your_turn, game_over
    print("Vier Gewinnt Client gestartet.\n")
    render_board(current_board)

    t = threading.Thread(target=ws_thread, daemon=True)
    t.start()

    while True:
        # nur abfragen, wenn es auch Sinn macht
        if your_turn and not game_over:
            move = input("Deine Spalte (0-6): ")
            if not move.isdigit() or not (0 <= int(move) <= 6):
                print("Ungültige Eingabe. Bitte 0-6 eingeben.")
                continue
            send_move(int(move))
            your_turn = False
        else:
            # kleine Pause, damit CPU nicht 100% läuft
            import time
            time.sleep(0.2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSpiel beendet.")

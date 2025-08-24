import requests
import websocket
import threading
import json
import os
from dotenv import load_dotenv

# --- CONFIG ---
SERVER_URL = os.getenv("SERVER_URL")
WS_URL = os.getenv("WS_URL")

# --- GLOBAL ---
current_board = [[0]*7 for _ in range(6)]
your_turn = False

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
    
    # Spaltennummern
    print("    " + "   ".join(str(i) for i in range(7)))

    # Top border
    print("  ┌───" + "┬───" * 6 + "┐")

    for r, row in enumerate(board):
        # Zeile mit Symbolen
        print("  │ " + " │ ".join(symbols[cell] for cell in row) + " │")
        # Zwischenlinien oder Bottom
        if r < len(board) - 1:
            print("  ├───" + "┼───" * 6 + "┤")
        else:
            print("  └───" + "┴───" * 6 + "┘")
    print()

def send_move(column):
    global your_turn, current_board
    try:
        response = requests.post(SERVER_URL, json={"column": column})
        if response.status_code == 200:
            data = response.json()
            current_board = data.get("board", current_board)
            your_turn = data.get("yourTurn", False)
            render_board(current_board)
        else:
            print(f"Server error: {response.status_code}")
    except Exception as e:
        print(f"Connection error: {e}")

# --- WEBSOCKET HANDLING ---
def on_message(ws, message):
    global current_board, your_turn
    try:
        data = json.loads(message)
        if "board" in data:
            current_board = data["board"]
            your_turn = data.get("yourTurn", False)
            render_board(current_board)
            if your_turn:
                print("✅ Dein Zug!")
            else:
                print("⏳ Warte auf den anderen Spieler...")
    except Exception as e:
        print(f"WS parse error: {e}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def ws_thread():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# --- MAIN LOOP ---
def main():
    global your_turn
    print("Vier Gewinnt Client gestartet.\n")

    render_board(current_board)

    # Starte WebSocket in eigenem Thread
    t = threading.Thread(target=ws_thread, daemon=True)
    t.start()

    while True:
        if your_turn:
            move = input("Deine Spalte (0-6): ")
            if not move.isdigit() or not (0 <= int(move) <= 6):
                print("Ungültige Eingabe. Bitte 0-6 eingeben.")
                continue
            send_move(int(move))
        else:
            # einfach warten bis WebSocket signal gibt
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSpiel beendet.")

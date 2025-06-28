# src/shared/config.py

# Lobby Server Configuration
# Ini adalah IP yang akan di-bind oleh Lobby Server di dalam containernya.
# Gunakan "0.0.0.0" agar bisa diakses dari jaringan Docker internal dan diekspos ke host.
LOBBY_SERVER_IP = "0.0.0.0"
# Ini adalah port yang akan diekspos Lobby Server ke host Anda (misal: 192.168.1.65:5000)
LOBBY_SERVER_PORT = 5050

# Game Server Configuration (Internal ke Docker Network)
# Ini adalah port yang akan didengarkan oleh Game Server di dalam masing-masing containernya.
GAME_SERVER_INTERNAL_PORT = 5555

# --- General Network Settings ---
BUFFER_SIZE = 4096
HEADER_SIZE = 4 # Ukuran header untuk pesan (4 bytes)

# --- Game Grid Settings ---
GRID_WIDTH = 24
GRID_HEIGHT = 12

# --- Player Movement Settings ---
PLAYER_SPEED = 0.25 # Kecepatan pergerakan pemain

# --- Game Timer Settings ---
GAME_TIMER_SECONDS = 300 # Durasi game dalam detik

# --- Game State Definitions ---
GAME_STATE_START_SCREEN = "start_screen"
GAME_STATE_PLAYING = "playing"
GAME_STATE_END_SCREEN = "end_screen"

# --- Station Settings ---
STATION_SIZE = 2
STATION_TYPE_FUSION = "fusion"
STATION_TYPE_ENTER = "enter"

# --- Order Spawning Settings ---
ORDER_SPAWN_INTERVAL_MIN = 5
ORDER_SPAWN_INTERVAL_MAX = 15

# --- Doorprize Station Settings ---
STATION_TYPE_DOORPRIZE = "doorprize"
DOORPRIZE_SPAWN_INTERVAL_MIN = 10
DOORPRIZE_SPAWN_INTERVAL_MAX = 15
DOORPRIZE_DURATION = 3
DOORPRIZE_SCORE_MIN = 1000
DOORPRIZE_SCORE_MAX = 20000

# --- Post-Fusion Settings ---
POST_FUSION_RELOCATION = True
POST_FUSION_INGREDIENT_CHANGE = True
FUSION_NEEDED_INGREDIENT_PRIORITY = 0.5

# --- Game Outcome Threshold ---
WIN_SCORE_THRESHOLD = 100000 # Skor minimum untuk menang
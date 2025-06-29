# src/shared/config.py 

SERVER_IP = "127.0.0.1" # Game servers akan mendengarkan di localhost
SERVER_PORT = 5555 # Port default untuk Game Server PERTAMA

BUFFER_SIZE = 4096

GRID_WIDTH = 24
GRID_HEIGHT = 12

PLAYER_SPEED = 0.25
GAME_TIMER_SECONDS = 180

GAME_STATE_START_SCREEN = "start_screen"
GAME_STATE_PLAYING = "playing"
GAME_STATE_END_SCREEN = "end_screen"

STATION_SIZE = 2
STATION_TYPE_FUSION = "fusion"
STATION_TYPE_ENTER = "enter"

ORDER_SPAWN_INTERVAL_MIN = 5
ORDER_SPAWN_INTERVAL_MAX = 15

# Doorprize Station
STATION_TYPE_DOORPRIZE = "doorprize"
DOORPRIZE_SPAWN_INTERVAL_MIN = 10
DOORPRIZE_SPAWN_INTERVAL_MAX = 15
DOORPRIZE_DURATION = 3
DOORPRIZE_SCORE_MIN = 1000
DOORPRIZE_SCORE_MAX = 10000

# Post-Fusion Settings
POST_FUSION_RELOCATION = True
POST_FUSION_INGREDIENT_CHANGE = True
FUSION_NEEDED_INGREDIENT_PRIORITY = 0.5

# Win/Lose System
WIN_SCORE_THRESHOLD = 100000
WIN_BACKGROUND_IMAGE = "end_win.jpg"
WIN_SOUND = "Mission Complete.mp3"
LOSE_BACKGROUND_IMAGE = "end_lose.jpg"
LOSE_SOUND = "Mission Failed.mp3"

# --- NEW LOBBY & SERVER CONFIGS ---
LOBBY_SERVER_IP = "127.0.0.1" # Lobby Server akan mendengarkan di localhost
LOBBY_SERVER_PORT = 5050 # Port unik untuk Lobby Server

# Target Game Servers untuk dipolling oleh Lobby Server (semua di localhost dengan port unik)
GAME_SERVER_TARGETS = [
    {"ip": "127.0.0.1", "port": 5555}, # Game Server 1
    {"ip": "127.0.0.1", "port": 5556}  # Game Server 2
]

POLL_INTERVAL_LOBBY = 2

MAX_PLAYERS_PER_SERVER = 4

GAME_SERVER_PORT_DEFAULT = 5555 
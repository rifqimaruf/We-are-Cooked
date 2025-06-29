# 🍣 We are Cooked

This is a multiplayer cooking game inspired by games like "Overcooked" but with a focus on sushi preparation. The game is built using Python with Pygame for the client interface and uses a custom HTTP implementation for network communication.

## 🍥 Gameplay

- Players control a specific ingredient (like Salmon, Tuna, Rice, etc.)
- When players move and collide within a fusion station, their ingredients can combine to create sushi recipes
- Successfully creating recipes earns points based on the recipe's price
- The game has different recipe levels (1-4) with increasing complexity and value
- Limited-time **Doorprize Events** appear randomly for bonus points
- Win condition: Reach the score threshold before time runs out

## 🕹️ How to Play

### Controls
- **Arrow Keys**: Move your character around the kitchen
- **Enter**: Change your ingredient at Enter Stations (green)
- **ESC**: Toggle recipe almanac
- **Alt+F4** or **Close Window**: Quit the game

### Game Mechanics
- Each player carries a single ingredient at a time
- **Fridge Stations** (green): Change your current ingredient
- **Fusion Stations** (red): Combine ingredients to create recipes
- **Doorprize Stations** (blue): Claim bonus points during limited-time events
- Successfully creating recipes awards points based on the recipe's complexity
- The game displays current orders to fulfill and a countdown timer
- Reach the win score threshold before time runs out to win!

## 👨🏻‍🍳 Recipes
The game includes recipes with various difficulty levels:
- **Level 1**: Simple recipes requiring 1-2 ingredients
- **Level 2**: Medium recipes requiring 3 ingredients  
- **Level 3**: Complex recipes requiring 4 ingredients
- **Level 4**: Master recipes requiring 5+ ingredients

Higher level recipes provide more points but require more coordination between players.

## ⚙️ Network Configuration

The game can be configured by editing `src/shared/config.py`:
```python
SERVER_IP = "127.0.0.1"       # Server IP address (localhost by default)
SERVER_PORT = 5555            # Server port
```

## 💡 Getting Started

### Prerequisites
Make sure you have Python 3.8+ installed, then install the required packages:
```sh
pip install -r requirements.txt
```

Required packages:
- `pygame==2.6.1` - Game engine and graphics
- `requests==2.31.0` - HTTP client functionality

### Database
After installation is complete, you would need to run the databse initialization program before running a server instance.
```sh
python -m src.shared.initialize_database
```

### Running the Game

#### 1. Start the Server
```sh
python -m src.server.server
```
The server will start on the IP and port specified in `config.py` (default: 127.0.0.1:5555).

#### 2. Start Client(s)
```sh
python -m src.client.client
```
Each client connects to the server automatically. Multiple clients can connect to play together.

### Network Configuration
Before starting the game, update the server IP in `src/shared/config.py`:
1. Find your server's IP address using `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Update `SERVER_IP` in the config file
3. Ensure all clients use the same configuration

## 🔧 Technical Breakdown

### Network Architecture
The game uses a custom HTTP implementation built on raw sockets:

1. **Server Architecture**:
   - Socket-based HTTP server handling multiple concurrent connections
   - Thread pool executor for handling client requests
   - Custom HTTP request/response parsing and generation
   - Game state management and broadcasting to all connected clients

2. **Client Architecture**:
   - HTTP client using raw sockets for communication
   - Polling-based game state updates from server
   - Pygame-based rendering and input handling
   - Asset management for graphics and audio

3. **Game State Management**:
   - Centralized game state on the server
   - Regular state synchronization between server and clients
   - Event-driven architecture for player actions and game events
   - Recipe validation and scoring system

### HTTP API Endpoints
- **GET /game_state**: Returns current game state
- **GET /health**: Server health check
- **POST /connect**: Register new client connection
- **POST /action**: Process client actions (movement, ingredient changes)
- **POST /disconnect**: Handle client disconnection

### Game Features
- **Multi-level Recipe System**: 4 difficulty levels with increasing complexity
- **Dynamic Order System**: Random order generation with time limits
- **Doorprize Events**: Limited-time bonus point opportunities
- **Real-time Multiplayer**: Synchronized gameplay across multiple clients
- **Asset Management**: Efficient loading and management of game assets
- **Performance Profiling**: Built-in client-side performance monitoring

## 🎮 Game Phases
1. **Start Screen**: Lobby where players wait for the game to begin
2. **Playing Phase**: Active gameplay with order fulfillment and scoring
3. **End Screen**: Final score display and win/lose conditions

## 🔧 Development Setup

### Project Structure
```
We-are-Cooked/
├── src/
│   ├── client/          # Client-side code
│   │   ├── client.py    # Main client entry point
│   │   ├── http.py      # HTTP client implementation
│   │   ├── renderer.py  # Game rendering
│   │   └── ...
│   ├── server/          # Server-side code
│   │   ├── server.py    # Main server entry point
│   │   ├── http.py      # HTTP server implementation
│   │   └── ...
│   └── shared/          # Shared code
│       ├── config.py    # Configuration settings
│       └── ...
├── assets/              # Game assets (images, sounds)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Configuration Updates
To run the game on your network:

1. **Find your server IP address**:
   ```sh
   # On Linux/Mac
   ifconfig
   
   # On Windows
   ipconfig
   ```

2. **Update configuration** in `src/shared/config.py`:
   ```python
   SERVER_IP = "YOUR_SERVER_IP_HERE"  # Replace with your actual IP
   SERVER_PORT = 5555                 # Or your preferred port
   ```

3. **Ensure firewall allows connections** on the specified port

### Troubleshooting
- **Connection Issues**: Verify SERVER_IP matches your actual network IP
- **Port Conflicts**: Change SERVER_PORT if 5555 is already in use
- **Asset Loading**: Ensure assets folder is present and accessible
- **Performance**: Check client_profile.prof for performance bottlenecks

## 📝 Credits
This game was developed as a Network Programming course project, demonstrating custom HTTP implementation and real-time multiplayer game architecture.
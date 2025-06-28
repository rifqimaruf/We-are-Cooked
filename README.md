# 🍣 We are Cooked

This is a multiplayer cooking game inspired by games like "Overcooked" but with a focus on sushi preparation. The game is built using Python with Pygame for the client interface and supports both socket programming and HTTP for network communication.

## 🍥 Gameplay

- Players control a specific ingredient (like Salmon, Tuna, Rice, etc.)
- When players move and collide within a fusion station, their ingredients can combine to create sushi recipes
- Successfully creating recipes earns points based on the recipe's price
- The game has different recipe levels (1-4) with increasing complexity and value

## 🕹️ How to Play
- Players can move using **Arrow Keys**
- Each players carry a single ingredient
- You can change your ingredient by going to the **Enter Station** (labeled green) and pressing **Enter**
- Players can fuse within a **Fusion Station** (Labeled Red) to fuse into a recipe
- If that was a valid recipe, points are awarded based on the recipe's price
- The game has a timer and displays current orders to fulfill
- There are limited time **Doorprize Events**, claim free prizes!

## 👨🏻‍🍳 Recipes
The game includes recipes with various difficulty levels, each difficulty is directly determined by the amount of ingredients are needed to make it. The higher the level, the more pricey a recipe becomes.

## 💡 Starting the Game
### Prerequisites
Make sure you have Python installed with the required packages
```sh
pip install -r requirements.txt
```

### Socket-Based Version
#### Server
Run this command to initialize the server before turning on any client instance.
```sh
python -m src.server.server
```

#### Client
Running this command will start up an individual client.
```sh
python -m src.client.client
```

### HTTP-Based Version
#### Server
Run this command to initialize the HTTP server.
```sh
python -m src.server.http_server_main
```

#### Client
Running this command will start up an HTTP-based client.
```sh
python -m src.client.http_client_main
```

For more details on the HTTP implementation, see [HTTP_IMPLEMENTATION.md](HTTP_IMPLEMENTATION.md).

## 🔧 Technical Breakdown (For Contributions)
1. Network Architecture:
   - Server manages the game state and broadcasts updates to all clients
   - Clients send movement commands to the server
   - The server processes player movements, recipe combinations, and doorprize 
interactions

2. Game State Management:
   - The GameState class tracks player positions, ingredients, orders, score, 
and timer
   - The server regularly checks for recipe combinations and doorprize 
interactions
   - State updates are broadcast to all clients at regular intervals

3. Client Rendering:
   - The client uses Pygame to render the game state
   - Visual effects and sound effects enhance the gameplay experience
   - The client handles user input and sends commands to the server

4. Game Phases:
   - Start screen (lobby) where players wait for the game to begin
   - Playing phase where players fulfill orders and collect points
   - End screen showing the final score

<!-- ## Credits
This game was made as a Finals Submission to our Network Programming course. Proper recognition due to the developers: -->
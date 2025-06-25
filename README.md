# 🍣 We are Cooked

This is a multiplayer cooking game inspired by games like "Overcooked" but with a focus on sushi preparation. The game is built using Python with Pygame for the client interface and uses socket programming for network communication.  

## 🍥 Gameplay

- Players control characters that each carry a specific ingredient (like Salmon, Tuna, Rice, etc.)
- When players move and collide with each other, their ingredients can combine to create sushi recipes
- Successfully creating recipes earns points based on the recipe's price
- The game has different recipe levels (1-4) with increasing complexity and value

## 🕹️ How to Play
- Players can move using arrow keys
- Each players carry a single ingredient
- When players collide, they can combine into a recipe
- If that was a valid recipe, points are awarded based on the recipe's price
- The game has a timer and displays current orders to fulfill

## 👨🏻‍🍳 Recipes
The game includes recipes with various difficulty levels, each difficulty is directly determined by the amount of ingredients are needed to make it. The higher the level, the more pricey a recipe becomes.

## 💡 Starting the Game
### Prerequisites
Make sure you have Python installed with the required packages
```sh
pip install -r requirements.txt
```

### Server
Run this command to initialize the server before turning on any client instance.
```sh
python -m src.server
```


### Client
Running this command will start up an individual client.
```sh
python -m src.client
```

## 🔧 Technical Breakdown (For Contributions)
1. Client-Server Architecture
   - Server manages game state and broadcasts updates to all clients
   - Clients send movement commands and render the game state

2. Database
   - SQLite database stores all recipes and ingredients
   - Recipes are organized by level (1-4) with increasing complexity
   - Each recipe requires specific ingredients and has a set price

3. Key Components
   - server.py: Handles client connections, game state updates, and broadcasts
   - client.py: Renders the game and handles player input
   - game_state.py: Manages player positions, recipe checking, and scoring
   - recipe_manager.py: Interfaces with the recipe database and checks valid combinations
   - initialize_database.py: Sets up the SQLite database with ingredients and recipes

<!-- ## Credits
This game was made as a Finals Submission to our Network Programming course. Proper recognition due to the developers: -->
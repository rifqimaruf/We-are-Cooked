import pygame
import sys
import json
import socket
import threading
import time
from src.network import Network
from src.shared import config

pygame.init()

tile_size = 50
# Add extra height for UI elements
ui_height = 60
screen_width = config.GRID_WIDTH * tile_size
screen_height = (config.GRID_HEIGHT * tile_size) + ui_height
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("We are Cooked")
clock = pygame.time.Clock()

current_state = None

def format_time(seconds):
    """Convert seconds to MM:SS format"""
    # Ensure we're working with an integer for display
    seconds = int(seconds)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def draw(state):
    # Clear the screen
    screen.fill((255, 255, 255))
    
    # Draw game area background
    game_area = pygame.Rect(0, 0, screen_width, screen_height - ui_height)
    pygame.draw.rect(screen, (240, 240, 240), game_area)
    
    client_id = state.get("client_id")

    # Draw players
    for player_id, player in state["players"].items():
        x, y = player["pos"]
        rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
        
        if player_id == client_id:
            pygame.draw.rect(screen, (0, 150, 255), rect)
        else:
            pygame.draw.rect(screen, (0, 200, 0), rect)
            
        font = pygame.font.SysFont(None, 24)
        img = font.render(player["ingredient"], True, (0, 0, 0))
        screen.blit(img, (rect.x, rect.y))

    # Draw current client's ingredient
    client_ingredient = None
    
    if client_id and client_id in state["players"]:
        client_ingredient = state["players"][client_id]["ingredient"]
    
    if client_ingredient:
        ingredient_bg = pygame.Rect(10, 10, 250, 50)
        pygame.draw.rect(screen, (50, 50, 50), ingredient_bg)
        pygame.draw.rect(screen, (100, 100, 100), ingredient_bg, 2)
        
        ingredient_title_font = pygame.font.SysFont(None, 18)
        ingredient_text = ingredient_title_font.render(f"you are:", True, (200, 200, 200))
        screen.blit(ingredient_text, (20, 18))

        ingredient_font = pygame.font.SysFont(None, 24)
        ingredient_text = ingredient_font.render(client_ingredient, True, (255, 255, 255))
        screen.blit(ingredient_text, (20, 35))
    
    # Draw UI background
    ui_area = pygame.Rect(0, screen_height - ui_height, screen_width, ui_height)
    pygame.draw.rect(screen, (50, 50, 50), ui_area)
    
    # Draw score
    score_font = pygame.font.SysFont(None, 28)
    score_text = score_font.render(f"Score: {state['score']}", True, (255, 255, 255))
    screen.blit(score_text, (20, screen_height - ui_height + 20))
    
    # Draw timer with color based on remaining time
    timer_font = pygame.font.SysFont(None, 28)
    timer_color = (255, 255, 255)  # Default white
    
    # Change timer color based on remaining time
    if state['timer'] < 30:
        # Gradually change from yellow to red as time decreases
        red = min(255, int(255))
        green = max(0, int(255 * (state['timer'] / 30)))
        timer_color = (red, green, 0)
    
    timer_text = timer_font.render(f"Time: {format_time(state['timer'])}", True, timer_color)
    timer_rect = timer_text.get_rect(midtop=(screen_width // 2, screen_height - ui_height + 10))
    screen.blit(timer_text, timer_rect)
    
    # Draw timer bar
    timer_bar_width = 200
    timer_bar_height = 8
    timer_bar_x = (screen_width // 2) - (timer_bar_width // 2)
    timer_bar_y = screen_height - ui_height + 35
    
    # Background bar (empty)
    pygame.draw.rect(screen, (100, 100, 100), 
                    (timer_bar_x, timer_bar_y, timer_bar_width, timer_bar_height))
    
    # Filled portion of the bar
    fill_width = int((state['timer'] / config.GAME_TIMER_SECONDS) * timer_bar_width)
    if fill_width > 0:
        # Color gradient from green to red
        if state['timer'] > config.GAME_TIMER_SECONDS * 0.6:  # > 60%
            bar_color = (0, 255, 0)  # Green
        elif state['timer'] > config.GAME_TIMER_SECONDS * 0.3:  # > 30%
            bar_color = (255, 255, 0)  # Yellow
        else:
            bar_color = (255, 0, 0)  # Red
            
        pygame.draw.rect(screen, bar_color, 
                        (timer_bar_x, timer_bar_y, fill_width, timer_bar_height))
    
    # Draw orders
    if "orders" in state and state["orders"]:
        order_font = pygame.font.SysFont(None, 24)
        order_text = order_font.render(f"Orders: {', '.join([order['name'] for order in state['orders'][:2]])}", True, (255, 255, 255))
        screen.blit(order_text, (screen_width - 250, screen_height - ui_height + 25))
    
    pygame.display.flip()

def receiver_thread(net):
    global current_state
    while True:
        try:
            state = net.receive()
            current_state = state
        except (json.JSONDecodeError, socket.error):
            break

def main():
    net = Network()
    print("Waiting for initial state...")
    global current_state
    current_state = net.receive()
    print(f"Got initial state: {current_state}")
    
    # Store the client's player ID (using the client's socket address)
    client_addr = net.get_addr()
    client_id = str(client_addr)
    print(f"Your player ID: {client_id}")

    threading.Thread(target=receiver_thread, args=(net,), daemon=True).start()
    
    # For local timer countdown - use absolute start time instead of incremental updates
    start_time = time.time()
    initial_timer = current_state.get("timer", config.GAME_TIMER_SECONDS)
    game_end_time = start_time + initial_timer
    
    # Variables for smooth timer adjustment
    target_timer = initial_timer
    displayed_timer = initial_timer
    last_frame_time = time.time()

    while True:
        current_time = time.time()
        delta_time = current_time - last_frame_time
        last_frame_time = current_time
        
        clock.tick(60)  # Increase frame rate for smoother updates

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            net.send({"action": "move", "direction": "UP"})
        elif keys[pygame.K_DOWN]:
            net.send({"action": "move", "direction": "DOWN"})
        elif keys[pygame.K_LEFT]:
            net.send({"action": "move", "direction": "LEFT"})
        elif keys[pygame.K_RIGHT]:
            net.send({"action": "move", "direction": "RIGHT"})

        if current_state:
            # Create a copy of the current state to modify locally
            display_state = current_state.copy()
            
            # Add client ID to the state for the draw function to use
            display_state["client_id"] = client_id
            
            # Calculate target time based on server updates
            if "timer" in current_state:
                server_timer = current_state["timer"]
                # Only make major adjustments if the difference is significant
                if abs(server_timer - displayed_timer) > 3:
                    target_timer = server_timer
                    # Adjust game_end_time based on the new target
                    game_end_time = current_time + target_timer
            
            # Calculate remaining time based on absolute end time
            remaining_seconds = max(0, game_end_time - current_time)
            
            # Smoothly interpolate between current displayed time and target time
            if abs(displayed_timer - remaining_seconds) > 0.05:
                # Interpolate with a small step for smooth transition
                displayed_timer = displayed_timer + (remaining_seconds - displayed_timer) * min(1.0, delta_time * 2)
            else:
                displayed_timer = remaining_seconds
                
            # Update the display state with our smooth timer (convert to int for display)
            display_state["timer"] = int(displayed_timer)
            
            draw(display_state)

if __name__ == "__main__":
    main()

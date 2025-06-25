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
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def draw(state):
    # Clear the screen
    screen.fill((255, 255, 255))
    
    # Draw game area background
    game_area = pygame.Rect(0, 0, screen_width, screen_height - ui_height)
    pygame.draw.rect(screen, (240, 240, 240), game_area)
    
    # Draw players
    for player in state["players"].values():
        x, y = player["pos"]
        rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
        pygame.draw.rect(screen, (0, 200, 0), rect)
        font = pygame.font.SysFont(None, 24)
        img = font.render(player["ingredient"], True, (0, 0, 0))
        screen.blit(img, (rect.x, rect.y))
    
    # Draw UI background
    ui_area = pygame.Rect(0, screen_height - ui_height, screen_width, ui_height)
    pygame.draw.rect(screen, (50, 50, 50), ui_area)
    
    # Draw score
    score_font = pygame.font.SysFont(None, 28)
    score_text = score_font.render(f"Score: {state['score']}", True, (255, 255, 255))
    screen.blit(score_text, (20, screen_height - ui_height + 15))
    
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
        screen.blit(order_text, (screen_width - 250, screen_height - ui_height + 15))
    
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

    threading.Thread(target=receiver_thread, args=(net,), daemon=True).start()
    
    # For local timer countdown - use absolute start time instead of incremental updates
    start_time = time.time()
    initial_timer = current_state.get("timer", config.GAME_TIMER_SECONDS)
    game_end_time = start_time + initial_timer

    while True:
        clock.tick(30)

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
            
            # Calculate remaining time based on absolute end time
            now = time.time()
            remaining_seconds = max(0, int(game_end_time - now))
            
            # If server sends a timer update, recalculate the end time
            if "timer" in current_state and abs(current_state["timer"] - remaining_seconds) > 2:
                # Only adjust if the difference is significant (>2 seconds)
                game_end_time = now + current_state["timer"]
                remaining_seconds = current_state["timer"]
            
            # Update the display state with our smooth timer
            display_state["timer"] = remaining_seconds
            
            draw(display_state)

if __name__ == "__main__":
    main()

import pygame
import sys
import json
import socket
import threading
import time
import random
from src.network import Network
from src.shared import config
import os

pygame.init()

tile_size = 50
ui_height = 60
screen_width = config.GRID_WIDTH * tile_size
screen_height = (config.GRID_HEIGHT * tile_size) + ui_height
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("We are Cooked")
clock = pygame.time.Clock()

current_state = None
game_screen_state = config.GAME_STATE_START_SCREEN
overlay_start_time = 0
final_score = 0
client_id = None
username = f"Player{random.randint(100, 999)}"
username_input_active = False
username_input_text = ""

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
image_path = os.path.join(base_dir, 'assets', 'images', 'end_bg.png')

def format_time(seconds):
    """Convert seconds to MM:SS format"""
    seconds = int(seconds)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def draw_text_input(rect, text, active):
    """Draw a text input field with the given text"""
    color = (100, 100, 200) if active else (70, 70, 70)
    pygame.draw.rect(screen, color, rect, border_radius=5)
    pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=5)
    
    font = pygame.font.SysFont(None, 32)
    text_surface = font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(midleft=(rect.x + 10, rect.centery))
    screen.blit(text_surface, text_rect)

def draw_button(rect, text, hover=False):
    """Draw a button with the given text"""
    color = (100, 200, 100) if hover else (80, 180, 80)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, (50, 150, 50), rect, 3, border_radius=10)
    
    font = pygame.font.SysFont(None, 36)
    text_surface = font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    
    return rect

def draw_start_screen():
    """Draw the start screen with connected clients and start button"""
    screen.fill((30, 30, 50))
    
    # Draw game title
    title_font = pygame.font.SysFont(None, 72)
    title_text = title_font.render("We are Cooked!", True, (255, 220, 100))
    title_rect = title_text.get_rect(center=(screen_width // 2, screen_height // 6))
    screen.blit(title_text, title_rect)
    
    # Draw username input field
    username_label_font = pygame.font.SysFont(None, 32)
    username_label = username_label_font.render("Your Username:", True, (200, 200, 200))
    screen.blit(username_label, (screen_width // 4, screen_height // 3))
    
    username_rect = pygame.Rect(screen_width // 4, screen_height // 3 + 40, 300, 40)
    draw_text_input(username_rect, username_input_text if username_input_active else username, username_input_active)
    
    # Draw connected clients
    clients_font = pygame.font.SysFont(None, 36)
    clients_title = clients_font.render("Connected Players:", True, (200, 200, 200))
    screen.blit(clients_title, (screen_width // 4, screen_height // 2))
    
    if current_state and "clients_info" in current_state:
        y_offset = screen_height // 2 + 40
        for player_id, info in current_state["clients_info"].items():
            player_name = info.get("username", "Unknown")
            ready_status = "Ready" if info.get("ready", False) else "Not Ready"
            
            # Highlight the current client
            if player_id == client_id:
                player_text = f"> {player_name} (You) - {ready_status}"
                text_color = (255, 255, 100)
            else:
                player_text = f"  {player_name} - {ready_status}"
                text_color = (255, 255, 255)
                
            player_font = pygame.font.SysFont(None, 28)
            player_label = player_font.render(player_text, True, text_color)
            screen.blit(player_label, (screen_width // 4, y_offset))
            y_offset += 30
    
    # Draw ready button
    ready_button_width, ready_button_height = 200, 50
    ready_button_x = (screen_width - ready_button_width) // 4
    ready_button_y = screen_height * 3 // 4
    ready_button_rect = pygame.Rect(ready_button_x, ready_button_y, ready_button_width, ready_button_height)
    
    # Check if mouse is hovering over button
    mouse_pos = pygame.mouse.get_pos()
    ready_button_hover = ready_button_rect.collidepoint(mouse_pos)
    
    # Get current ready status
    is_ready = False
    if current_state and "clients_info" in current_state and client_id in current_state["clients_info"]:
        is_ready = current_state["clients_info"][client_id].get("ready", False)
        # print(f"Current ready status: {is_ready}")
    
    ready_text = "Cancel Ready" if is_ready else "Ready Up"
    draw_button(ready_button_rect, ready_text, ready_button_hover)
    
    # Draw start button
    start_button_width, start_button_height = 200, 50
    start_button_x = (screen_width - start_button_width) * 3 // 4
    start_button_y = screen_height * 3 // 4
    start_button_rect = pygame.Rect(start_button_x, start_button_y, start_button_width, start_button_height)
    
    # Check if mouse is hovering over button
    start_button_hover = start_button_rect.collidepoint(mouse_pos)
    
    # Check if all players are ready
    all_ready = False
    if current_state and "clients_info" in current_state:
        all_ready = all(client["ready"] for client in current_state["clients_info"].values())
    
    # Draw start button with different color based on readiness
    if all_ready:
        draw_button(start_button_rect, "Start Game", start_button_hover)
    else:
        # Draw disabled button
        pygame.draw.rect(screen, (100, 100, 100), start_button_rect, border_radius=10)
        pygame.draw.rect(screen, (70, 70, 70), start_button_rect, 3, border_radius=10)
        
        font = pygame.font.SysFont(None, 36)
        text_surface = font.render("Start Game", True, (180, 180, 180))
        text_rect = text_surface.get_rect(center=start_button_rect.center)
        screen.blit(text_surface, text_rect)
    
    pygame.display.flip()
    
    return username_rect, ready_button_rect, start_button_rect, all_ready

def draw_end_screen():
    """Draw the end screen with final score and restart button"""
    try:
        bg_image = pygame.image.load(image_path)
        bg_image = pygame.transform.scale(bg_image, (screen_width, screen_height))
        screen.blit(bg_image, (0, 0))
    except pygame.error:
        screen.fill((30, 30, 50))
        print("Warning: Could not load end_bg.png, using fallback background")
    
    # Draw final score
    score_font = pygame.font.SysFont(None, 48)
    score_text = score_font.render(f"Final Score: {final_score}", True, (0, 0, 0))
    score_rect = score_text.get_rect(center=(screen_width // 2, screen_height // 2 + 130))
    screen.blit(score_text, score_rect)
    
    # Draw restart button
    button_width, button_height = 200, 60
    button_x = (screen_width - button_width) // 2
    button_y = (screen_height * 3) // 4
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    
    # Check if mouse is hovering over button
    mouse_pos = pygame.mouse.get_pos()
    button_hover = button_rect.collidepoint(mouse_pos)
    
    draw_button(button_rect, "Play Again", button_hover)
    
    pygame.display.flip()
    
    return button_rect  

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
    
    # Draw UI background
    ui_area = pygame.Rect(0, screen_height - ui_height, screen_width, ui_height)
    pygame.draw.rect(screen, (50, 50, 50), ui_area)
    
    if client_ingredient:
        ingredient_bg = pygame.Rect(10, 10, 250, 50)
        pygame.draw.rect(screen, (50, 50, 50), ingredient_bg)
        pygame.draw.rect(screen, (100, 100, 100), ingredient_bg, 2)

        ingredient_title_font = pygame.font.SysFont(None, 18)
        ingredient_text = ingredient_title_font.render(f"You are:", True, (200, 200, 200))
        screen.blit(ingredient_text, (screen_width - 200, screen_height - ui_height + 15))

        ingredient_font = pygame.font.SysFont(None, 28)
        ingredient_text = ingredient_font.render(client_ingredient, True, (255, 255, 255))
        screen.blit(ingredient_text, (screen_width - 200, screen_height - ui_height + 30))

        # order_font = pygame.font.SysFont(None, 24)
        # order_text = order_font.render(f"Orders: {', '.join([order['name'] for order in state['orders'][:2]])}", True, (255, 255, 255))
        # screen.blit(order_text, (screen_width - 500, screen_height - ui_height + 25))

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
    timer_bar_y = screen_height - ui_height + 40
    
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
        orders_bg = pygame.Rect(10, 10, 250, 75)
        pygame.draw.rect(screen, (50, 50, 50), orders_bg)
        pygame.draw.rect(screen, (100, 100, 100), orders_bg, 2)
        
        orders_title_font = pygame.font.SysFont(None, 18)
        orders_text = orders_title_font.render(f"orders:", True, (200, 200, 200))
        screen.blit(orders_text, (20, 18))

        order_font = pygame.font.SysFont(None, 24)
        for i, order in enumerate(state["orders"][:2]):
            order_name = order["name"]
            order_text = order_font.render(order_name, True, (255, 255, 255))
            screen.blit(order_text, (20, 35 + i * 25))
    
    # Draw single player mode indicator if only one player
    if len(state["players"]) == 1:
        single_player_bg = pygame.Rect(screen_width - 400, 10, 380, 40)
        pygame.draw.rect(screen, (50, 50, 100), single_player_bg, border_radius=5)
        pygame.draw.rect(screen, (100, 100, 200), single_player_bg, 2, border_radius=5)
        
        single_player_font = pygame.font.SysFont(None, 24)
        single_player_text = single_player_font.render("Single Player Mode: Hit bottom to merge!", True, (255, 200, 100))
        screen.blit(single_player_text, (screen_width - 390, 20))
    
    pygame.display.flip()

def receiver_thread(net):
    global current_state, game_screen_state, client_id
    while True:
        try:
            state = net.receive()
            # print(f"Received state: game_started={state.get('game_started')}, timer={state.get('timer')}")
            current_state = state
            
            if "game_started" in state:
                if state["game_started"] and game_screen_state == config.GAME_STATE_START_SCREEN:
                    print("Transitioning to PLAYING state")
                    game_screen_state = config.GAME_STATE_PLAYING
                elif not state["game_started"] and game_screen_state == config.GAME_STATE_PLAYING:
                    print("Transitioning to START_SCREEN state")
                    game_screen_state = config.GAME_STATE_START_SCREEN
            
            if client_id is None and "client_id" in state:
                client_id = state["client_id"]
                
        except (json.JSONDecodeError, socket.error) as e:
            print(f"Error in receiver thread: {e}")
            break

def main():
    global current_state, game_screen_state, overlay_start_time, final_score
    global client_id, username, username_input_active, username_input_text
    
    net = Network()
    # print("Waiting for initial state...")
    current_state = net.receive()
    print(f"Got initial state: {current_state}")
    
    client_id = current_state.get("client_id")
    print(f"Your player ID: {client_id}")
    
    if "game_started" in current_state:
        if current_state["game_started"]:
            game_screen_state = config.GAME_STATE_PLAYING
        else:
            game_screen_state = config.GAME_STATE_START_SCREEN
    
    threading.Thread(target=receiver_thread, args=(net,), daemon=True).start()
    
    last_frame_time = time.time()
    
    restart_button_rect = None
    username_rect = None
    ready_button_rect = None
    start_button_rect = None
    all_ready = False

    net.send({"action": "set_username", "username": username})

    while True:
        current_time = time.time()
        delta_time = current_time - last_frame_time
        last_frame_time = current_time
        
        clock.tick(60)  # Increase frame rate for smoother updates

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if game_screen_state == config.GAME_STATE_START_SCREEN:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    
                    # Check if username field was clicked
                    if username_rect and username_rect.collidepoint(mouse_pos):
                        username_input_active = not username_input_active
                        if username_input_active:
                            username_input_text = username
                    else:
                        username_input_active = False
                        
                    # Check if ready button was clicked
                    if ready_button_rect and ready_button_rect.collidepoint(mouse_pos):
                        # print("Ready button clicked, sending toggle_ready action")
                        net.send({"action": "toggle_ready"})
                        
                    # Check if start button was clicked and all players are ready
                    if start_button_rect and start_button_rect.collidepoint(mouse_pos) and all_ready:
                        # print("Start button clicked, sending start_game action")
                        net.send({"action": "start_game"})
                
                # Handle text input for username
                if event.type == pygame.KEYDOWN and username_input_active:
                    if event.key == pygame.K_RETURN:
                        username = username_input_text
                        username_input_active = False
                        net.send({"action": "set_username", "username": username})
                    elif event.key == pygame.K_BACKSPACE:
                        username_input_text = username_input_text[:-1]
                    else:
                        if len(username_input_text) < 15:
                            username_input_text += event.unicode
            
            elif game_screen_state == config.GAME_STATE_END_SCREEN and event.type == pygame.MOUSEBUTTONDOWN:
                if restart_button_rect and restart_button_rect.collidepoint(event.pos):
                    # print("Play Again button clicked, sending return_to_lobby action")
                    game_screen_state = config.GAME_STATE_START_SCREEN
                    net.send({"action": "return_to_lobby"})
                    if client_id in current_state.get("clients_info", {}):
                        current_state["clients_info"][client_id]["ready"] = False

        if game_screen_state == config.GAME_STATE_START_SCREEN:
            username_rect, ready_button_rect, start_button_rect, all_ready = draw_start_screen()
            
        elif game_screen_state == config.GAME_STATE_PLAYING:
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
                display_state = current_state.copy()
                
                display_state["client_id"] = client_id
                
                if display_state.get("timer", 0) <= 0:
                    game_screen_state = config.GAME_STATE_END_SCREEN
                    overlay_start_time = current_time
                    final_score = display_state.get("score", 0)
                
                draw(display_state)
                
        elif game_screen_state == config.GAME_STATE_END_SCREEN:
            restart_button_rect = draw_end_screen()

if __name__ == "__main__":
    main()

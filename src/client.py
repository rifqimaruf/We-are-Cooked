import pygame
import sys
import json
import socket
import threading
from src.network import Network
from src.shared import config

pygame.init()

tile_size = 50
screen = pygame.display.set_mode((config.GRID_WIDTH * tile_size, config.GRID_HEIGHT * tile_size))
clock = pygame.time.Clock()

current_state = None

def draw(state):
    screen.fill((255, 255, 255))
    for player in state["players"].values():
        x, y = player["pos"]
        rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
        pygame.draw.rect(screen, (0, 200, 0), rect)
        font = pygame.font.SysFont(None, 24)
        img = font.render(player["ingredient"], True, (0, 0, 0))
        screen.blit(img, (rect.x, rect.y))
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
            draw(current_state)

if __name__ == "__main__":
    main()

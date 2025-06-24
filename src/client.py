import pygame
import sys
from network import Network
import config

pygame.init()

tile_size = 50
screen = pygame.display.set_mode((config.GRID_WIDTH * tile_size, config.GRID_HEIGHT * tile_size))
clock = pygame.time.Clock()

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

def main():
    net = Network()
    state = net.receive()

    while True:
        clock.tick(10)
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

        state = net.receive()
        draw(state)

if __name__ == "__main__":
    main()

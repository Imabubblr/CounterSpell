import pygame
from pygame.locals import *
import sys

pygame.init()
Vec = pygame.math.Vector2  # 2 for two dimensional

HEIGHT = 500  # Screen height
WIDTH = 400  # Screen width
ACC = 0.5  # Impact of user's keyboard on the acceleration
FRIC = -0.12  # Impact of acceleration on velocity

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.surf = pygame.Surface((30, 30))
        self.surf.fill((128, 255, 40))
        self.rect = self.surf.get_rect(center = (10, 420))

        self.pos = Vec((10, 385))
        self.vel = Vec(0, 0)
        self.acc = Vec(0, 0)

    def move(self):
        self.acc = Vec(0, 0)
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_LEFT]:
            self.acc.x = -ACC
        if pressed_keys[K_RIGHT]:
            self.acc.x = ACC

        self.acc.x += self.vel.x * FRIC
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        if self.pos.x > WIDTH:
            self.pos.x = 0
        if self.pos.x < 0:
            self.pos.x = WIDTH

        self.rect.midbottom = self.pos

class Platform(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.surf = pygame.Surface((WIDTH, 20))
        self.surf.fill((255, 0, 0))
        self.rect = self.surf.get_rect(center = (WIDTH / 2, HEIGHT - 100))

def main():
    platform_sprite = Platform()
    player = Player()

    all_sprites = pygame.sprite.Group()
    all_sprites.add(platform_sprite)
    all_sprites.add(player)

    pygame.display.set_caption("Game")
    background_surface = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    FPS = 60

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        background_surface.fill((0, 0, 0))

        for entity in all_sprites:
            background_surface.blit(entity.surf, entity.rect)

        player.move()

        pygame.display.update()
        clock.tick(FPS)

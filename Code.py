import pygame
from pygame.locals import *
import sys

pygame.init()
Vec = pygame.math.Vector2  # 2 for two dimensional

HEIGHT = 600  # Screen height
WIDTH = 800  # Screen width
ACC = 0.5  # Impact of user's keyboard on the acceleration
FRIC_X = -0.12  # Air resistance
FRIC_Y = -0.01

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = 30
        self.height = 30
        self.surf = pygame.Surface((self.width, self.height))
        self.surf.fill((128, 255, 40))
        self.rect = self.surf.get_rect(center = (x, y))
        self.platforms_rects = []

        self.pos = Vec((10, 385))
        self.vel = Vec(0, 0)
        self.acc = Vec(0, 0)

    def physics(self):
        for platform in self.platforms_rects:
            if self.rect.colliderect(platform) and self.rect[1] <= platform[1]:
                on_platform = platform
                break
        else:
            on_platform = None

        self.acc = Vec(0, 0)
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_LEFT] or pressed_keys[K_a]:
            self.acc.x = -ACC
        if pressed_keys[K_RIGHT] or pressed_keys[K_d]:
            self.acc.x = ACC
        if pressed_keys[K_SPACE] and on_platform is not None:
            self.acc.y = -7  # Up

        # Gravity
        if on_platform is None:
            self.vel.y += 0.2
        else:
            # Prevent from going down on a platform
            self.vel.y = min(0, self.vel.y)

        self.acc.x += self.vel.x * FRIC_X
        self.acc.y += self.vel.y * FRIC_Y
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        if self.pos.x > WIDTH:
            self.pos.x = 0
        if self.pos.x < 0:
            self.pos.x = WIDTH

        if on_platform is not None:
            # Prevent from going down on a platform
            self.pos[1] = on_platform[1]

    def update_ui(self):
        self.rect.midbottom = self.pos

class Platform(pygame.sprite.Sprite):
    def __init__(self, width, height, pos_x, pos_y):
        super().__init__()
        self.surf = pygame.Surface((width, height))
        self.surf.fill((255, 0, 0))
        self.rect = self.surf.get_rect(center = (pos_x, pos_y))

    def update_ui(self):
        pass

class Images(pygame.sprite.Sprite): 
    def __init__(self, picture, Xpos, Ypos, width, height):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load(picture).convert_alpha()
        self.image= pygame.transform.scale(self.image, (width, height))
        self.rect = self.image.get_rect(topleft = (Xpos, Ypos))

def main():
    plat1 = Platform(WIDTH, 30, WIDTH * 0.5, HEIGHT - 15)
    plat2 = Platform(WIDTH / 2, 50, WIDTH * 0.75, HEIGHT - 70)
    player = Player(50, 50)
    player.platforms_rects.append(plat1.rect)
    player.platforms_rects.append(plat2.rect)

    all_sprites = pygame.sprite.Group()
    all_sprites.add(plat1)
    all_sprites.add(plat2)
    all_sprites.add(player)

    pygame.display.set_caption("Game")
    background_surface = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    FPS = 60

    Map = Images('Assets\MenuScreen.png', 0, 0, 800, 600)
    
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        background_surface.blit(Map.image, Map.rect)

        player.physics()

        for entity in all_sprites:
            entity.update_ui()
            background_surface.blit(entity.surf, entity.rect)

        pygame.display.update()
        clock.tick(FPS)

main()

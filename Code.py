import pygame
from pygame.locals import *
import sys
from collections import deque

pygame.init()

Vec = pygame.math.Vector2  # 2 for two dimensional

HEIGHT = 600  # Screen height
WIDTH = 800  # Screen width
MAP_WIDTH = 2000  # Map width
ACC = 0.5  # Impact of user's keyboard on the acceleration
FRIC_X = -0.09  # Air resistance
FRIC_Y = -0.01

class Images(pygame.sprite.Sprite):
    def __init__(self, picture, Xpos, Ypos, width, height):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load(picture)
        self.image = pygame.transform.scale(self.image, (width, height))
        self.rect = self.image.get_rect(topleft = (Xpos, Ypos))

    def blit(self, background_surface: pygame.Surface, camera_x_offset):
        new_rect = self.rect.move(-camera_x_offset, 0)
        background_surface.blit(self.image, new_rect)

class ImageHorizontalTile(pygame.sprite.Sprite):
    def __init__(self, picture, x, y, width, height):
        super().__init__()
        img = pygame.image.load(picture)
        self.image = pygame.transform.scale_by(img, height / img.get_height())
        self.rect = pygame.Rect(x, y, width, height)
        self.img_width = self.image.get_width()
        self.height = height

    def blit(self, background_surface: pygame.Surface, camera_x_offset):
        new_rect = self.rect.move(-camera_x_offset, 0)
        r = range(new_rect.x, new_rect.right, self.img_width)
        for x in r[:-1]:
            background_surface.blit(self.image, (x, new_rect.y))
        background_surface.blit(
            self.image, (r[-1], new_rect.y),
            (0, 0, new_rect.right - r[-1], self.height)
        )

class TextElements():
    def __init__(self, font, size, colour, text, xpos, ypos):
        self.words = text
        self.colour = colour
        self.xpos = xpos
        self.ypos = ypos

        self.font = pygame.font.Font(font, size)
        self.text = self.font.render(self.words, True, colour)
        self.rect = self.text.get_rect(center=(xpos, ypos))

    def update(self, screen):
        self.text = self.font.render(self.words, True, self.colour)
        self.rect = self.text.get_rect(center=(self.xpos, self.ypos))
        screen.blit(self.text, self.rect)

class Player(Images):
    def __init__(self, x, y):
        self.width = 30
        self.height = 75
        super().__init__("images/Player.png", x, y, self.width, self.height)
        self.platforms = []

        self.pos = Vec((x, y))
        self.vel = Vec(0, 0)
        self.acc = Vec(0, 0)

    def blit(self, background_surface, camera_x_offset):
        self.rect.midbottom = self.pos
        return super().blit(background_surface, camera_x_offset)

    def physics(self):
        on_platform_rect = None
        min_x = max_x = None
        platform_resistance_factor = 1.0
        hitbox = self.rect.move(0, 1)
        for platform in self.platforms:
            plat_rect: pygame.Rect = platform.rect
            if hitbox.colliderect(plat_rect):
                # Collision from top
                if plat_rect.collidepoint(hitbox.midbottom):
                    on_platform_rect = plat_rect
                    platform_resistance_factor = platform.resistance_factor
                # Collision from left/right
                if plat_rect.collidepoint(hitbox.midright):
                    max_x = plat_rect.x - self.width / 2
                if plat_rect.collidepoint(hitbox.midleft):
                    min_x = plat_rect.x + self.width / 2

        self.acc = Vec(0, 0)
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_LEFT] or pressed_keys[K_a]:
            self.acc.x = -ACC
        if pressed_keys[K_RIGHT] or pressed_keys[K_d]:
            self.acc.x = ACC
        if pressed_keys[K_SPACE] and on_platform_rect is not None:
            self.acc.y = -7  # Up

        # Gravity
        if on_platform_rect is None:
            self.vel.y += 0.2
        else:
            # Prevent from going down on a platform
            self.vel.y = min(0, self.vel.y)

        # Prevent from going left or right if there is obstacle
        if min_x is not None:
            self.vel.x = max(0, self.vel.x)
        if max_x is not None:
            self.vel.x = min(0, self.vel.x)

        # Compute resistance
        resistance = Vec(FRIC_X, FRIC_Y)
        resistance.x *= platform_resistance_factor

        self.acc.x += self.vel.x * resistance.x
        self.acc.y += self.vel.y * resistance.y
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        if self.pos.x > MAP_WIDTH - self.width / 2:
            self.pos.x = MAP_WIDTH - self.width / 2
        if self.pos.x < self.width / 2:
            self.pos.x = self.width / 2

        if on_platform_rect is not None:
            # Prevent from going down on a platform
            self.pos[1] = min(on_platform_rect[1], self.pos[1])
        if min_x is not None:
            self.pos[0] = max(min_x, self.pos[0])
        if max_x is not None:
            self.pos[0] = min(max_x, self.pos[0])

class Shadow(Images):
    def __init__(self, x, y, countdown: int, player: Player):
        self.player = player
        super().__init__("images/Enemy.png", x, y, player.width, player.height)
        self.past_pos = deque()
        self.countdown = countdown

    def track(self):
        if self.countdown > 0:
            self.countdown -= 1
        self.past_pos.append(self.player.pos.copy())

    def blit(self, background_surface, camera_x_offset):
        if self.countdown <= 0:
            self.rect.midbottom = self.past_pos.popleft()
        return super().blit(background_surface, camera_x_offset)

class Platform(ImageHorizontalTile):
    resistance_factor = 1.0

class NormalPlatform(Platform):
    def __init__(self, width, height, x, y):
        # TODO change the image
        super().__init__("images/Cement.png", x, y, width, height)

class CementPlatform(Platform):
    resistance_factor = 1.5

    def __init__(self, width, height, x, y):
        super().__init__("images/Cement.png", x, y, width, height)

def main():
    plat1 = NormalPlatform(MAP_WIDTH, 30, 0, HEIGHT - 30)
    plat2 = CementPlatform(300, 20, 0, HEIGHT - 100)
    player = Player(50, 50)
    shadow = Shadow(50, 50, 100, player)
    player.platforms.append(plat1)
    player.platforms.append(plat2)

    all_sprites = pygame.sprite.Group()
    all_sprites.add(plat1)
    all_sprites.add(plat2)
    all_sprites.add(player)
    all_sprites.add(shadow)

    pygame.display.set_caption("Game")
    background_surface = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    FPS = 60

    Map = Images('images/GameScreen.png', 0, 0, 800, 600)

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        background_surface.blit(Map.image, Map.rect)

        player.physics()
        shadow.track()

        # Camera
        camera_x_offset = min(max(0, player.pos.x - WIDTH / 2),
                              MAP_WIDTH - WIDTH)

        for entity in all_sprites:
            entity.blit(background_surface, camera_x_offset)

        pygame.display.update()
        clock.tick(FPS)

def Menu():
    pygame.font.init()
    pygame.display.set_caption("Game")
    background_surface = pygame.display.set_mode((WIDTH, HEIGHT))

    clock = pygame.time.Clock()
    FPS = 60

    Map = Images('images/MenuScreen.png', 0, 0, 800, 600)
    playbutton = TextElements('images/Bauhaus93.ttf',40, (255,255,255),"Press Space to Play",400,250)
    NameGame = TextElements('images/Bauhaus93.ttf',60, (255,255,255),"Game Name",400,150)
    rectangle = pygame.Rect(350, 300,600,60)
    rectangle.center = (400,250)

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_SPACE]:
            main()
            break

        background_surface.blit(Map.image, Map.rect)
        pygame.draw.rect(background_surface,(0,0,0),rectangle)
        background_surface.blit(playbutton.text, playbutton.rect)
        background_surface.blit(NameGame.text, NameGame.rect)

        pygame.display.update()
        clock.tick(FPS)

Menu()

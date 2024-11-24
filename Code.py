import pygame
from pygame.locals import *
import sys
from collections import deque

pygame.init()

Vec = pygame.math.Vector2  # 2 for two dimensional

HEIGHT = 600  # Screen height
WIDTH = 800  # Screen width
ACC = 0.5  # Impact of user's keyboard on the acceleration
FRIC_X = -0.09  # Air resistance
FRIC_Y = -0.01

class Images(pygame.sprite.Sprite):
    def __init__(self, picture, Xpos, Ypos, width, height):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load(picture)
        self.image = pygame.transform.scale(self.image, (width, height))
        self.initial_pos = (Xpos, Ypos)
        self.rect = self.image.get_rect(topleft=self.initial_pos)

    def reset(self):
        self.rect.topleft = self.initial_pos

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
    def __init__(self, x, y, map_width):
        self.width = 30
        self.height = 75
        self.map_width = map_width
        super().__init__("images/Player.png", x, y, self.width, self.height)
        self.platforms = []

        self.right_boundary = self.map_width - self.width / 2
        self.left_boundary = self.width / 2

        self.reset()

    def reset(self):
        super().reset()
        self.pos = Vec(self.initial_pos)
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
            self.image = pygame.image.load('images/PlayerLeft.png')
            self.image = pygame.transform.scale(self.image, (30, 70))
        if pressed_keys[K_RIGHT] or pressed_keys[K_d]:
            self.acc.x = ACC
            self.image = pygame.image.load('images/Player.png')
            self.image = pygame.transform.scale(self.image, (30, 70))
        if (
            (pressed_keys[K_w] or pressed_keys[K_UP] or pressed_keys[K_SPACE])
            and on_platform_rect is not None
        ):
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

        self.pos.x = max(
            min(self.pos.x, self.right_boundary), self.left_boundary
        )

        if on_platform_rect is not None:
            # Prevent from going down on a platform
            self.pos[1] = min(on_platform_rect[1], self.pos[1])
        if min_x is not None:
            self.pos[0] = max(min_x, self.pos[0])
        if max_x is not None:
            self.pos[0] = min(max_x, self.pos[0])

    def check_collision_with_shadow(self, shadow_rect) -> bool:
        return self.rect.colliderect(shadow_rect)

    def is_in_void(self) -> bool:
        return self.pos.y > HEIGHT

class Shadow(Images):
    def __init__(self, x, y, countdown: int, player: Player):
        self.player = player
        super().__init__("images/Enemy.png", x, y, player.width, player.height)
        self.initial_countdown = countdown
        self.reset()

    def reset(self):
        super().reset()
        self.past_pos = deque()
        self.countdown = self.initial_countdown

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

class IcePlatform(Platform):
    resistance_factor = 0.75

    def __init__(self, width, height, x, y):
        # TODO change the image
        super().__init__("images/Cement.png", x, y, width, height)

class Level:
    def __init__(
        self,
        name: str,
        platforms,
        map_width: int,
        spawn_x: int, spawn_y: int,
        shadow_countdown: int,
        health: int,
    ):
        self.name = name
        self.platforms = platforms
        self.map_width = map_width
        self.player = Player(spawn_x, spawn_y, map_width)
        # The shadow is initially outside screen.
        self.shadow = Shadow(-100, 0, shadow_countdown, self.player)
        self.health = health

        self.player.platforms.extend(platforms)
        self.all_sprites = pygame.sprite.Group()
        for platform in platforms:
            self.all_sprites.add(platform)
        self.all_sprites.add(self.player)
        self.all_sprites.add(self.shadow)

    def reset(self):
        self.player.reset()
        self.shadow.reset()
        self.health -= 1
        print(self.health)

    def tick(self, background_surface):
        # Subroutine loops
        self.player.physics()
        self.shadow.track()
        # Camera
        camera_x_offset = min(max(0, self.player.pos.x - WIDTH / 2),
                              self.map_width - WIDTH)
        for entity in self.all_sprites:
            entity.blit(background_surface, camera_x_offset)
        # Check player's collision with the shadow
        if self.player.check_collision_with_shadow(self.shadow.rect):
            self.reset()
        # Check if player is in the void
        if self.player.is_in_void():
            self.reset()

def main(level: Level):
    pygame.display.set_caption(f"Game - {level.name}")
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
        level.tick(background_surface)
        pygame.display.update()
        clock.tick(FPS)

TEST_LEVEL = Level(
    "Test level",
    (
        NormalPlatform(1500, 30, 0, HEIGHT - 30),
        IcePlatform(300, 20, 0, HEIGHT - 100),
    ),
    2000,
    50, 0,
    100,
    3,
)

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
            main(TEST_LEVEL)
            break

        background_surface.blit(Map.image, Map.rect)
        pygame.draw.rect(background_surface,(0,0,0),rectangle)
        background_surface.blit(playbutton.text, playbutton.rect)
        background_surface.blit(NameGame.text, NameGame.rect)

        pygame.display.update()
        clock.tick(FPS)

Menu()

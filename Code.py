import pygame
from pygame.locals import *
import sys
from collections import deque
from typing import NamedTuple

pygame.init()

Vec = pygame.math.Vector2  # 2 for two dimensional

HEIGHT = 600  # Screen height
WIDTH = 800  # Screen width
ACC = 0.5  # Impact of user's keyboard on the acceleration
FRIC_X = -0.09  # Air resistance
FRIC_Y = -0.01

class Images(pygame.sprite.Sprite):
    _img_cache = {}

    def __init__(self, picture, Xpos, Ypos, width, height):
        pygame.sprite.Sprite.__init__(self)
        self.image_size = (width, height)
        self._my_cache = self._img_cache.setdefault(type(self), {})
        self.reset_texture(picture)
        self.initial_pos = (Xpos, Ypos)
        self.rect = self.image.get_rect(topleft=self.initial_pos)

    def reset_texture(self, picture):
        cache_key = (picture, self.image_size)
        if cache_key in self._my_cache:
            self.image = self._my_cache[cache_key]
        else:
            self._my_cache[cache_key] = self.image = pygame.transform.scale(
                pygame.image.load(picture), self.image_size
            )

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
        self.obstacles = []
        self.turning_left = False

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
        for obstacle in self.obstacles:
            plat_rect: pygame.Rect = obstacle.rect
            if hitbox.colliderect(plat_rect):
                # Collision from top
                if plat_rect.collidepoint(hitbox.midbottom):
                    on_platform_rect = plat_rect
                    platform_resistance_factor = obstacle.resistance_factor
                # Collision from left/right
                if plat_rect.collidepoint(hitbox.midright):
                    max_x = plat_rect.x - self.width / 2
                if plat_rect.collidepoint(hitbox.midleft):
                    min_x = plat_rect.x + self.width / 2

        self.acc = Vec(0, 0)
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_LEFT] or pressed_keys[K_a]:
            self.acc.x = -ACC
            self.turning_left = True
            self.reset_texture('images/PlayerLeft.png')
        if pressed_keys[K_RIGHT] or pressed_keys[K_d]:
            self.acc.x = ACC
            self.turning_left = False
            self.reset_texture('images/Player.png')
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

    def is_in_void(self) -> bool:
        return self.pos.y > HEIGHT

class MovementRecord(NamedTuple):
    pos: Vec
    left: bool

class Shadow(Images):
    def __init__(self, x, y, countdown: int, player: Player):
        self.player = player
        super().__init__("images/Enemy.png", x, y, player.width, player.height)
        self.initial_countdown = countdown
        self.reset()
        self.turning_left = False

    def reset(self):
        super().reset()
        self.past_movements = deque()
        self.countdown = self.initial_countdown

    def track(self):
        if self.countdown > 0:
            self.countdown -= 1
        self.past_movements.append(MovementRecord(
            self.player.pos.copy(),
            self.player.turning_left
        ))

    def blit(self, background_surface, camera_x_offset):
        if self.countdown <= 0:
            record: MovementRecord = self.past_movements.popleft()
            self.rect.midbottom = record.pos
            if record.left:
                self.reset_texture("images/EnemyLeft.png")
            else:
                self.reset_texture("images/Enemy.png")
        return super().blit(background_surface, camera_x_offset)

class Platform(ImageHorizontalTile):
    resistance_factor = 1.0

class NormalPlatform(Platform):
    def __init__(self, width, height, x, y):
        # TODO change the image
        super().__init__("images/Platform.png", x, y, width, height)

class CementPlatform(Platform):
    resistance_factor = 3

    def __init__(self, width, height, x, y):
        super().__init__("images/Cement.png", x, y, width, height)

class IcePlatform(Platform):
    resistance_factor = 0.4

    def __init__(self, width, height, x, y):
        # TODO change the image
        super().__init__("images/Ice.png", x, y, width, height)

class Key(Images):
    def __init__(self, x, y):
        super().__init__("images/Key.png", x, y, 30, 30)
        self.used = False

    def reset(self):
        self.used = False

    def on_picked_up(self):
        self.used = True

    def blit(self, background_surface, camera_x_offset):
        if not self.used:
            super().blit(background_surface, camera_x_offset)

class Door(Images):
    resistance_factor = 1.0

    def __init__(self, x, y):
        super().__init__("images/LockedDoor.png", x, y, 150, 150)
        self.unlocked = False

    def reset(self):
        self.unlocked = False

    def on_unlocked(self):
        self.unlocked = True

    def blit(self, background_surface, camera_x_offset):
        if not self.unlocked:
            super().blit(background_surface, camera_x_offset)

class Goal(Images):
    def __init__(self, x, y):
        super().__init__("images/GoalFlag.png", x, y, 50, 75)

class Level:
    def __init__(
        self,
        name: str,
        platforms,
        map_width: int,
        spawn_x: int, spawn_y: int,
        goal_x: int, goal_y: int,
        shadow_countdown: int,
        health: int,
        key_door_pairs,
    ):
        self.name = name
        self.platforms = platforms
        self.map_width = map_width
        self.player = Player(spawn_x, spawn_y, map_width)
        # The shadow is initially outside screen.
        self.shadow = Shadow(-100, 0, shadow_countdown, self.player)
        self.goal = Goal(goal_x, goal_y)
        self.health = self.initial_health = health
        self.key_door_pairs = key_door_pairs
        self.dirty = False
        self.won = False

        self.player.obstacles.extend(platforms)
        self.player.obstacles.extend(door for _, door in key_door_pairs)
        self.all_sprites = pygame.sprite.Group()
        for platform in platforms:
            self.all_sprites.add(platform)
        self.all_sprites.add(self.player, self.shadow, self.goal)
        self.add_keys_and_doors()

    def add_keys_and_doors(self):
        for key, door in self.key_door_pairs:
            self.all_sprites.add(key, door)

    def hard_reset(self):
        self.reset()
        self.won = False
        self.dirty = False
        self.health = self.initial_health

    def reset(self):
        self.player.reset()
        self.shadow.reset()
        self.add_keys_and_doors()
        for key, door in self.key_door_pairs:
            if key.used:
                self.player.obstacles.append(door)
                key.reset()
                door.reset()

    def tick(self, background_surface):
        # Subroutine loops
        self.player.physics()
        self.shadow.track()
        # Camera
        camera_x_offset = min(max(0, self.player.pos.x - WIDTH / 2),
                              self.map_width - WIDTH)
        for entity in self.all_sprites:
            entity.blit(background_surface, camera_x_offset)
        # Check if key is picked up
        for key, door in self.key_door_pairs:
            if not key.used and self.player.rect.colliderect(key.rect):
                key.on_picked_up()
                door.on_unlocked()
                self.player.obstacles.remove(door)
        # Check if player is dead
        if (
            self.player.is_in_void()
            or self.player.rect.colliderect(self.shadow.rect)
        ):
            self.reset()
            self.health -= 1
        # Check if player won
        if self.player.rect.colliderect(self.goal.rect):
            self.won = True

class Game:
    def __init__(self, levels):
        self.levels = levels
        self.level_id = 0
        self.title = "Nighttime Chase"

    def run_level(self, level: Level):
        if level.dirty:
            level.hard_reset()
        level.dirty = True
        pygame.display.set_caption(
            f"{self.title} - Level {self.level_id + 1}. {level.name}"
        )
        background_surface = pygame.display.set_mode((WIDTH, HEIGHT))
        clock = pygame.time.Clock()
        FPS = 60

        Map = Images('images/GameScreen.png', 0, 0, 800, 600)

        while True:
            
            LivesRemaining = TextElements('images/Bauhaus93.ttf', 30, (255,255,255),f"LIVES: {level.health}", 70, 50)
            CurrentLevel = TextElements('images/Bauhaus93.ttf', 30, (255,255,255),f"{level.name}", 730, 50)

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            background_surface.blit(Map.image, Map.rect)
            background_surface.blit(LivesRemaining.text, LivesRemaining.rect)
            background_surface.blit(CurrentLevel.text, CurrentLevel.rect)
            level.tick(background_surface)
            pygame.display.update()
            clock.tick(FPS)

            if level.health <= 0:
                return False
            if level.won:
                return True

    def reset_caption(self):
        pygame.display.set_caption(self.title)

    def victory_screen(self):
        pygame.display.set_caption(f"{self.title} - You beat the game!!")
        background_surface = pygame.display.set_mode((WIDTH, HEIGHT))
        clock = pygame.time.Clock()
        FPS = 60
        Map = Images('images/MenuScreen.png', 0, 0, 800, 600)
        playbutton = TextElements('images/Bauhaus93.ttf',40, (255,255,255),"Press Space to Replay",400,250)
        NameGame = TextElements('images/Bauhaus93.ttf',60, (255,255,255),"You Win!!",400,150)
        rectangle = pygame.Rect(350, 300,600,60)
        rectangle.center = (400,250)
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
            pressed_keys = pygame.key.get_pressed()
            if pressed_keys[K_SPACE]:
                break
            background_surface.blit(Map.image, Map.rect)
            pygame.draw.rect(background_surface,(0,0,0),rectangle)
            background_surface.blit(playbutton.text, playbutton.rect)
            background_surface.blit(NameGame.text, NameGame.rect)
            pygame.display.update()
            clock.tick(FPS)

    def game_over_screen(self):
        pygame.display.set_caption(f"{self.title} - Game Over!")
        background_surface = pygame.display.set_mode((WIDTH, HEIGHT))
        clock = pygame.time.Clock()
        FPS = 60
        Map = Images('images/MenuScreen.png', 0, 0, 800, 600)
        playbutton = TextElements('images/Bauhaus93.ttf',40, (255,255,255),"Press Space to Replay",400,250)
        NameGame = TextElements('images/Bauhaus93.ttf',60, (255,255,255),"You Lose",400,150)
        rectangle = pygame.Rect(350, 300,600,60)
        rectangle.center = (400,250)
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
            pressed_keys = pygame.key.get_pressed()
            if pressed_keys[K_SPACE]:
                break
            background_surface.blit(Map.image, Map.rect)
            pygame.draw.rect(background_surface,(0,0,0),rectangle)
            background_surface.blit(playbutton.text, playbutton.rect)
            background_surface.blit(NameGame.text, NameGame.rect)
            pygame.display.update()
            clock.tick(FPS)

    def hard_reset(self):
        self.reset_caption()
        self.level_id = 0

    def main(self):
        pygame.font.init()
        self.reset_caption()
        background_surface = pygame.display.set_mode((WIDTH, HEIGHT))

        clock = pygame.time.Clock()
        FPS = 60

        Map = Images('images/MenuScreen.png', 0, 0, 800, 600)
        playbutton = TextElements('images/Bauhaus93.ttf', 40, (255,255,255),"Press Space to Play",400,250)
        NameGame = TextElements('images/Bauhaus93.ttf', 60, (255,255,255),self.title,400,150)
        rectangle = pygame.Rect(350, 300, 600, 60)
        rectangle.center = (400, 250)

        self.level_id = 0

        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN and event.key == K_SPACE:
                    while True:
                        won = self.run_level(self.levels[self.level_id])
                        if won:
                            self.level_id += 1
                            if self.level_id == len(self.levels):
                                # Beat the game!
                                self.victory_screen()
                                self.hard_reset()
                        else:
                            self.game_over_screen()
                            self.hard_reset()
            background_surface.blit(Map.image, Map.rect)
            pygame.draw.rect(background_surface,(0,0,0),rectangle)
            background_surface.blit(playbutton.text, playbutton.rect)
            background_surface.blit(NameGame.text, NameGame.rect)

            pygame.display.update()
            clock.tick(FPS)

TEST_LEVEL = Level(
    "Test level",
    (
        NormalPlatform(300, 30, 0, HEIGHT - 30),
        CementPlatform(300, 30, 300, HEIGHT - 30),
        NormalPlatform(300, 30, 000, HEIGHT - 330),
        NormalPlatform(200, 30, 790, HEIGHT - 130),
        IcePlatform(100, 30, 1200, HEIGHT - 230),
        IcePlatform(200, 30, 750, HEIGHT - 330),
        CementPlatform(200, 30, 550, HEIGHT - 330),
        IcePlatform(200, 30, 1200, HEIGHT - 430),
        IcePlatform(200, 30, 1650, HEIGHT - 530),
        CementPlatform(300, 30, 2500, HEIGHT - 30),
        CementPlatform(300, 30, 2950, HEIGHT - 130),
        CementPlatform(300, 30, 3400, HEIGHT - 230),
        CementPlatform(300, 30, 3850, HEIGHT - 330),
        NormalPlatform(400, 30, 4600, HEIGHT - 30),
    ),
    5000,
    50, 450,
    4900, HEIGHT - 120,
    100,
    3,
    (
        (Key(100, HEIGHT - 380), Door(4820, HEIGHT - 180)),
    )
)

Level_1 = Level(
    "LEVEL 1",
    (
        NormalPlatform(1500, 30, 0, HEIGHT - 30),
        NormalPlatform(700, 30, 1800, HEIGHT - 30),
        NormalPlatform(400, 30, 2800, HEIGHT - 30),
        NormalPlatform(75,100,400,HEIGHT - 130),
        NormalPlatform(75,100,1000,HEIGHT - 130),
        NormalPlatform(75,200,1200,HEIGHT - 230),
        NormalPlatform(75,100,2425,HEIGHT - 130),
        NormalPlatform(75,100,2800,HEIGHT - 130),
    ),
    3200,
    50, 450,
    3100, HEIGHT - 120,
    100,
    3,
    ()
)

Level_2 = Level(
    "LEVEL 2",
    (
        NormalPlatform(300, 30, 0, HEIGHT - 30),
        CementPlatform(500, 30, 300, HEIGHT - 30),
        CementPlatform(475, 30, 1100, HEIGHT - 30),
        CementPlatform(75, 100, 1300, HEIGHT - 130),
        CementPlatform(75, 200, 1500, HEIGHT - 230),
        CementPlatform(200, 30, 1700, HEIGHT - 300),
        CementPlatform(600, 30, 2400, HEIGHT - 30),
    ),
    3000,
    50, 450,
    2900, HEIGHT - 120,
    100,
    3,
    ()
)

Level_3 = Level(
    "LEVEL 3",
    (
        NormalPlatform(300, 30, 0, HEIGHT - 30),
        IcePlatform(300, 30, 300, HEIGHT - 30),
        IcePlatform(500, 30, 1000, HEIGHT - 30),
        IcePlatform(500, 30, 1750, HEIGHT - 130),
        IcePlatform(500, 30, 1000, HEIGHT - 230),
        IcePlatform(500, 30, 1750, HEIGHT - 330),
        NormalPlatform(350, 30, 2850, HEIGHT - 30),
    ),
    3200,
    50, 450,
    3100, HEIGHT - 120,
    100,
    3,
    ()
)

Level_4 = Level(
    "LEVEL 4",
    (
        NormalPlatform(500, 30, 0, HEIGHT - 30),
        NormalPlatform(300, 30, 0, HEIGHT - 330),
        NormalPlatform(300, 30, 800, HEIGHT - 30),
        NormalPlatform(300, 30, 1300, HEIGHT - 130),
        NormalPlatform(300, 30, 1800, HEIGHT - 230),
        NormalPlatform(300, 30, 2300, HEIGHT - 330),
        NormalPlatform(300, 30, 1800, HEIGHT - 430),
        NormalPlatform(300, 30, 1300, HEIGHT - 430),
        NormalPlatform(300, 30, 800, HEIGHT - 430),
        NormalPlatform(200, 30, 500, HEIGHT - 330),
        NormalPlatform(350, 30, 2850, HEIGHT - 30),
    ),
    3200,
    50, 450,
    3100, HEIGHT - 120,
    100,
    3,
    (
        (Key(100, HEIGHT - 380), Door(3000, HEIGHT - 180)),
    )
)

Level_5 = Level(
    "LEVEL 5",
    (
        NormalPlatform(300, 30, 0, HEIGHT - 30),
        CementPlatform(300, 30, 300, HEIGHT - 30),
        NormalPlatform(300, 30, 000, HEIGHT - 330),
        NormalPlatform(200, 30, 790, HEIGHT - 130),
        IcePlatform(100, 30, 1200, HEIGHT - 230),
        IcePlatform(200, 30, 750, HEIGHT - 330),
        CementPlatform(200, 30, 550, HEIGHT - 330),
        IcePlatform(200, 30, 1200, HEIGHT - 430),
        IcePlatform(200, 30, 1650, HEIGHT - 530),
        CementPlatform(300, 30, 2500, HEIGHT - 30),
        CementPlatform(300, 30, 2950, HEIGHT - 130),
        CementPlatform(300, 30, 3400, HEIGHT - 230),
        CementPlatform(300, 30, 3850, HEIGHT - 330),
        NormalPlatform(400, 30, 4600, HEIGHT - 30),
    ),
    5000,
    50, 450,
    4900, HEIGHT - 120,
    100,
    3,
    (
        (Key(100, HEIGHT - 380), Door(4820, HEIGHT - 180)),
    )
)
Game((
    Level_1, Level_2, Level_3, Level_4, Level_5
)).main()

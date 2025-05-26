import pygame
import random
import math
import sys
import os
from enum import Enum
from dataclasses import dataclass

# Initialize pygame
pygame.init()
pygame.mixer.init()


# Constants and configurations
@dataclass
class Config:
    SCREEN_WIDTH: int = 800
    SCREEN_HEIGHT: int = 600
    FPS: int = 60
    BG_COLOR: tuple = (0, 0, 20)
    PLAYER_SPEED: int = 5
    BULLET_SPEED: int = 10
    ENEMY_SPEED: int = 2
    FONT_SIZE: int = 32

    # Colors
    WHITE: tuple = (255, 255, 255)
    RED: tuple = (255, 0, 0)
    GREEN: tuple = (0, 255, 0)
    BLUE: tuple = (0, 100, 255)
    YELLOW: tuple = (255, 255, 0)
    PURPLE: tuple = (255, 0, 255)

    # Paths
    ASSETS_DIR: str = "assets"
    SOUNDS_DIR: str = os.path.join(ASSETS_DIR, "sounds")
    IMAGES_DIR: str = os.path.join(ASSETS_DIR, "images")

    @staticmethod
    def init_assets():
        """Initialize asset paths and ensure directories exist"""
        os.makedirs(Config.SOUNDS_DIR, exist_ok=True)
        os.makedirs(Config.IMAGES_DIR, exist_ok=True)


class Difficulty(Enum):
    EASY = {"enemies": 5, "speed": 1, "health": 1, "name": "Легко"}
    NORMAL = {"enemies": 8, "speed": 1.5, "health": 2, "name": "Нормально"}
    HARD = {"enemies": 12, "speed": 2, "health": 3, "name": "Сложно"}


class GameState(Enum):
    MENU = "menu"
    GAME = "game"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    STORY = "story"
    UPGRADE = "upgrade"


class Entity(pygame.sprite.Sprite):
    """Base class for all game entities"""

    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.health = 1
        self.max_health = 1

    def draw_health(self, surface):
        if self.health < self.max_health:
            health_width = self.rect.width * (self.health / self.max_health)
            pygame.draw.rect(surface, Config.RED, (self.rect.x, self.rect.y - 10, self.rect.width, 5))
            pygame.draw.rect(surface, Config.GREEN, (self.rect.x, self.rect.y - 10, health_width, 5))


class Player(Entity):
    def __init__(self):
        super().__init__(
            Config.SCREEN_WIDTH // 2 - 25,
            Config.SCREEN_HEIGHT - 50,
            50, 40, Config.BLUE
        )
        self.speed = Config.PLAYER_SPEED
        self.health = 100
        self.max_health = 100
        self.bullets = pygame.sprite.Group()
        self.shoot_delay = 250  # ms between shots
        self.last_shot = pygame.time.get_ticks()
        self.upgrades = {
            "speed": 1,
            "damage": 1,
            "fire_rate": 1,
            "shield": 0  # New upgrade - temporary invulnerability
        }
        self.shield_active = False
        self.shield_timer = 0
        self.shield_duration = 3000  # 3 seconds

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed * self.upgrades["speed"]
        if keys[pygame.K_RIGHT] and self.rect.right < Config.SCREEN_WIDTH:
            self.rect.x += self.speed * self.upgrades["speed"]
        if keys[pygame.K_UP] and self.rect.top > 0:
            self.rect.y -= self.speed * self.upgrades["speed"]
        if keys[pygame.K_DOWN] and self.rect.bottom < Config.SCREEN_HEIGHT:
            self.rect.y += self.speed * self.upgrades["speed"]

        # Update shield
        if self.shield_active:
            self.shield_timer += 1000 / Config.FPS
            if self.shield_timer >= self.shield_duration:
                self.shield_active = False
                self.shield_timer = 0

    def shoot(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.shoot_delay / self.upgrades["fire_rate"]:
            self.last_shot = now
            bullet = Bullet(self.rect.centerx, self.rect.top)
            bullet.damage *= self.upgrades["damage"]
            self.bullets.add(bullet)
            return bullet
        return None

    def activate_shield(self):
        if self.upgrades["shield"] > 0:
            self.shield_active = True
            self.shield_timer = 0


class Bullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 5, 15, Config.YELLOW)
        self.speed = Config.BULLET_SPEED
        self.damage = 10
        self.rect.centerx = x
        self.rect.bottom = y

    def update(self):
        self.rect.y -= self.speed
        if self.rect.bottom < 0:
            self.kill()


class Enemy(Entity):
    def __init__(self, difficulty, x=None, y=None):
        super().__init__(
            x if x is not None else random.randrange(Config.SCREEN_WIDTH - 40),
            y if y is not None else random.randrange(-100, -40),
            40, 40, Config.RED
        )
        self.speed = Config.ENEMY_SPEED * difficulty["speed"]
        self.health = difficulty["health"]
        self.max_health = difficulty["health"]
        self.difficulty = difficulty

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > Config.SCREEN_HEIGHT:
            self.reset_position()

    def reset_position(self):
        self.rect.x = random.randrange(Config.SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)


class Boss(Enemy):
    def __init__(self, difficulty):
        super().__init__(difficulty, Config.SCREEN_WIDTH // 2 - 40, -100)
        self.image = pygame.Surface((80, 80))
        self.image.fill(Config.PURPLE)
        self.health = 50 * difficulty["health"]
        self.max_health = self.health
        self.pattern = 0
        self.pattern_timer = 0
        self.attack_timer = 0
        self.attack_delay = 1000  # ms between attacks

    def update(self):
        self.pattern_timer += 1
        self.attack_timer += 1000 / Config.FPS

        # Movement patterns
        if self.pattern == 0:  # Entrance
            self.rect.y += 1
            if self.rect.top > 50:
                self.pattern = 1
        elif self.pattern == 1:  # Side-to-side
            self.rect.x += math.sin(self.pattern_timer * 0.05) * 3
            if self.pattern_timer > 200:
                self.pattern = 2
                self.pattern_timer = 0
        elif self.pattern == 2:  # Circular
            angle = self.pattern_timer * 0.05
            self.rect.x = Config.SCREEN_WIDTH // 2 + math.sin(angle) * 200
            self.rect.y = 100 + math.cos(angle) * 50
            if self.pattern_timer > 300:
                self.pattern = 1
                self.pattern_timer = 0

        # Attack logic
        if self.attack_timer >= self.attack_delay:
            self.attack_timer = 0
            return True  # Signal to spawn enemy bullets
        return False


class StoryManager:
    """Manages the game's story progression"""

    def __init__(self):
        self.chapters = [
            "Глава 1: Начало\n\nВаша миссия - защитить Землю от вторжения инопланетян.",
            "Глава 2: Первая волна\n\nРазведчики обнаружили ваш корабль. Будьте осторожны!",
            "Глава 3: Усиление\n\nВраг посылает более мощные корабли.",
            "Глава 4: Босс\n\nПриготовьтесь к встрече с линкором противника!",
            "Глава 5: Финальная битва\n\nЭто ваша последняя миссия. Удачи, командир!"
        ]
        self.current_chapter = 0

    def get_current_story(self):
        if self.current_chapter < len(self.chapters):
            return self.chapters[self.current_chapter]
        return None

    def advance_story(self):
        self.current_chapter += 1
        return self.current_chapter < len(self.chapters)


class QuadTree:
    """Simple QuadTree implementation for collision optimization"""

    def __init__(self, boundary, capacity):
        self.boundary = boundary  # (x, y, width, height)
        self.capacity = capacity
        self.objects = []
        self.divided = False

    def subdivide(self):
        x, y, w, h = self.boundary
        nw = (x, y, w / 2, h / 2)
        ne = (x + w / 2, y, w / 2, h / 2)
        sw = (x, y + h / 2, w / 2, h / 2)
        se = (x + w / 2, y + h / 2, w / 2, h / 2)

        self.northwest = QuadTree(nw, self.capacity)
        self.northeast = QuadTree(ne, self.capacity)
        self.southwest = QuadTree(sw, self.capacity)
        self.southeast = QuadTree(se, self.capacity)
        self.divided = True

    def insert(self, obj):
        if not self._intersects(obj.rect):
            return False

        if len(self.objects) < self.capacity:
            self.objects.append(obj)
            return True

        if not self.divided:
            self.subdivide()

        return (self.northwest.insert(obj) or
                self.northeast.insert(obj) or
                self.southwest.insert(obj) or
                self.southeast.insert(obj))

    def _intersects(self, rect):
        x, y, w, h = self.boundary
        return not (rect.right < x or
                    rect.left > x + w or
                    rect.bottom < y or
                    rect.top > y + h)

    def query(self, rect, found=None):
        if found is None:
            found = []

        if not self._intersects(rect):
            return found

        for obj in self.objects:
            if rect.colliderect(obj.rect):
                found.append(obj)

        if self.divided:
            self.northwest.query(rect, found)
            self.northeast.query(rect, found)
            self.southwest.query(rect, found)
            self.southeast.query(rect, found)

        return found


class ParticleSystem:
    """Simple particle system for visual effects"""

    def __init__(self):
        self.particles = []

    def add_explosion(self, x, y, color, count=20):
        for _ in range(count):
            self.particles.append({
                'x': x,
                'y': y,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'life': random.randint(20, 40),
                'color': color,
                'size': random.randint(2, 5)
            })

    def update(self):
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.particles.remove(particle)

    def draw(self, surface):
        for particle in self.particles:
            pygame.draw.circle(
                surface,
                particle['color'],
                (int(particle['x']), int(particle['y'])),
                particle['size']
            )


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        pygame.display.set_caption("Космический шутер")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, Config.FONT_SIZE)
        self.big_font = pygame.font.Font(None, 64)
        self.difficulty = Difficulty.NORMAL
        self.level = 1
        self.score = 0
        self.high_score = 0
        self.state = GameState.MENU
        self.story_manager = StoryManager()
        self.particle_system = ParticleSystem()
        self.quadtree = QuadTree((0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT), 4)
        self.load_assets()

    def load_assets(self):
        """Load game assets (placeholder - implement actual asset loading)"""
        Config.init_assets()
        # In a real game, you would load images and sounds here
        # Example:
        # self.player_image = pygame.image.load(os.path.join(Config.IMAGES_DIR, "player.png"))
        # self.shoot_sound = pygame.mixer.Sound(os.path.join(Config.SOUNDS_DIR, "shoot.wav"))

    def new_game(self):
        self.player = Player()
        self.enemies = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group(self.player)
        self.score = 0
        self.level = 1
        self.story_manager.current_chapter = 0
        self.state = GameState.STORY
        self.spawn_enemies()

    def spawn_enemies(self):
        diff = self.difficulty.value
        count = diff["enemies"] + self.level

        for i in range(count):
            if self.level % 5 == 0 and i == 0:  # Boss every 5 levels
                enemy = Boss(diff)
            else:
                enemy = Enemy(diff)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)

    def show_menu(self):
        self.screen.fill(Config.BG_COLOR)

        title = self.big_font.render("КОСМИЧЕСКИЙ ШУТЕР", True, Config.WHITE)
        start = self.font.render("1 - Новая игра (Легко)", True, Config.GREEN)
        start2 = self.font.render("2 - Новая игра (Нормально)", True, Config.YELLOW)
        start3 = self.font.render("3 - Новая игра (Сложно)", True, Config.RED)
        high_score = self.font.render(f"Рекорд: {self.high_score}", True, Config.WHITE)
        quit_text = self.font.render("ESC - Выход", True, Config.WHITE)

        self.screen.blit(title, (Config.SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        self.screen.blit(start, (Config.SCREEN_WIDTH // 2 - start.get_width() // 2, 200))
        self.screen.blit(start2, (Config.SCREEN_WIDTH // 2 - start2.get_width() // 2, 250))
        self.screen.blit(start3, (Config.SCREEN_WIDTH // 2 - start3.get_width() // 2, 300))
        self.screen.blit(high_score, (Config.SCREEN_WIDTH // 2 - high_score.get_width() // 2, 350))
        self.screen.blit(quit_text, (Config.SCREEN_WIDTH // 2 - quit_text.get_width() // 2, 400))

        pygame.display.flip()

    def show_story(self):
        self.screen.fill(Config.BG_COLOR)
        story_text = self.story_manager.get_current_story()

        if story_text:
            lines = story_text.split('\n')
            y_pos = 150
            for line in lines:
                text = self.font.render(line, True, Config.WHITE)
                self.screen.blit(text, (Config.SCREEN_WIDTH // 2 - text.get_width() // 2, y_pos))
                y_pos += 40

            continue_text = self.font.render("Нажмите ПРОБЕЛ для продолжения", True, Config.YELLOW)
            self.screen.blit(continue_text, (Config.SCREEN_WIDTH // 2 - continue_text.get_width() // 2, 450))
        else:
            self.state = GameState.GAME

        pygame.display.flip()

    def show_hud(self):
        score_text = self.font.render(f"Очки: {self.score}", True, Config.WHITE)
        level_text = self.font.render(f"Уровень: {self.level}", True, Config.WHITE)

        # Draw health bar
        health_width = 200 * (self.player.health / self.player.max_health)
        pygame.draw.rect(self.screen, Config.RED, (10, 10, 200, 20))
        pygame.draw.rect(self.screen, Config.GREEN, (10, 10, health_width, 20))

        # Draw shield indicator if active
        if self.player.shield_active:
            shield_text = self.font.render("ЩИТ АКТИВЕН", True, Config.BLUE)
            self.screen.blit(shield_text, (Config.SCREEN_WIDTH - 150, 10))

        self.screen.blit(score_text, (10, 40))
        self.screen.blit(level_text, (10, 70))

    def check_collisions(self):
        # Update quadtree
        self.quadtree = QuadTree((0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT), 4)
        for enemy in self.enemies:
            self.quadtree.insert(enemy)

        # Check bullet-enemy collisions using quadtree
        for bullet in self.player.bullets:
            potential_collisions = self.quadtree.query(bullet.rect)
            for enemy in potential_collisions:
                if pygame.sprite.collide_rect(bullet, enemy):
                    enemy.health -= bullet.damage
                    bullet.kill()
                    self.particle_system.add_explosion(
                        bullet.rect.centerx, bullet.rect.centery,
                        Config.YELLOW
                    )

                    if enemy.health <= 0:
                        self.score += 10 * (5 if isinstance(enemy, Boss) else 1)
                        enemy.kill()
                        self.particle_system.add_explosion(
                            enemy.rect.centerx, enemy.rect.centery,
                            Config.RED, 40
                        )

                        # Chance for upgrade
                        if random.random() < 0.1:
                            self.show_upgrade_screen()

        # Player-enemy collisions
        if not self.player.shield_active:
            hits = pygame.sprite.spritecollide(self.player, self.enemies, True)
            for hit in hits:
                self.player.health -= 20
                self.particle_system.add_explosion(
                    hit.rect.centerx, hit.rect.centery,
                    Config.RED, 30
                )
                if self.player.health <= 0:
                    self.game_over()

        # Level completion check
        if len(self.enemies) == 0:
            self.level_complete()

    def level_complete(self):
        self.level += 1
        self.player.health = min(self.player.max_health, self.player.health + 20)

        # Every 3 levels increase difficulty
        if self.level % 3 == 0:
            for enemy in self.enemies:
                enemy.speed *= 1.1

        # Show story every 5 levels
        if self.level % 5 == 0 and self.story_manager.advance_story():
            self.state = GameState.STORY
        else:
            self.spawn_enemies()

        # Victory after 15 levels
        if self.level > 15:
            self.victory()

    def game_over(self):
        self.state = GameState.GAME_OVER
        if self.score > self.high_score:
            self.high_score = self.score

    def victory(self):
        self.state = GameState.VICTORY
        if self.score > self.high_score:
            self.high_score = self.score

    def show_upgrade_screen(self):
        self.state = GameState.UPGRADE
        self.upgrade_options = [
            {"name": "Скорость", "type": "speed", "description": "+20% к скорости корабля"},
            {"name": "Урон", "type": "damage", "description": "+20% к урону пуль"},
            {"name": "Скорострельность", "type": "fire_rate", "description": "+20% к скорости стрельбы"},
            {"name": "Щит", "type": "shield", "description": "Временная неуязвимость"}
        ]

    def apply_upgrade(self, upgrade_type):
        self.player.upgrades[upgrade_type] += 0.2
        if upgrade_type == "shield":
            self.player.activate_shield()
        self.state = GameState.GAME

    def show_upgrade_menu(self):
        self.screen.fill(Config.BG_COLOR)
        title = self.font.render("Выберите улучшение:", True, Config.YELLOW)
        self.screen.blit(title, (Config.SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        for i, option in enumerate(self.upgrade_options):
            text = self.font.render(f"{i + 1} - {option['name']}: {option['description']}", True, Config.WHITE)
            self.screen.blit(text, (Config.SCREEN_WIDTH // 2 - text.get_width() // 2, 200 + i * 50))

        pygame.display.flip()

    def show_game_over(self):
        self.screen.fill(Config.BG_COLOR)
        game_over_text = self.big_font.render("ИГРА ОКОНЧЕНА", True, Config.RED)
        score_text = self.font.render(f"Ваш счет: {self.score}", True, Config.WHITE)
        high_score_text = self.font.render(f"Рекорд: {self.high_score}", True, Config.YELLOW)
        restart_text = self.font.render("Нажмите R для рестарта", True, Config.WHITE)
        menu_text = self.font.render("ESC - Меню", True, Config.WHITE)

        self.screen.blit(game_over_text, (Config.SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, 150))
        self.screen.blit(score_text, (Config.SCREEN_WIDTH // 2 - score_text.get_width() // 2, 250))
        self.screen.blit(high_score_text, (Config.SCREEN_WIDTH // 2 - high_score_text.get_width() // 2, 300))
        self.screen.blit(restart_text, (Config.SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 400))
        self.screen.blit(menu_text, (Config.SCREEN_WIDTH // 2 - menu_text.get_width() // 2, 450))

        pygame.display.flip()

    def show_victory_screen(self):
        self.screen.fill(Config.BG_COLOR)
        victory_text = self.big_font.render("ПОБЕДА!", True, Config.GREEN)
        score_text = self.font.render(f"Ваш счет: {self.score}", True, Config.WHITE)
        high_score_text = self.font.render(f"Рекорд: {self.high_score}", True, Config.YELLOW)
        restart_text = self.font.render("Нажмите R для рестарта", True, Config.WHITE)
        menu_text = self.font.render("ESC - Меню", True, Config.WHITE)

        self.screen.blit(victory_text, (Config.SCREEN_WIDTH // 2 - victory_text.get_width() // 2, 150))
        self.screen.blit(score_text, (Config.SCREEN_WIDTH // 2 - score_text.get_width() // 2, 250))
        self.screen.blit(high_score_text, (Config.SCREEN_WIDTH // 2 - high_score_text.get_width() // 2, 300))
        self.screen.blit(restart_text, (Config.SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 400))
        self.screen.blit(menu_text, (Config.SCREEN_WIDTH // 2 - menu_text.get_width() // 2, 450))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            self.clock.tick(Config.FPS)

            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if self.state == GameState.MENU:
                        if event.key == pygame.K_1:
                            self.difficulty = Difficulty.EASY
                            self.new_game()
                        elif event.key == pygame.K_2:
                            self.difficulty = Difficulty.NORMAL
                            self.new_game()
                        elif event.key == pygame.K_3:
                            self.difficulty = Difficulty.HARD
                            self.new_game()
                        elif event.key == pygame.K_ESCAPE:
                            running = False

                    elif self.state == GameState.STORY and event.key == pygame.K_SPACE:
                        if not self.story_manager.get_current_story():
                            self.state = GameState.GAME
                        else:
                            self.story_manager.advance_story()
                            if not self.story_manager.get_current_story():
                                self.state = GameState.GAME

                    elif self.state == GameState.UPGRADE:
                        if event.key == pygame.K_1:
                            self.apply_upgrade("speed")
                        elif event.key == pygame.K_2:
                            self.apply_upgrade("damage")
                        elif event.key == pygame.K_3:
                            self.apply_upgrade("fire_rate")
                        elif event.key == pygame.K_4:
                            self.apply_upgrade("shield")

                    elif event.key == pygame.K_ESCAPE:
                        if self.state in [GameState.GAME_OVER, GameState.VICTORY]:
                            self.state = GameState.MENU
                        elif self.state == GameState.GAME:
                            self.state = GameState.MENU

                    elif event.key == pygame.K_r and self.state in [GameState.GAME_OVER, GameState.VICTORY]:
                        self.new_game()

                    elif event.key == pygame.K_SPACE and self.state == GameState.GAME:
                        self.player.shoot()

                    elif event.key == pygame.K_s and self.state == GameState.GAME:
                        self.player.activate_shield()

            # State-specific updates
            if self.state == GameState.GAME:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_SPACE]:
                    self.player.shoot()

                self.all_sprites.update()
                self.player.bullets.update()
                self.particle_system.update()
                self.check_collisions()

                # Special boss attacks
                for enemy in self.enemies:
                    if isinstance(enemy, Boss) and enemy.update():  # Boss.update() returns True when attacking
                        # Boss shoots bullets
                        bullet = Bullet(enemy.rect.centerx, enemy.rect.bottom)
                        bullet.speed = -bullet.speed  # Enemy bullets go downward
                        bullet.image.fill(Config.PURPLE)
                        self.all_sprites.add(bullet)
                        self.enemies.add(bullet)

            # Rendering
            self.screen.fill(Config.BG_COLOR)

            if self.state == GameState.MENU:
                self.show_menu()
            elif self.state == GameState.STORY:
                self.show_story()
            elif self.state == GameState.GAME:
                self.all_sprites.draw(self.screen)
                self.player.bullets.draw(self.screen)
                self.particle_system.draw(self.screen)
                self.show_hud()
            elif self.state == GameState.UPGRADE:
                self.show_upgrade_menu()
            elif self.state == GameState.GAME_OVER:
                self.show_game_over()
            elif self.state == GameState.VICTORY:
                self.show_victory_screen()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()

"""Game rules + physics: spawning, gravity, slicing, scoring, lives, HUD."""
import math
import random

from .assets import SpriteSet, blit_rgba, cut_sprite
from .effects import Effects, draw_heart, put_text

GRAVITY = 1700.0      # px/s^2 at 720p (scaled with height)
MAX_LIVES = 3


class Body:
    def __init__(self, img, x, y, vx=0.0, vy=0.0, angle=0.0, spin=0.0, scale=1.0):
        self.img, self.x, self.y, self.vx, self.vy = img, x, y, vx, vy
        self.angle, self.spin, self.scale = angle, spin, scale

    def update(self, dt, g):
        self.vy += g * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt

    def draw(self, frame):
        blit_rgba(frame, self.img, self.x, self.y, self.angle, self.scale)


class Fruit(Body):
    def __init__(self, sprite, *a, button=False, **kw):
        super().__init__(sprite.img, *a, **kw)
        self.sprite = sprite
        self.bomb = sprite.bomb
        self.button = button
        self.radius = sprite.radius * self.scale


class Half(Body):
    pass


def _seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    if l2 < 1e-9:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / l2))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


class Game:
    def __init__(self, W, H, sprites=None, seed=None):
        self.W, self.H = W, H
        self.k = H / 720.0
        self.g = GRAVITY * self.k
        self.rng = random.Random(seed)
        self.sprites = sprites or SpriteSet()
        self.fx = Effects(W, H, self.rng, self.k)
        self.best = 0
        self.slices = 0
        self.events = []        # sound events for the caller to play: slice, combo, bomb, miss, over
        self.reset()

    # -- state ----------------------------------------------------------------
    def reset(self):
        self.state = "menu"
        self.fruits, self.halves = [], []
        self.score, self.lives = 0, MAX_LIVES
        self.spawn_timer, self.over_timer = 1.0, 0.0
        self._spawn_button()

    def _spawn_button(self):
        s = self.sprites.fruits.get("watermelon") or next(iter(self.sprites.fruits.values()))
        self.fruits.append(Fruit(s, self.W / 2, self.H * 0.58, scale=1.7 * self.k, spin=25, button=True))

    def start(self):
        self.state = "playing"
        self.fruits = [f for f in self.fruits if not f.button]
        self.score, self.lives, self.spawn_timer = 0, MAX_LIVES, 0.6

    def _game_over(self):
        self.state = "over"
        self.events.append("over")
        self.best = max(self.best, self.score)
        self.over_timer = 0.0
        self.fruits = []

    # -- spawning -------------------------------------------------------------
    def _launch(self, bomb):
        k, W, H = self.k, self.W, self.H
        sprite = self.sprites.bomb if bomb else self.sprites.choose(self.rng)
        x = self.rng.uniform(0.12, 0.88) * W
        rise = self.rng.uniform(0.50, 0.88) * H                 # how high it flies
        vy = -math.sqrt(2 * self.g * rise)
        flight = 2 * abs(vy) / self.g
        vx = (W / 2 - x) * self.rng.uniform(0.25, 0.9) / flight + self.rng.uniform(-50, 50) * k
        self.fruits.append(Fruit(sprite, x, H + 90 * k, vx, vy, angle=self.rng.uniform(0, 360),
                                 spin=self.rng.uniform(-240, 240),
                                 scale=k * self.rng.uniform(0.95, 1.12)))

    def _spawn_wave(self):
        n = 1 + min(3, self.score // 12) + (1 if self.rng.random() < 0.35 else 0)
        bomb_p = min(0.07 + self.score * 0.0015, 0.18)
        for _ in range(min(n, 5)):
            self._launch(self.score >= 5 and self.rng.random() < bomb_p)

    # -- main update -------------------------------------------------------------
    def update(self, dt, segments=()):
        if self.state == "playing":
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self._spawn_wave()
                self.spawn_timer = max(0.45, 1.5 - 0.012 * self.score) + self.rng.uniform(0, 0.5)
        elif self.state == "over":
            self.over_timer += dt
            if self.over_timer > 1.2 and not any(f.button for f in self.fruits):
                self._spawn_button()

        for f in self.fruits:
            if f.button:
                f.angle += f.spin * dt
            else:
                f.update(dt, self.g)
        for h in self.halves:
            h.update(dt, self.g)
        self.halves = [h for h in self.halves if h.y < self.H + 200 * self.k]

        # slicing
        cut = []
        for seg in segments:
            for f in list(self.fruits):
                if f in self.fruits and _seg_dist(f.x, f.y, *seg[0], *seg[1]) <= f.radius:
                    if self._slice(f, seg):
                        cut.append(f)
        if cut:
            n = len(cut)
            self.score += n
            if n >= 2:
                self.events.append("combo")
                self.score += n
                cx = sum(f.x for f in cut) / n
                cy = sum(f.y for f in cut) / n
                self.fx.popup(f"COMBO x{n}!", cx, cy - 70 * self.k, (80, 230, 255), 1.3)

        # misses
        if self.state == "playing":
            for f in list(self.fruits):
                if f.y - f.radius > self.H + 40 * self.k and f.vy > 0 and not f.button:
                    self.fruits.remove(f)
                    if not f.bomb:
                        self.lives -= 1
                        self.events.append("miss")
                        self.fx.popup("MISS", min(max(f.x, 60), self.W - 60), self.H - 70 * self.k, (60, 60, 255), 1.0)
            if self.lives <= 0:
                self._game_over()
        else:
            self.fruits = [f for f in self.fruits if f.button or f.y < self.H + 300]

        self.fx.update(dt)

    def _slice(self, f, seg):
        """Cut fruit f with blade segment seg. Returns True if it was a scoring fruit."""
        k = self.k
        (x0, y0), (x1, y1) = seg
        world = math.degrees(math.atan2(y1 - y0, x1 - x0))
        self.fruits.remove(f)
        if f.bomb:
            self.events.append("bomb")
            self.fx.flash((255, 255, 255), 1.0)
            self.fx.juice(f.x, f.y, (40, 160, 255), world, n=70)
            self.fx.popup("BOOM!", f.x, f.y, (70, 70, 255), 1.8)
            if self.state == "playing":
                self._game_over()
            return False

        local = world - f.angle                      # cut angle in the fruit's own (rotated) frame
        if f.sprite.cut_img is not None:             # halves show the fruit's inside
            half_a, half_b = cut_sprite(f.sprite.cut_img, local)
        else:                                        # no inside image: paint a flesh-coloured edge
            half_a, half_b = cut_sprite(f.sprite.img, local, f.sprite.flesh, f.sprite.band)
        nx, ny = -math.sin(math.radians(world)), math.cos(math.radians(world))
        for img, sign in ((half_a, 1), (half_b, -1)):
            # each half is pushed away from the cut line, keeps the fruit's momentum, spins, then falls
            push = self.rng.uniform(140, 260) * k
            self.halves.append(Half(
                img, f.x + nx * sign * 3 * k, f.y + ny * sign * 3 * k,
                f.vx * 0.8 + nx * sign * push, f.vy * 0.8 + ny * sign * push - 40 * k,
                angle=f.angle, spin=f.spin + sign * self.rng.uniform(35, 110), scale=f.scale))
        self.events.append("slice")
        self.fx.slash(f.x, f.y, world, f.radius * 1.4)
        self.fx.juice(f.x, f.y, f.sprite.juice, world)
        self.fx.splat(f.x, f.y, f.sprite.juice)
        self.slices += 1
        if f.button:
            if self.state == "menu":
                self.start()
            elif self.state == "over":
                self.start()
            return False
        return True

    # -- drawing --------------------------------------------------------------------
    def draw(self, frame):
        k = self.k
        self.fx.draw_under(frame)
        for h in self.halves:
            h.draw(frame)
        for f in self.fruits:
            f.draw(frame)
        self.fx.draw_over(frame)

        if self.state == "playing":
            put_text(frame, str(self.score), 40 * k, 52 * k, 1.8 * k, (255, 255, 255), 3, center=False)
            put_text(frame, f"best {self.best}", 42 * k, 100 * k, 0.8 * k, (200, 200, 200), 1, center=False)
            for i in range(MAX_LIVES):
                full = i < self.lives
                draw_heart(frame, int(self.W - (50 + i * 55) * k), int(52 * k), 22 * k,
                           (60, 60, 240) if full else (120, 120, 120), filled=full)
        elif self.state == "menu":
            put_text(frame, "FRUIT SLASH", self.W / 2, self.H * 0.16, 2.6 * k, (90, 220, 255), 5)
            put_text(frame, "slice the watermelon with your finger to start", self.W / 2, self.H * 0.84, 0.95 * k, (255, 255, 255), 2)
        else:
            put_text(frame, "GAME OVER", self.W / 2, self.H * 0.17, 2.4 * k, (70, 70, 255), 5)
            put_text(frame, f"score {self.score}    best {self.best}", self.W / 2, self.H * 0.28, 1.2 * k, (255, 255, 255), 2)
            if any(f.button for f in self.fruits):
                put_text(frame, "slice the watermelon to play again", self.W / 2, self.H * 0.84, 0.95 * k, (255, 255, 255), 2)

"""Angry Birds gameplay: a small pymunk world rendered on the desktop.

Coordinates are local to the primary work area, in screen pixels, with y growing
downwards.  Level layouts are authored in a 1600x1000 design space and scaled to
the actual screen so the same towers work on every resolution.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import pymunk

GRAVITY = 1400.0
MAX_DRAG = 130.0
MIN_DRAG = 16.0
MAX_LAUNCH = 1650.0
BIRD_MASS = 7.0
BIRD_RADIUS = 34.0

WOOD = 'wood'
STONE = 'stone'
TNT = 'tnt'

# collision types
C_GROUND = 1
C_BIRD = 2
C_BLOCK = 3
C_PIG = 4
C_TNT = 5


@dataclass
class GameObject:
    uid: int
    kind: str  # wood / stone / pig / tnt
    body: pymunk.Body
    shape: pymunk.Shape
    w: float
    h: float
    hp: float
    max_hp: float
    radius: float = 0.0
    variant: int = 0
    dead: bool = False
    fuse: float = 0.0
    effect: str | None = None
    effect_t: float = 0.0
    last_pose: tuple = field(default_factory=tuple)

    @property
    def position(self):
        return self.body.position

    @property
    def angle(self):
        return self.body.angle


@dataclass
class Level:
    name: str
    birds: int
    blocks: list
    pigs: list
    tnt: list
    two_star: int
    three_star: int


def _b(kind, x, y, w, h, angle=0.0):
    return (kind, x, y, w, h, angle)


def _p(x, y, radius=30.0):
    return (x, y, radius)


LEVELS = [
    Level(
        '小木屋', 4,
        [
            _b(WOOD, -70, 60, 24, 120),
            _b(WOOD, 70, 60, 24, 120),
            _b(WOOD, 0, 132, 180, 24),
        ],
        [_p(0, 30, 28), _p(0, 172, 28)],
        [],
        12000, 20000,
    ),
    Level(
        '双塔', 4,
        [
            _b(WOOD, -90, 80, 32, 160),
            _b(WOOD, 90, 80, 32, 160),
            _b(STONE, 0, 172, 240, 24),
        ],
        [_p(-40, 30, 30), _p(40, 30, 30), _p(0, 214, 30)],
        [],
        18000, 28000,
    ),
    Level(
        '石头城堡', 5,
        [
            _b(STONE, -120, 70, 40, 140),
            _b(STONE, 0, 70, 40, 140),
            _b(STONE, 120, 70, 40, 140),
            _b(STONE, 0, 153, 360, 26),
            _b(WOOD, -70, 221, 30, 110),
            _b(WOOD, 70, 221, 30, 110),
            _b(STONE, 0, 288, 220, 24),
        ],
        [_p(-60, 30, 30), _p(60, 30, 30), _p(0, 196, 30), _p(0, 330, 30)],
        [(150, 30, 46)],
        26000, 40000,
    ),
    Level(
        '双子屋', 5,
        [
            _b(WOOD, -350, 60, 24, 120),
            _b(WOOD, -210, 60, 24, 120),
            _b(WOOD, -280, 132, 180, 24),
            _b(WOOD, 210, 60, 24, 120),
            _b(WOOD, 350, 60, 24, 120),
            _b(WOOD, 280, 132, 180, 24),
        ],
        [_p(-280, 30, 28), _p(-280, 172, 28), _p(280, 30, 28), _p(280, 172, 28)],
        [(0, 30, 46)],
        30000, 50000,
    ),
    Level(
        '高塔', 5,
        [
            _b(WOOD, -70, 60, 24, 120),
            _b(WOOD, 70, 60, 24, 120),
            _b(WOOD, 0, 132, 180, 24),
            _b(WOOD, -50, 190, 24, 90),
            _b(WOOD, 50, 190, 24, 90),
            _b(WOOD, 0, 247, 140, 24),
        ],
        [_p(0, 30, 28), _p(0, 176, 28), _p(0, 289, 28)],
        [],
        22000, 34000,
    ),
    Level(
        '石桥', 5,
        [
            _b(STONE, -180, 70, 40, 140),
            _b(STONE, 0, 70, 40, 140),
            _b(STONE, 180, 70, 40, 140),
            _b(STONE, 0, 153, 440, 26),
        ],
        [_p(-90, 30, 30), _p(90, 30, 30), _p(-120, 196, 30), _p(120, 196, 30)],
        [],
        28000, 44000,
    ),
    Level(
        '火药库', 5,
        [
            _b(STONE, -100, 80, 36, 160),
            _b(STONE, 100, 80, 36, 160),
            _b(STONE, 0, 172, 260, 26),
            _b(WOOD, -60, 230, 28, 90),
            _b(WOOD, 60, 230, 28, 90),
            _b(WOOD, 0, 286, 170, 24),
        ],
        [_p(-110, 30, 30), _p(110, 30, 30), _p(-70, 211, 30), _p(70, 211, 30)],
        [(0, 30, 46)],
        32000, 52000,
    ),
    Level(
        '哨站', 5,
        [
            _b(WOOD, -220, 60, 24, 120),
            _b(WOOD, -80, 60, 24, 120),
            _b(WOOD, -150, 132, 180, 24),
            _b(STONE, 180, 70, 40, 140),
            _b(STONE, 320, 70, 40, 140),
            _b(STONE, 250, 153, 180, 26),
        ],
        [_p(-150, 30, 28), _p(-150, 172, 28), _p(250, 30, 30), _p(250, 196, 30)],
        [],
        28000, 46000,
    ),
]


class AngryBirdsGame:
    """Authoritative game state, physics and level flow."""

    def __init__(self, width, height):
        self.width = float(width)
        self.height = float(height)
        self.scale = max(0.72, min(self.width / 1600.0, self.height / 1000.0))
        self.ground_y = self.height * 0.835
        self.sling_x = self.width * 0.205
        self.sling_base = (self.sling_x, self.ground_y)
        self.fork_y = self.ground_y - 315.0 * self.scale
        self.anchor = (self.sling_x, self.ground_y - 255.0 * self.scale)
        self.max_drag = MAX_DRAG * self.scale
        self.min_drag = MIN_DRAG * self.scale
        self.max_launch = MAX_LAUNCH * self.scale
        self.bird_radius = BIRD_RADIUS * self.scale
        self.space = pymunk.Space()
        self.space.gravity = (0.0, GRAVITY * self.scale)
        self.space.iterations = 30
        self.space.sleep_time_threshold = 0.45
        self.space.idle_speed_threshold = 0.2
        self.space.collision_slop = 0.5
        self.space.on_collision(None, None, post_solve=self._on_collision)
        self._next_uid = 1
        self.objects: list[GameObject] = []
        self.shapes: dict[int, GameObject] = {}
        self.level_index = 0
        self.level = LEVELS[0]
        self.score = 0
        self.shots = 0
        self.state = 'ready'  # ready | flying | between | won | lost
        self.state_since = time.monotonic()
        self.current_bird = 0
        self.bird_body = None
        self.bird_shape = None
        self.bird_pose = None
        self.bird_rest = 0.0
        self.bird_launched_at = 0.0
        self.drag_origin = None
        self.drag_point = None
        self.dragging = False
        self.clear_serial = 0
        self.last_impact = 0.0
        self.settling = False
        self._build_ground()
        self.load_level(0)

    # -- construction ------------------------------------------------------
    def _build_ground(self):
        body = self.space.static_body
        segment = pymunk.Segment(body, (-400, self.ground_y), (self.width + 400, self.ground_y), 1.0)
        segment.friction = 0.92
        segment.elasticity = 0.05
        segment.collision_type = C_GROUND
        self.space.add(segment)

    def _clear_level(self):
        for obj in self.objects:
            if obj.shape in self.space.shapes:
                self.space.remove(obj.shape, obj.body)
        self.objects.clear()
        self.shapes.clear()
        self._retire_bird(remove_body=True)

    def load_level(self, index):
        self.level_index = max(0, min(len(LEVELS) - 1, int(index)))
        self.level = LEVELS[self.level_index]
        self._clear_level()
        self.score = 0
        self.shots = 0
        self.state = 'ready'
        self.state_since = time.monotonic()
        self.current_bird = 0
        self.dragging = False
        self.drag_point = None
        base_x = self.width * 0.70
        s = self.scale
        for kind, dx, dy, w, h, angle in self.level.blocks:
            self._add_block(kind, base_x + dx * s, self.ground_y - dy * s, w * s, h * s, angle)
        for dx, dy, radius in self.level.pigs:
            self._add_pig(base_x + dx * s, self.ground_y - dy * s, radius * s)
        for dx, dy, size in self.level.tnt:
            self._add_tnt(base_x + dx * s, self.ground_y - dy * s, size * s)
        # Let the tower settle before the first shot. Damage is muted here: a pig that
        # starts a few pixels above its platform must not die from the settling drop.
        self.settling = True
        for _ in range(120):
            self.space.step(1 / 120.0)
        self.score = 0
        for obj in self.objects:
            if not obj.dead:
                obj.hp = obj.max_hp
        self.settling = False

    def _new_object(self, kind, body, shape, w, h, hp, radius=0.0):
        obj = GameObject(self._next_uid, kind, body, shape, w, h, hp, hp, radius)
        self._next_uid += 1
        self.objects.append(obj)
        self.shapes[id(shape)] = obj
        self.space.add(body, shape)
        return obj

    def _add_block(self, kind, x, y, w, h, angle=0.0):
        mass = max(1.0, (w * h) / 1050.0) * (1.0 if kind == WOOD else 2.3)
        moment = pymunk.moment_for_box(mass, (w, h))
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        body.angle = math.radians(angle)
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.friction = 0.86
        shape.elasticity = 0.08
        shape.collision_type = C_BLOCK
        hp = (w * h) * (0.10 if kind == WOOD else 0.16)
        self._new_object(kind, body, shape, w, h, max(60.0, hp))

    def _add_pig(self, x, y, radius):
        mass = 4.2 * max(0.7, radius / 30.0)
        # A circle on a beam has no rolling resistance and slowly rolls off even at
        # rest.  A slightly narrower box keeps the round pig visually planted.
        moment = pymunk.moment_for_box(mass, (radius * 1.6, radius * 2.0))
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        shape = pymunk.Poly.create_box(body, (radius * 1.6, radius * 2.0))
        shape.friction = 0.7
        shape.elasticity = 0.25
        shape.collision_type = C_PIG
        variant = sum(1 for item in self.objects if item.kind == 'pig')
        obj = self._new_object('pig', body, shape, radius * 2, radius * 2, 100.0, radius)
        obj.variant = variant

    def _add_tnt(self, x, y, size):
        body = pymunk.Body(2.5, pymunk.moment_for_box(2.5, (size, size)))
        body.position = (x, y)
        shape = pymunk.Poly.create_box(body, (size, size))
        shape.friction = 0.8
        shape.elasticity = 0.15
        shape.collision_type = C_TNT
        self._new_object(TNT, body, shape, size, size, 1.0)

    # -- input -------------------------------------------------------------
    @property
    def birds_left(self):
        return max(0, self.level.birds - self.shots)

    def near_bird(self, x, y):
        if self.state != 'ready':
            return False
        ax, ay = self.anchor
        return math.hypot(x - ax, y - ay) <= 105 * self.scale

    def begin_drag(self, x, y):
        if self.near_bird(x, y):
            self.dragging = True
            self.drag_point = self.anchor
            return True
        return False

    def drag_to(self, x, y):
        if not self.dragging:
            return
        ax, ay = self.anchor
        dx, dy = x - ax, y - ay
        distance = math.hypot(dx, dy)
        if distance > self.max_drag:
            dx *= self.max_drag / distance
            dy *= self.max_drag / distance
        self.drag_point = (ax + dx, ay + dy)

    def release(self):
        if not self.dragging:
            return
        self.dragging = False
        ax, ay = self.anchor
        px, py = self.drag_point or self.anchor
        dx, dy = ax - px, ay - py
        pull = math.hypot(dx, dy)
        if pull < self.min_drag:
            self.drag_point = None
            return
        power = min(1.0, pull / self.max_drag)
        speed = self.max_launch * power
        direction = (dx / pull, dy / pull)
        self._launch(px, py, direction[0] * speed, direction[1] * speed)
        self.drag_point = None

    def aim_velocity(self):
        """The velocity the bird would get if released now."""
        ax, ay = self.anchor
        px, py = self.drag_point or self.anchor
        dx, dy = ax - px, ay - py
        pull = math.hypot(dx, dy)
        if pull < 1:
            return 0.0, 0.0
        speed = self.max_launch * min(1.0, pull / self.max_drag)
        return dx / pull * speed, dy / pull * speed

    def _launch(self, x, y, vx, vy):
        body = pymunk.Body(BIRD_MASS, pymunk.moment_for_circle(BIRD_MASS, 0, self.bird_radius))
        body.position = (x, y)
        shape = pymunk.Circle(body, self.bird_radius)
        shape.friction = 0.75
        shape.elasticity = 0.35
        shape.collision_type = C_BIRD
        self.space.add(body, shape)
        body.velocity = (vx, vy)
        self.bird_body = body
        self.bird_shape = shape
        self.bird_pose = (x, y, 0.0)
        self.bird_rest = 0.0
        self.bird_launched_at = time.monotonic()
        self.shots += 1
        self.state = 'flying'
        self.state_since = time.monotonic()

    def _retire_bird(self, remove_body=False):
        if self.bird_body is not None and self.bird_body in self.space.bodies:
            self.space.remove(self.bird_shape, self.bird_body)
        self.bird_body = None
        self.bird_shape = None
        self.bird_rest = 0.0

    # -- simulation --------------------------------------------------------
    def _on_collision(self, arbiter, space, data):
        if self.settling or not arbiter.is_first_contact:
            return
        impulse = float(arbiter.total_impulse.length)
        # A tower resting on the ground produces a large support impulse every step.
        # Damage needs a first contact with real incoming speed as well.
        if impulse < 1200:
            return
        impact_speed = max((body.velocity.length for body in arbiter.bodies
                            if body.body_type == pymunk.Body.DYNAMIC), default=0.0)
        if impact_speed < 90:
            return
        self.last_impact = impulse
        for shape in arbiter.shapes:
            obj = self.shapes.get(id(shape))
            if obj is None or obj.dead:
                continue
            if obj.kind == 'pig':
                obj.hp -= impulse * 0.075
                if obj.hp <= 0:
                    self._pop_pig(obj)
            elif obj.kind == TNT:
                if impulse > 1200:
                    obj.fuse = 0.001
            else:
                factor = 0.35 if obj.kind == WOOD else 0.28
                obj.hp -= impulse * factor
                if obj.hp <= 0:
                    self._break_block(obj)

    def _pop_pig(self, obj):
        if obj.dead:
            return
        obj.dead = True
        obj.effect = 'pop'
        obj.effect_t = 0.0
        obj.last_pose = (obj.body.position.x, obj.body.position.y, obj.body.angle)
        self.space.remove(obj.shape, obj.body)
        self.score += 5000

    def _break_block(self, obj):
        if obj.dead:
            return
        obj.dead = True
        obj.effect = 'break'
        obj.effect_t = 0.0
        obj.last_pose = (obj.body.position.x, obj.body.position.y, obj.body.angle)
        self.space.remove(obj.shape, obj.body)
        self.score += 500 if obj.kind == WOOD else 800

    def _explode(self, obj):
        if obj.dead:
            return
        x, y = obj.body.position
        obj.dead = True
        obj.effect = 'boom'
        obj.effect_t = 0.0
        obj.last_pose = (x, y, obj.body.angle)
        self.space.remove(obj.shape, obj.body)
        self.score += 1000
        radius = 250 * self.scale
        for body in list(self.space.bodies):
            if body.body_type != pymunk.Body.DYNAMIC:
                continue
            dx, dy = body.position.x - x, body.position.y - y
            distance = math.hypot(dx, dy)
            if distance > radius or distance < 1:
                continue
            strength = 5200 * (1 - distance / radius) * self.scale
            body.apply_impulse_at_world_point((dx / distance * strength, dy / distance * strength), body.position)
        for other in self.objects:
            if other is obj or other.dead:
                continue
            dx, dy = other.body.position.x - x, other.body.position.y - y
            distance = math.hypot(dx, dy)
            if distance > radius:
                continue
            if other.kind == TNT and distance < radius * 0.7:
                other.fuse = 0.08
            elif other.kind == 'pig' and distance < radius * 0.75:
                self._pop_pig(other)
            elif other.kind != 'pig':
                other.hp -= (1 - distance / radius) * 1200
                if other.hp <= 0:
                    self._break_block(other)
        self.last_impact = 9999

    def step(self, dt):
        dt = max(0.001, min(dt, 0.033))
        if self.state in ('ready', 'flying', 'between'):
            self.space.step(dt)
        for obj in self.objects:
            if obj.dead and obj.effect:
                obj.effect_t += dt
            if obj.fuse:
                obj.fuse += dt
                if obj.fuse >= 0.001:
                    self._explode(obj)
        if self.state == 'flying' and self.bird_body is not None:
            body = self.bird_body
            speed = body.velocity.length
            pos = body.position
            if speed < 26 * self.scale:
                self.bird_rest += dt
            else:
                self.bird_rest = 0.0
            out = pos.x < -300 or pos.x > self.width + 300 or pos.y > self.height + 300
            if out or self.bird_rest > 0.75 or time.monotonic() - self.bird_launched_at > 9.0:
                self.bird_pose = (pos.x, pos.y, body.angle)
                self._retire_bird()
                self.state = 'between'
                self.state_since = time.monotonic()
        elif self.state == 'between':
            if time.monotonic() - self.state_since > 0.65:
                if self.birds_left <= 0:
                    self.state = 'lost' if self._pigs_alive() else 'won'
                    self.state_since = time.monotonic()
                    if self.state == 'won':
                        self._win()
                else:
                    self.state = 'ready'
                    self.state_since = time.monotonic()
                    self.current_bird = self.shots
        if self.state not in ('won', 'lost') and not self._pigs_alive():
            self.state = 'won'
            self.state_since = time.monotonic()
            self._win()

    def _pigs_alive(self):
        return any(obj.kind == 'pig' and not obj.dead for obj in self.objects)

    def _win(self):
        self.score += self.birds_left * 10000
        self.clear_serial += 1
        self._retire_bird()

    def pigs_left(self):
        return sum(1 for obj in self.objects if obj.kind == 'pig' and not obj.dead)

    def blocks_left(self):
        return sum(1 for obj in self.objects if obj.kind in (WOOD, STONE) and not obj.dead)

    def score_stars(self):
        if self.state != 'won':
            return 0
        if self.score >= self.level.three_star:
            return 3
        if self.score >= self.level.two_star:
            return 2
        return 1

    # -- display helpers ---------------------------------------------------
    def bird_screen_pose(self):
        """Centre, angle and alpha for the current bird sprite."""
        if self.state == 'ready':
            if self.dragging and self.drag_point:
                return (self.drag_point[0], self.drag_point[1], 0.0)
            return (self.anchor[0], self.anchor[1], 0.0)
        if self.state == 'flying' and self.bird_body is not None:
            p = self.bird_body.position
            return (p.x, p.y, self.bird_body.angle)
        return None

    def camera_pose(self):
        """Frozen pose of the last bird after it came to rest."""
        return self.bird_pose

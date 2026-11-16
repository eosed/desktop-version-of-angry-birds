"""Level layouts modelled on the original Angry Birds.

The originals reuse a handful of primitives and stack them higher as the
levels progress: a tall ground-floor hut with a pig inside, shallow storeys
above it, stone slabs, glass (ice) columns, wide roofs over several supports,
and a pig perched on the summit.  Later levels put two or three of these
side by side and reach ten-plus storeys.

Everything is authored in the same 1600x1000 design space the game scales to
the screen: x is relative to the castle anchor, y is height above the ground.
"""
from __future__ import annotations

from dataclasses import dataclass

WOOD = 'wood'
STONE = 'stone'
ICE = 'ice'

RED = 'red'
BOMB = 'bomb'
SPLIT = 'split'
BIRD_NAMES = {RED: '红鸟', BOMB: '炸弹鸟', SPLIT: '分裂鸟'}

TALL_LEG = 108.0   # ground-floor hut legs, tall enough to hold a pig
TALL_BEAM = 16.0   # its roof beam
LEG = 36.0         # shallow structural storey
BEAM = 10.0
LEG_W = 44.0       # thick legs: thin ones let tall towers creep sideways


@dataclass
class Level:
    name: str
    birds: int
    blocks: list
    pigs: list
    tnt: list
    two_star: int
    three_star: int
    bird_types: tuple = ()

    @property
    def types(self):
        """A deterministic red/bomb/split cycle, with authored specials first."""
        authored = tuple(self.bird_types)
        cycle = (RED, BOMB, SPLIT) * self.birds
        return (authored + cycle)[:self.birds]


def _b(kind, x, y, w, h, angle=0.0):
    return (kind, x, y, w, h, angle)


def _p(x, y, radius=28.0):
    return (x, y, radius)


# -- primitives: each returns (blocks, pigs) --------------------------------
def storey(cx, base, width=210.0, kind=WOOD, pig=0.0, leg_h=None, beam=BEAM,
           leg_w=LEG_W):
    """One hut: two legs, one beam, an optional pig standing inside.

    A storey holding a pig grows just tall enough for it, so that a ten-plus
    storey tower still fits between the ground and the top of the screen.
    """
    if leg_h is None:
        leg_h = max(LEG, 2 * pig + 10.0) if pig else LEG
    half = width / 2 - leg_w / 2
    blocks = [
        _b(kind, cx - half, base + leg_h / 2, leg_w, leg_h),
        _b(kind, cx + half, base + leg_h / 2, leg_w, leg_h),
        _b(kind, cx, base + leg_h + beam / 2, width, beam),
    ]
    pigs = [_p(cx, base + pig + 2.0, pig)] if pig else []
    return blocks, pigs


def tower(cx, floors, base=0.0, width=220.0, kinds=WOOD, pigs=None, taper=6.0,
          leg_w=LEG_W, ceiling=770.0):
    """A stack of huts: a tall ground floor, then storeys sized to their pigs.

    Stops at the design ceiling so a fifteen-storey castle still fits between
    the ground and the top of the screen; pigs on skipped floors perch on top.
    """
    pigs = pigs or {}
    blocks, placed = [], []
    y, w = base, width
    for floor in range(floors):
        kind = kinds[floor % len(kinds)] if isinstance(kinds, (list, tuple)) else kinds
        radius = pigs.get(floor, 0.0)
        if floor == 0:
            leg_h, beam = TALL_LEG, TALL_BEAM
        else:
            leg_h = max(LEG, 2 * radius + 10.0) if radius else LEG
            beam = BEAM
        if y + leg_h + beam > ceiling:
            if radius:
                placed.append(_p(cx, y + radius + 2.0, radius))
            break
        part, here = storey(cx, y, w, kind, radius, leg_h, beam, leg_w)
        blocks += part
        placed += here
        y = part[-1][2] + part[-1][4] / 2        # top of this storey's beam
        w = max(130.0, w - taper)
    return blocks, placed


def arch(cx, base=0.0, width=260.0, height=110.0, kind=STONE, thickness=30.0,
         pig=0.0, cap_h=18.0):
    """Two thick piers under one lintel; a pig can stand underneath."""
    blocks = [
        _b(kind, cx - width / 2 + thickness / 2, base + height / 2, thickness, height),
        _b(kind, cx + width / 2 - thickness / 2, base + height / 2, thickness, height),
        _b(kind, cx, base + height + cap_h / 2, width, cap_h),
    ]
    pigs = [_p(cx, base + pig + 2.0, pig)] if pig else []
    return blocks, pigs


def pillar(cx, base, w=32.0, h=150.0, kind=STONE):
    return [_b(kind, cx, base + h / 2, w, h)], []


def slab(cx, base, w, h, kind=STONE):
    return [_b(kind, cx, base + h / 2, w, h)], []


def wall(cx, base, w=190.0, h=110.0, kind=WOOD):
    return [_b(kind, cx, base + h / 2, w, h)], []


def merge(*parts):
    blocks, pigs = [], []
    for b, p in parts:
        blocks += b
        pigs += p
    return blocks, pigs


# -- level specs -----------------------------------------------------------
def _specs():
    W, S, I = WOOD, STONE, ICE
    mix1 = (W, I, S)
    mix2 = (I, W, S)
    mix3 = (S, W, I)
    mix4 = (S, I, W)

    def t(cx, floors, kinds, pigs=None, width=220.0, base=0.0):
        return lambda: tower(cx, floors, base, width, kinds, pigs or {})

    def a(cx, width=220.0, height=110.0, kind=STONE, pig=0.0):
        return lambda: arch(cx, 0, width, height, kind, 30.0, pig)

    def wl(cx, width=190.0, height=110.0, kind=WOOD):
        return lambda: wall(cx, 0, width, height, kind)

    def pair(lx, lf, lk, lp, rx, rf, rk, rp, width=210.0):
        return lambda: merge(tower(lx, lf, 0, width, lk, lp),
                             tower(rx, rf, 0, width, rk, rp))

    return [
        # -- opening levels: one or two low huts
        ('小木屋', 3, [t(0, 2, (W, W), {0: 28})], [], [], 12000, 19000),
        ('三间屋', 4, [t(-150, 2, (W, W), {0: 26}, 170),
                       t(0, 3, (W, W, S), {0: 26}, 170),
                       t(150, 2, (W, W), {0: 26}, 170)], [], [], 18000, 26000),
        ('门廊', 4, [t(-120, 2, (W, W), {0: 28}),
                     t(120, 2, (W, W), {}),
                     lambda: slab(0, TALL_LEG + TALL_BEAM, 540, 24, W),
                     lambda: slab(0, TALL_LEG + TALL_BEAM + 24, 460, 20, W)],
         [], [], 20000, 30000),

        # -- stone appears
        ('双塔', 4, [pair(-170, 3, (W, W, S), {0: 26}, 170, 3, (W, S, W), {0: 26})],
         [], [], 24000, 34000),
        ('高脚屋', 5, [lambda: merge(pillar(-150, 0, 30, 170, W), pillar(150, 0, 30, 170, W),
                                    slab(0, 170, 360, 22, W),
                                    storey(0, 192, 210, W, pig=26))],
         [], [], 26000, 36000),
        ('石顶', 5, [t(-130, 2, (W, W), {0: 28}), t(130, 2, (W, W), {0: 28}),
                     lambda: slab(0, TALL_LEG + TALL_BEAM, 480, 34, S)],
         [], [], 28000, 38000),

        # -- glass/ice arrives
        ('冰屋', 5, [t(0, 4, (I, I, W, S), {0: 28, 2: 20})], [], [(-190, 30, 42)], 30000, 42000),
        ('拱桥', 5, [a(-300, 200, 96, S, 26), a(0, 200, 96, S, 26), a(300, 200, 96, S, 26),
                     lambda: slab(0, 114, 740, 24, W)], [], [], 32000, 44000),

        # -- first multi-structure levels
        ('阶梯', 5, [t(-300, 2, (W, W), {0: 26}, 170),
                     t(0, 4, (W, I, W, S), {0: 26, 2: 20}, 190),
                     t(300, 6, (W, I, S), {0: 26, 2: 20}, 200)], [], [], 36000, 50000),
        ('双塔楼', 5, [pair(-200, 5, mix1, {0: 28, 3: 20}, 200, 5, mix2, {0: 26, 3: 20}, 200)],
         [], [(-400, 30, 46)], 40000, 56000),
        ('通天塔', 6, [t(0, 9, mix1, {0: 28, 3: 24, 6: 20}, 230)],
         [], [(-260, 30, 46), (260, 30, 46)], 46000, 64000),
        ('石堡', 6, [t(-230, 4, (S, W, W, S), {0: 28, 2: 22}),
                     t(230, 4, (S, W, W, S), {0: 28, 2: 22}),
                     lambda: merge(slab(0, 0, 240, 120, S), slab(0, 120, 700, 22, W))],
         [], [], 50000, 70000),
        ('猪王堡', 7, [t(-300, 6, mix1, {0: 28, 3: 22}, 200),
                       t(0, 8, mix2, {0: 28, 3: 24, 6: 20}, 210),
                       t(300, 6, mix1, {0: 28, 3: 22}, 200)],
         [], [(-520, 30, 44), (520, 30, 44)], 56000, 78000),
        ('三层堡', 6, [pair(-200, 7, (W, W, I, S), {0: 28, 3: 24, 5: 20},
                            200, 7, (I, W, W, S), {0: 26, 3: 22, 5: 20}, 200)],
         [], [(-400, 30, 44), (400, 30, 44)], 58000, 82000),

        # -- ten storeys and more
        ('双高塔', 7, [pair(-230, 10, mix1, {0: 28, 4: 24, 7: 20},
                            230, 10, mix2, {0: 26, 5: 24, 8: 20}, 215)],
         [], [(-470, 30, 46), (470, 30, 46)], 68000, 94000),
        ('长城', 7, [wl(-360, 170, 150, S), wl(-120, 170, 150, W),
                     wl(120, 170, 150, S), wl(360, 170, 150, W),
                     t(0, 4, (W, I, S), {0: 28, 2: 20}, 240)],
         [(-360, 170, 26), (360, 170, 26)], [], 72000, 98000),
        ('巨塔', 7, [t(0, 12, mix1, {0: 28, 3: 24, 6: 22, 9: 20}, 240),
                     lambda: merge(pillar(-310, 0, 40, 150, S), pillar(310, 0, 40, 150, S),
                                   slab(0, 150, 720, 22, W))],
         [], [(-380, 30, 46), (380, 30, 46)], 76000, 104000),
        ('云梯', 7, [t(-190, 13, mix1, {0: 28, 5: 24, 9: 20}, 210),
                     t(210, 9, mix2, {0: 28, 4: 24, 7: 20}, 210)],
         [], [(-520, 30, 44)], 80000, 110000),
        ('石林', 7, [t(-330, 8, mix3, {0: 28, 3: 22, 6: 20}, 200),
                     t(0, 11, mix1, {0: 28, 5: 26, 8: 22}, 210),
                     t(330, 8, mix4, {0: 28, 4: 22, 7: 20}, 200)],
         [], [(-540, 30, 46), (540, 30, 46)], 86000, 118000),
        ('空中楼阁', 8, [lambda: merge(pillar(-310, 0, 36, 200, S), pillar(310, 0, 36, 200, S),
                                    slab(0, 200, 720, 26, S)),
                     t(0, 5, mix1, {0: 26, 2: 20}, 250, base=226),
                     t(-310, 3, mix3, {0: 20}, 130, base=226),
                     t(310, 3, mix4, {0: 20}, 130, base=226)],
         [(-310, 30, 26), (310, 30, 26)], [], 90000, 124000),
        ('大本营', 8, [a(-370, 200, 130, S, 26), a(370, 200, 130, S, 26),
                       t(0, 10, mix1, {0: 28, 4: 24, 7: 20}, 230)],
         [(-370, 200, 26), (370, 200, 26)], [], 96000, 132000),
        ('猪王之塔', 8, [t(0, 14, mix1, {0: 28, 3: 24, 6: 24, 9: 22, 12: 20}, 240)],
         [(-400, 30, 46), (400, 30, 46)], [], 102000, 140000),
        ('双子堡', 8, [pair(-240, 12, mix1, {0: 28, 4: 24, 8: 20},
                            240, 12, mix2, {0: 26, 5: 24, 9: 20}, 215)],
         [], [(-470, 30, 46), (470, 30, 46)], 108000, 148000),
        ('水晶宫', 8, [t(0, 13, mix1, {0: 28, 3: 24, 6: 24, 9: 22, 12: 20}, 230),
                       wl(-380, 120, 130, I), wl(380, 120, 130, I)],
         [(-380, 30, 44), (380, 30, 44)], [], 114000, 156000),
        ('要塞', 8, [wl(-400, 110, 200, S), wl(400, 110, 200, S),
                     lambda: slab(0, 200, 900, 26, S),
                     t(0, 8, mix1, {0: 28, 3: 24, 5: 20}, 240, base=226)],
         [(-400, 222, 26), (400, 222, 26)], [], 120000, 164000),
        ('三连塔', 9, [t(-340, 8, mix1, {0: 28, 3: 22}, 200),
                       t(0, 12, mix2, {0: 28, 5: 26, 9: 20}, 210),
                       t(340, 8, mix1, {0: 28, 4: 22}, 200)],
         [(-610, 30, 46), (610, 30, 46)], [], 126000, 172000),
        ('天梯', 9, [t(0, 14, mix1, {0: 28, 3: 24, 6: 24, 9: 22, 12: 20}, 250)],
         [(-400, 30, 46), (400, 30, 46)], [], 132000, 180000),
        ('终局', 9, [pair(-260, 11, mix1, {0: 28, 4: 24, 8: 20},
                          260, 11, mix2, {0: 26, 5: 24, 9: 20}, 210)],
         [(-520, 30, 46), (520, 30, 46)], [], 138000, 188000),
        ('猪王城', 9, [t(-360, 9, mix3, {0: 28, 3: 22, 6: 20}, 200),
                       t(0, 13, mix1, {0: 28, 5: 26, 8: 24, 11: 20}, 230),
                       t(360, 9, mix4, {0: 28, 4: 22, 7: 20}, 200)],
         [(-560, 30, 46), (560, 30, 46)], [], 146000, 198000),
        ('天际', 9, [pair(-210, 14, mix2, {0: 28, 4: 24, 8: 22, 12: 20},
                          210, 14, mix1, {0: 26, 5: 24, 9: 22, 13: 20}, 215)],
         [(-520, 30, 46), (520, 30, 46)], [], 154000, 208000),

        # -- finale
        ('百万石塔', 10, [t(0, 15, mix1, {0: 28, 3: 24, 6: 24, 9: 22, 12: 20}, 260),
                          lambda: merge(pillar(-430, 0, 44, 190, S), pillar(430, 0, 44, 190, S))],
         [(-430, 200, 28), (430, 200, 28)], [], 164000, 220000),
        ('最后一战', 10, [t(-320, 12, mix3, {0: 28, 4: 24, 8: 20}, 210),
                          t(0, 16, mix1, {0: 28, 6: 26, 10: 24, 14: 20}, 250),
                          t(320, 12, mix4, {0: 26, 5: 22, 9: 20}, 210)],
         [(-570, 30, 46), (570, 30, 46)], [], 174000, 234000),
    ]


def build_levels():
    levels = []
    for name, birds, structures, loose, tnt, two, three in _specs():
        blocks, pigs = [], []
        for structure in structures:
            b, p = structure()
            blocks += b
            pigs += p
        for x, y, radius in loose:
            pigs.append(_p(x, y, radius))
        levels.append(Level(name, birds, blocks, pigs, list(tnt), two, three))
    return levels


LEVELS = build_levels()

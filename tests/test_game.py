"""Deterministic checks for the physics and level flow (no desktop windows needed)."""
from __future__ import annotations

import math
import unittest
from unittest.mock import patch

import dab.game as game_module
from dab.game import AngryBirdsGame, LEVELS
from dab.overlay import GamePointer


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def run_seconds(game, clock, seconds):
    for _ in range(max(1, int(seconds * 60))):
        clock.now += 1 / 60
        game.step(1 / 60)


def shoot(game, angle, power=1.0):
    assert game.state == 'ready', game.state
    direction = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    ax, ay = game.anchor
    pull = game.max_drag * power
    game.begin_drag(ax, ay)
    game.drag_to(ax - direction[0] * pull, ay - direction[1] * pull)
    game.release()
    assert game.state == 'flying', game.state


class GameTests(unittest.TestCase):
    def test_idle_towers_stay_put(self):
        for index in range(len(LEVELS)):
            clock = Clock()
            with patch('dab.game.time.monotonic', clock):
                game = AngryBirdsGame(1600, 1000)
                game.load_level(index)
                variants = [obj.variant for obj in game.objects if obj.kind == 'pig']
                self.assertEqual(variants, list(range(len(variants))), f'level {index} pig variants')
                before = [(obj.uid, obj.body.position, obj.dead, obj.hp) for obj in game.objects]
                run_seconds(game, clock, 6)
                after = {obj.uid: obj for obj in game.objects}
                for uid, position, dead, hp in before:
                    obj = after[uid]
                    self.assertEqual(obj.dead, dead, f'level {index} uid {uid} died while idle')
                    self.assertLess(abs(obj.body.position.x - position.x), 1.0)
                    self.assertLess(abs(obj.body.position.y - position.y), 1.0)
                    self.assertGreaterEqual(obj.hp, hp - 1.0)

    def test_each_level_can_be_won(self):
        # (angle, power, ability delay) per shot, harvested by replaying each
        # plan with exactly this 12 s tail at 2560x1380.
        # (angle, power, ability delay) per shot, harvested with the shipped
        # bird roster and this exact 12 s replay tail at 2560x1380.
        # (angle, power, ability delay) per shot, harvested with the shipped
        # bird roster and a fresh game per level at 2560x1380.
        cases = {
            0: [(-12, 1.0, None)],
            1: [(-12, 1.0, None)],
            2: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            3: [(-12, 1.0, None)],
            4: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            5: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            6: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            7: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            8: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            9: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            10: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            11: [(-12, 1.0, None), (-20, 1.0, None)],
            12: [(-12, 1.0, None)],
            13: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            14: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            15: [(-12, 1.0, None), (-20, 1.0, None)],
            16: [(-12, 1.0, None), (-20, 1.0, None)],
            17: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            18: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            19: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            20: [(-12, 1.0, None)],
            21: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            22: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            23: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            24: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            25: [(-12, 1.0, None), (-20, 1.0, None)],
            26: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            27: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            28: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            29: [(-12, 1.0, None), (-20, 1.0, None)],
            30: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            31: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            32: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            33: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            34: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            35: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            36: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            37: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            38: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            39: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            40: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            41: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            42: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            43: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            44: [(-12, 1.0, None)],
            45: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            46: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            47: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            48: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            49: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            50: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            51: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            52: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            53: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            54: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            55: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            56: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            57: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None)],
            58: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            59: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            60: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            61: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            62: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None)],
            63: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            64: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            65: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None), (0, 1.0, None)],
            66: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            67: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None), (0, 1.0, None), (-68, 1.0, None), (20, 1.0, None)],
            68: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            69: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None)],
            70: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            71: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None)],
            72: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None)],
            73: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None)],
            74: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None)],
            75: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            76: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            77: [(-12, 1.0, None), (-20, 1.0, None)],
            78: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            79: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            80: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            81: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            82: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            83: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None)],
            84: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None), (16, 1.0, None), (0, 1.0, None), (-68, 1.0, None), (20, 1.0, None)],
            85: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            86: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            87: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            88: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            89: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            90: [(-12, 1.0, None), (-20, 1.0, None)],
            91: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            92: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            93: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            94: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
            95: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None)],
            96: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            97: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None), (-60, 1.0, None), (-8, 1.0, None)],
            98: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None), (-44, 1.0, None), (-52, 1.0, None), (12, 1.0, None)],
            99: [(-12, 1.0, None), (-20, 1.0, None), (-4, 1.0, None), (-28, 1.0, None), (-36, 1.0, None), (4, 1.0, None)],
        }
        self.assertEqual(len(cases), len(LEVELS))
        for index, shots in cases.items():
            clock = Clock()
            with patch('dab.game.time.monotonic', clock):
                game = AngryBirdsGame(2560, 1380)
                game.load_level(index)
                for angle, power, delay in shots:
                    if game.state == 'won':
                        break
                    shoot(game, angle, power)
                    if delay is not None:
                        run_seconds(game, clock, delay)
                        game.trigger_ability()
                    run_seconds(game, clock, 12)
                self.assertEqual(game.state, 'won', f'level {index} ended as {game.state}')
                self.assertEqual(game.pigs_left(), 0)
                self.assertGreater(game.score, 0)


class SpecialBirdTests(unittest.TestCase):
    def test_bomb_explodes_and_split_makes_three(self):
        clock = Clock()
        with patch('dab.game.time.monotonic', clock):
            game = AngryBirdsGame(2560, 1380)
            game.load_level(0)
            self.assertEqual(game.level.types[0], 'red')
            # A deliberately weak lob: enough to use the bird, far from any pig.
            game.begin_drag(*game.anchor)
            game.drag_to(game.anchor[0] - game.max_drag * 0.12,
                         game.anchor[1] + game.max_drag * 0.12)
            game.release()
            run_seconds(game, clock, 12)
            self.assertEqual(game.bird_kind, 'bomb')
            shoot(game, 0)
            run_seconds(game, clock, 0.1)
            game.trigger_ability()
            self.assertTrue(game.ability_used)
            run_seconds(game, clock, 4)
            self.assertIn(game.state, ('between', 'ready', 'won'))
            for _ in range(80):
                clock.now += 1 / 60
                game.step(1 / 60)
            self.assertEqual(game.bird_kind, 'split')
            shoot(game, 0)
            run_seconds(game, clock, 0.1)
            game.trigger_ability()
            self.assertEqual(len(game.split_children), 3)
            self.assertEqual(len(game._flying_bodies()), 3)
            run_seconds(game, clock, 12)
            self.assertEqual(game.split_children, [])


class InputTests(unittest.TestCase):
    def test_drag_release_fires_a_bird(self):
        game = AngryBirdsGame(2560, 1380)
        pointer = GamePointer()
        ax, ay = game.anchor
        pointer.update(game, ax, ay, True, True)
        self.assertTrue(game.dragging)
        pointer.update(game, ax - game.max_drag, ay + 20, True, True)
        pointer.update(game, ax - game.max_drag, ay + 20, False, True)
        self.assertEqual(game.state, 'flying')
        self.assertEqual(game.shots, 1)
        self.assertIsNotNone(game.bird_body)


if __name__ == '__main__':
    unittest.main()

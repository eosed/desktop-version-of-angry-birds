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
        # (angle, power, ability delay) per shot, found with _probe.py at 2560x1380.
        cases = {
            0: [(-15, 0.85, None)],
            1: [(-8, 0.85, None), (-20, 0.85, None)],
            2: [(-11, 0.85, None)],
            3: [(-5, 1.0, None), (-26, 0.85, None)],
            4: [(-24, 0.85, None)],
            5: [(3, 0.85, None), (-2, 0.85, None)],
            6: [(-22, 0.85, None)],
            7: [(-2, 0.85, None), (-4, 1.0, 0.5), (0, 1.0, None)],
            8: [(-17, 0.85, None), (-8, 1.0, None), (-4, 0.85, None)],
            9: [(4, 0.85, None)],
            10: [(-21, 0.85, None)],
            11: [(-9, 1.0, None), (-14, 1.0, None), (-8, 0.85, 0.5)],
            12: [(16, 1.0, None), (-29, 1.0, None)],
            13: [(4, 0.85, None)],
            14: [(-9, 1.0, None), (-13, 1.0, 0.5)],
            15: [(-2, 1.0, None), (-4, 1.0, None)],
            16: [(-29, 1.0, None)],
            17: [(-24, 1.0, None), (-13, 0.85, None)],
            18: [(-1, 1.0, None), (-8, 1.0, 0.5), (-32, 0.85, 0.5)],
            19: [(-2, 0.85, None)],
            20: [(-6, 0.85, None), (-21, 0.85, None)],
            21: [(-1, 0.85, None), (-32, 0.85, None)],
            22: [(-19, 1.0, None), (-23, 0.85, None)],
            23: [(-6, 1.0, None), (2, 1.0, None)],
            24: [(-25, 0.85, None), (-28, 1.0, None)],
            25: [(3, 1.0, None), (2, 0.85, None), (-32, 0.85, None)],
            26: [(6, 1.0, None), (-32, 0.85, None)],
            27: [(9, 0.85, None), (-19, 1.0, None), (-32, 0.85, None)],
            28: [(-1, 1.0, None), (-21, 0.85, None), (15, 1.0, 0.5), (-30, 0.85, None)],
            29: [(1, 0.85, None), (-23, 0.85, None), (-32, 0.85, None)],
            30: [(-13, 0.85, None), (-31, 0.85, None)],
            31: [(-16, 1.0, None), (-12, 1.0, None), (0, 0.85, 0.5), (-32, 0.85, None)],
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

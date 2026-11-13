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


def shoot(game, angle):
    assert game.state == 'ready', game.state
    direction = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    ax, ay = game.anchor
    game.begin_drag(ax, ay)
    game.drag_to(ax - direction[0] * game.max_drag, ay - direction[1] * game.max_drag)
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
        cases = {
            0: [(-9, None)],
            1: [(-7, None)],
            2: [(-4, None), (-7, None)],
            3: [(-2, None)],
            4: [(-15, None)],
            5: [(-8, None), (-5, None)],
            6: [(-11, None)],
            7: [(-15.5, None), (-5, None)],
            8: [(-5, None), (-7, 0.4)],
            9: [(-4, None), (-12, 0.8)],
            10: [(-9, None)],
            11: [(-6, None), (-7.5, 1.0), (-18, 0.2)],
            12: [(-10, None), (-7, 0.4)],
            13: [(-4, None), (-10, 1.0)],
            14: [(-9, None)],
            15: [(-6, None), (-15, 0.8), (-8, 0.4)],
            16: [(-3, None), (-4, 0.6)],
            17: [(-3, None), (-6, 0.6)],
            18: [(-7.5, None), (6, None)],
            19: [(-18, None), (-10, 0.8), (-7.5, 0.4)],
            20: [(-17, None)],
            21: [(-17, None), (0, 0.35)],
            22: [(-16, None), (-18, 0.7)],
            23: [(-12.5, None)],
            24: [(-0.5, None), (-18, None)],
            25: [(-13, None)],
            26: [(-1, None), (-17, None)],
            27: [(-9.5, None), (-12.5, 0.7), (-3, 0.35)],
            28: [(-3, None), (-18, None)],
            29: [(-0.5, None), (-16, 0.7)],
            30: [(0, None), (-17, None)],
            31: [(-17.5, None), (-17.5, None)],
        }
        self.assertEqual(len(cases), len(LEVELS))
        for index, shots in cases.items():
            clock = Clock()
            with patch('dab.game.time.monotonic', clock):
                game = AngryBirdsGame(2560, 1380)
                game.load_level(index)
                for angle, delay in shots:
                    if game.state == 'won':
                        break
                    shoot(game, angle)
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
            game.load_level(10)
            self.assertEqual(game.level.types[0], 'red')
            game.begin_drag(*game.anchor)
            game.drag_to(game.anchor[0] - game.max_drag, game.anchor[1] + 30)
            game.release()
            run_seconds(game, clock, 12)
            self.assertEqual(game.bird_kind, 'bomb')
            shoot(game, -9)
            run_seconds(game, clock, 0.5)
            game.trigger_ability()
            self.assertTrue(game.ability_used)
            run_seconds(game, clock, 4)
            self.assertIn(game.state, ('between', 'ready', 'won'))
            for _ in range(80):
                clock.now += 1 / 60
                game.step(1 / 60)
            self.assertEqual(game.bird_kind, 'split')
            shoot(game, -9)
            run_seconds(game, clock, 0.5)
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

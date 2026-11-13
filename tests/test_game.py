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
            2: [(-7, None), (-18, 0.7)],
            3: [(-8, None)],
            4: [(-15, None)],
            5: [(-12, None)],
            6: [(-10, None)],
            7: [(-6, None), (-2, 0.7)],
            8: [(-10, None), (-1, 0.7)],
            9: [(-4, None), (-26, 0.7)],
            10: [(-22, None)],
            11: [(-17, None), (-5, 1.0)],
            12: [(-9, None), (0, 0.7)],
            13: [(-3, None), (-7, 0.7)],
            14: [(1, None), (-25, 1.0)],
            15: [(-21, None), (-13, 0.7)],
            16: [(-6, None), (-6, 0.7)],
            17: [(-10, None)],
            18: [(-2, None), (-1, None)],
            19: [(-26, None)],
            20: [(-5, None)],
            21: [(-5, None), (-6, 0.7)],
            22: [(-7, None), (-19, 0.7)],
            23: [(-1, None), (-5, 0.35)],
            24: [(-5, None), (4, None)],
            25: [(-8, None), (-6, 0.7)],
            26: [(-2, None), (-27, 0.7)],
            27: [(-8, None), (-2, 0.35)],
            28: [(-14, None)],
            29: [(-18, None)],
            30: [(-8, None), (-11, 0.7)],
            31: [(-1, None), (0, 1.0)],
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

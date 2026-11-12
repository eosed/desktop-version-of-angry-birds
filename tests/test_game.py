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
            0: [-9],
            1: [-7],
            2: [-4, -7],
        }
        for index, angles in cases.items():
            clock = Clock()
            with patch('dab.game.time.monotonic', clock):
                game = AngryBirdsGame(2560, 1380)
                game.load_level(index)
                for angle in angles:
                    if game.state == 'won':
                        break
                    shoot(game, angle)
                    run_seconds(game, clock, 12)
                self.assertEqual(game.state, 'won', f'level {index} ended as {game.state}')
                self.assertEqual(game.pigs_left(), 0)
                self.assertGreater(game.score, 0)


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

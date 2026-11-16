"""Levels imported from the original Angry Birds.

The 100 layouts in :mod:`dab.original_levels` are the real game's levels
transcribed as tile matrices.  Each matrix is turned into the game's own
coordinate system by cutting it into rectangles of one material, so a
single-column ice stack becomes one tall beam and a wide roof becomes one
lintel.  Pigs keep their size from the matrix letter.  Grids are
bottom-aligned to the ground so the 15-row matrices fill the same sky the
hand-authored towers did.

The corpus is an occupancy map read off screenshots, so islands of material
sometimes hang in mid-air with nothing under them; left alone they fall on
the first frame and shake the tower apart.  :func:`_settle_islands` lowers
each island until something holds it up, which keeps the original
silhouette instead of scattering the pieces.
"""
from __future__ import annotations

from dataclasses import dataclass

from .original_levels import GRIDS

WOOD = 'wood'
STONE = 'stone'
ICE = 'ice'

RED = 'red'
BOMB = 'bomb'
SPLIT = 'split'
BIRD_NAMES = {RED: '红鸟', BOMB: '炸弹鸟', SPLIT: '分裂鸟'}

CEILING = 770.0          # design-space height above the ground
MAX_TILE = 52.0          # one cell side, before a tall or wide level shrinks it
SPAN = 928.0             # widest castle that still fits beside the slingshot
MATERIAL = {'w': WOOD, 's': STONE, 'i': ICE}
PIG_RADIUS = {'A': 0.34, 'B': 0.40, 'C': 0.46, 'D': 0.50}   # of one tile side

# The corpus is grouped by matrix size, which matches how the originals grew.
CHAPTERS = ((60, '原始版'), (74, '宽屏版'), (92, '高塔版'), (100, '终章'))
NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


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


def _chapter(number):
    for last, title in CHAPTERS:
        if number <= last:
            return title
    return CHAPTERS[-1][1]


def _rects(grid):
    """Cut the matrix into maximal rectangles of one material.

    A column of ice cells becomes a single tall beam instead of a stack of
    loose cubes, which is both what the originals look like and what keeps
    a twelve-storey tower standing in the physics engine.
    """
    rows = len(grid)
    cells = {(row, col): MATERIAL.get(line[col])
             for row, line in enumerate(grid)
             for col in range(len(line))}
    used, parts = set(), []
    for row in range(rows):
        for col in range(max(len(line) for line in grid)):
            kind = cells.get((row, col))
            if kind is None or (row, col) in used:
                continue
            width = 1
            while cells.get((row, col + width)) == kind and (row, col + width) not in used:
                width += 1
            height = 1
            while all(cells.get((row + height, col + step)) == kind
                      and (row + height, col + step) not in used for step in range(width)):
                height += 1
            for dr in range(height):
                for dc in range(width):
                    used.add((row + dr, col + dc))
            parts.append([kind, row, col, height, width])
    return parts


def _islands(parts):
    """Group parts that touch by side or corner into rigid islands."""
    owners = {}
    for index, (_kind, row, col, height, width) in enumerate(parts):
        for dr in range(height):
            for dc in range(width):
                owners[(row + dr, col + dc)] = index
    parent = list(range(len(parts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for (row, col), index in owners.items():
        for dr, dc in NEIGHBOURS:
            other = owners.get((row + dr, col + dc))
            if other is not None and parts[other][0] == parts[index][0]:
                a, b = find(index), find(other)
                if a != b:
                    parent[a] = b
    islands = {}
    for index in range(len(parts)):
        islands.setdefault(find(index), []).append(index)
    return owners, list(islands.values())


def _settle_islands(parts, pigs, rows):
    """Lower each island until a cell under it rests on something else."""
    owners, islands = _islands(parts)

    def rebuild():
        owners.clear()
        for index, (_kind, row, col, height, width) in enumerate(parts):
            for dr in range(height):
                for dc in range(width):
                    owners[(row + dr, col + dc)] = index

    for _ in range(rows * 2):
        moved = False
        for group in islands:
            under = set()
            for index in group:
                _kind, row, col, height, width = parts[index]
                for dc in range(width):
                    under.add(row + height)
            if all(row >= rows for row in under):
                continue
            held = False
            for row in under:
                for index in group:
                    _kind, top, col, height, width = parts[index]
                    if top + height != row:
                        continue
                    for dc in range(width):
                        below = (row, col + dc)
                        holder = owners.get(below)
                        if (holder is not None and holder not in group) or below in pigs:
                            held = True
                            break
                    if held:
                        break
                if held:
                    break
            if not held and all(row < rows for row in under):
                for index in group:
                    parts[index][1] += 1
                rebuild()
                moved = True
        for cell in list(pigs):
            row, col = cell
            if row + 1 < rows and (row + 1, col) not in owners:
                pigs[(row + 1, col)] = pigs.pop(cell)
                moved = True
        if not moved:
            break
    return parts, pigs


def grid_to_shapes(grid):
    """Blocks and pigs for one matrix, in the game's centred design space."""
    rows = len(grid)
    cols = max(len(line) for line in grid)
    tile = min(MAX_TILE, CEILING / rows, SPAN / cols)
    width = cols * tile
    pigs = {(row, col): PIG_RADIUS[line[col]]
            for row, line in enumerate(grid)
            for col in range(len(line)) if line[col] in PIG_RADIUS}
    parts, pigs = _settle_islands(_rects(grid), pigs, rows)
    blocks = [(kind, (col + w / 2) * tile - width / 2,
               (rows - row - h / 2) * tile, w * tile, h * tile, 0.0)
              for kind, row, col, h, w in parts]
    pig_shapes = [((col + 0.5) * tile - width / 2, (rows - row - 0.5) * tile,
                   radius * tile) for (row, col), radius in pigs.items()]
    return blocks, pig_shapes


def build_levels():
    levels = []
    for number, grid in enumerate(GRIDS, 1):
        blocks, pigs = grid_to_shapes(grid)
        worth = len(pigs) * 5000 + sum(500 if block[0] == WOOD else 800 for block in blocks)
        # A win clears every pig; spare birds and rubble add the rest.  Two
        # stars should be reachable by simply winning, three need the rubble.
        # Imported castles are far denser than the hand-built ones, so the
        # roster follows the measured shot budget (harvest runs) instead of
        # the old 3-per-three-pigs rule.
        birds = max(3, min(16, 5 + len(pigs) + len(blocks) // 5))
        levels.append(Level(_chapter(number), birds, blocks, pigs, [],
                            int(worth * 0.75), int(worth * 1.15)))
    return levels


LEVELS = build_levels()

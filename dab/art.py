"""Procedural artwork for the desktop Angry Birds game.

Everything is drawn with Pillow at runtime, so the repository carries no binary
assets and the game stays crisp on any DPI.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_REGULAR = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'

INK = (36, 44, 32, 255)
CREAM = (255, 246, 219, 255)
RED = (213, 57, 53, 255)
RED_DARK = (145, 31, 33, 255)
GREEN = (124, 196, 70, 255)
GREEN_DARK = (54, 113, 43, 255)
BIRD_LABELS = {'red': '红鸟', 'bomb': '炸弹鸟', 'split': '分裂鸟'}


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, max(8, int(size)))
    except OSError:
        return ImageFont.load_default(max(8, int(size)))


def _supersampled(size, painter, factor=3):
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    big = Image.new('RGBA', (width * factor, height * factor), (0, 0, 0, 0))
    painter(ImageDraw.Draw(big), factor)
    return big.resize((width, height), Image.LANCZOS)


def _shadowed_text(draw, xy, text, fnt, fill=CREAM, shadow=(0, 0, 0, 130), offset=2):
    x, y = xy
    draw.text((x + offset, y + offset), text, font=fnt, fill=shadow)
    draw.text((x, y), text, font=fnt, fill=fill)


def background(width, height, ground_y, sling_x, fork_y, scale, wallpaper=None):
    """Desktop wallpaper, grass, dirt and the slingshot fork (one static frame).

    ``wallpaper`` is the real Windows wallpaper cropped to the work area.  The
    upstream billiards project keeps the desktop itself as the playfield; this
    game does the same instead of hiding it behind a synthetic sky.
    """
    width, height = int(width), int(height)
    if wallpaper is not None:
        image = wallpaper.convert('RGB').resize((width, height), Image.LANCZOS).convert('RGBA')
        image = image.filter(ImageFilter.GaussianBlur(radius=max(4, min(14, height / 140))))
        image = Image.alpha_composite(image, Image.new('RGBA', (width, height), (10, 30, 46, 28)))
        draw = ImageDraw.Draw(image)
    else:
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        top = (104, 194, 245)
        bottom = (216, 243, 255)
        for y in range(height):
            t = min(1.0, y / max(1.0, float(ground_y)))
            color = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            draw.line((0, y, width, y), fill=color + (255,))
        # sun and soft clouds
        sun_r = 70 * scale
        draw.ellipse((width * 0.09 - sun_r, height * 0.08 - sun_r, width * 0.09 + sun_r, height * 0.08 + sun_r),
                     fill=(255, 236, 150, 210))
        random.seed(11)
        for cx, cy, size in ((0.32, 0.13, 1.0), (0.58, 0.08, 0.7), (0.84, 0.17, 1.25)):
            x, y, s = width * cx, height * cy, scale * size
            for dx, dy, rx, ry in ((-80, 10, 90, 34), (0, -12, 110, 48), (85, 8, 80, 30)):
                draw.ellipse((x + dx * s - rx * s, y + dy * s - ry * s, x + dx * s + rx * s, y + dy * s + ry * s),
                             fill=(255, 255, 255, 150))
        # rolling hills
        for offset, color, height_factor in ((0.0, (126, 193, 108, 255), 0.10),
                                             (0.25, (100, 174, 96, 255), 0.07)):
            points = [(0, ground_y)]
            for i in range(0, width + 80, 80):
                points.append((i, ground_y - (math.sin(i / 230 + offset * 8) * 0.5 + 0.5) * height * height_factor - 22 * scale))
            points += [(width, ground_y)]
            draw.polygon(points, fill=color)
    # ground: grass strip + dirt body
    if wallpaper is not None:
        draw.rectangle((0, ground_y - 5, width, ground_y), fill=(0, 0, 0, 55))
    draw.rectangle((0, ground_y, width, height), fill=(120, 76, 44, 255))
    draw.rectangle((0, ground_y, width, ground_y + 26 * scale), fill=(92, 166, 63, 255))
    draw.rectangle((0, ground_y + 22 * scale, width, ground_y + 32 * scale), fill=(66, 133, 48, 255))
    random.seed(4)
    for _ in range(int(220 * scale)):
        x = random.uniform(0, width)
        y = random.uniform(ground_y + 40 * scale, height)
        r = random.uniform(1, 3) * scale
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(96, 59, 33, 150))
    for _ in range(int(90 * scale)):
        x = random.uniform(0, width)
        y = random.uniform(ground_y + 2, ground_y + 24 * scale)
        draw.line((x, y, x + random.uniform(-4, 4), y + 9 * scale), fill=(60, 120, 44, 200), width=max(1, int(scale)))
    # slingshot: wooden Y, feet planted on the grass
    wood = (126, 79, 40, 255)
    wood_light = (170, 112, 60, 255)
    outline = (74, 42, 20, 255)
    base_y = ground_y + 6 * scale
    top_y = fork_y
    width_line = max(7, int(16 * scale))
    left_tip = (sling_x - 46 * scale, top_y)
    right_tip = (sling_x + 46 * scale, top_y)
    draw.line((sling_x, base_y, sling_x, top_y + 78 * scale), fill=outline, width=width_line + 8)
    draw.line((sling_x, base_y, sling_x, top_y + 78 * scale), fill=wood, width=width_line)
    draw.line((sling_x, top_y + 92 * scale, left_tip[0], left_tip[1]), fill=outline, width=width_line + 6)
    draw.line((sling_x, top_y + 92 * scale, right_tip[0], right_tip[1]), fill=outline, width=width_line + 6)
    draw.line((sling_x, top_y + 92 * scale, left_tip[0], left_tip[1]), fill=wood_light, width=width_line)
    draw.line((sling_x, top_y + 92 * scale, right_tip[0], right_tip[1]), fill=wood_light, width=width_line)
    for tx, ty in (left_tip, right_tip):
        r = 12 * scale
        draw.ellipse((tx - r, ty - r, tx + r, ty + r), fill=outline)
        r2 = 8 * scale
        draw.ellipse((tx - r2, ty - r2, tx + r2, ty + r2), fill=wood_light)
    # little grass tufts around the feet
    for dx in (-34, -12, 16, 38):
        x = sling_x + dx * scale
        draw.line((x, ground_y + 4 * scale, x - 5 * scale, ground_y - 14 * scale), fill=(65, 133, 49, 255), width=max(2, int(3 * scale)))
    # Drawing translucent shapes onto a transparent canvas replaces their alpha; make
    # the finished scene opaque so the Windows desktop never shows through clouds.
    image.putalpha(255)
    return image


def ability_tag(text, scale=1.0):
    """A small floating pill that explains a special bird's one-click ability."""
    fnt = font(max(10, round(14 * scale)), bold=True)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    box = probe.textbbox((0, 0), text, font=fnt)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad_x, pad_y = max(7, round(9 * scale)), max(4, round(5 * scale))
    width, height = tw + pad_x * 2, th + pad_y * 2 + max(4, round(6 * scale))
    image = Image.new('RGBA', (width, height + max(4, round(7 * scale))), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 2,
                           fill=(24, 32, 30, 238), outline=(255, 214, 130, 235),
                           width=max(1, round(1.5 * scale)))
    draw.text((pad_x - box[0], pad_y - box[1]), text, font=fnt, fill=CREAM)
    # little pointer towards the bird
    tip = height + max(3, round(5 * scale))
    draw.polygon([(width / 2 - 5 * scale, height - 1), (width / 2 + 5 * scale, height - 1),
                  (width / 2, tip)], fill=(255, 214, 130, 235))
    return image


def block_sprite(kind, width, height):
    width, height = max(6, int(round(width))), max(6, int(round(height)))
    wood = kind == 'wood'
    ice = kind == 'ice'

    def painter(draw, f):
        w, h = width * f, height * f
        pad = 2 * f
        radius = min(w, h) * 0.16
        if ice:
            base, light, dark, line = (170, 224, 242), (226, 249, 255), (94, 158, 192), (118, 186, 214)
        elif wood:
            base, light, dark, line = (181, 126, 66), (214, 160, 95), (111, 71, 33), (139, 91, 45)
        else:
            base, light, dark, line = (139, 143, 150), (177, 181, 187), (82, 86, 93), (107, 111, 118)
        draw.rounded_rectangle((pad, pad, w - pad, h - pad), radius=radius, fill=base + (235 if ice else 255,),
                               outline=dark + (255,), width=max(1, int(2 * f)))
        if ice:
            # A couple of diagonal cracks read as "fragile" next to wood and stone.
            draw.line((w * 0.28, pad, w * 0.42, h * 0.45, w * 0.3, h * 0.62, w * 0.46, h - pad),
                      fill=light + (235,), width=max(1, int(2 * f)))
            draw.line((w * 0.68, pad, w * 0.56, h * 0.35, w * 0.72, h * 0.55),
                      fill=(255, 255, 255, 220), width=max(1, int(1.5 * f)))
            draw.rectangle((pad + 4 * f, pad + 4 * f, w - pad - 4 * f, pad + 7 * f), fill=(255, 255, 255, 210))
        elif wood:
            step = max(8 * f, min(h, w) / 5)
            y = step
            while y < h - pad:
                draw.line((pad + 2 * f, y, w - pad - 2 * f, y), fill=line + (180,), width=max(1, int(1.5 * f)))
                y += step
            # knots
            for kx, ky in ((w * 0.32, h * 0.3), (w * 0.68, h * 0.68)):
                r = max(2 * f, min(w, h) * 0.06)
                draw.ellipse((kx - r, ky - r, kx + r, ky + r), outline=line + (220,), width=max(1, int(1.5 * f)))
            draw.line((pad, pad + 2 * f, pad, h - pad), fill=light + (160,), width=max(1, int(2 * f)))
        else:
            for _ in range(max(10, int(w * h / (900 * f)))):
                x = random.uniform(pad, w - pad)
                y = random.uniform(pad, h - pad)
                r = random.uniform(1, 3) * f
                draw.ellipse((x - r, y - r, x + r, y + r), fill=light + (120,))
            draw.line((w * 0.2, h * 0.2, w * 0.55, h * 0.5, w * 0.4, h * 0.8), fill=dark + (130,), width=max(1, int(1.5 * f)))
        # corner bolts
        for cx, cy in ((pad + 6 * f, pad + 6 * f), (w - pad - 6 * f, pad + 6 * f),
                       (pad + 6 * f, h - pad - 6 * f), (w - pad - 6 * f, h - pad - 6 * f)):
            r = max(1.5 * f, min(w, h) * 0.025)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=dark + (220,))

    return _supersampled((width, height), painter)


def pig_sprite(radius):
    size = int(round(radius * 2.35))
    r = radius

    def painter(draw, f):
        cx = cy = size * f / 2
        R = r * f
        # ears
        for sign in (-1, 1):
            ex = cx + sign * R * 0.62
            ey = cy - R * 0.73
            draw.ellipse((ex - R * 0.3, ey - R * 0.26, ex + R * 0.3, ey + R * 0.3), fill=GREEN_DARK, outline=GREEN_DARK)
        # body
        draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=GREEN, outline=GREEN_DARK, width=max(2, int(3 * f)))
        # belly highlight
        draw.ellipse((cx - R * 0.7, cy + R * 0.05, cx + R * 0.55, cy + R * 0.78), fill=(155, 217, 98, 180))
        # eyes
        for sign in (-1, 1):
            ex = cx + sign * R * 0.32
            ey = cy - R * 0.22
            draw.ellipse((ex - R * 0.24, ey - R * 0.27, ex + R * 0.24, ey + R * 0.21), fill=(255, 255, 255, 255),
                         outline=GREEN_DARK, width=max(1, int(1.5 * f)))
            pr = R * 0.09
            px = ex + sign * R * 0.05
            draw.ellipse((px - pr, ey - pr, px + pr, ey + pr), fill=INK)
        # angry brows
        draw.line((cx - R * 0.55, cy - R * 0.58, cx - R * 0.12, cy - R * 0.44), fill=INK, width=max(2, int(4 * f)))
        draw.line((cx + R * 0.55, cy - R * 0.58, cx + R * 0.12, cy - R * 0.44), fill=INK, width=max(2, int(4 * f)))
        # snout
        draw.ellipse((cx - R * 0.34, cy + R * 0.02, cx + R * 0.34, cy + R * 0.42), fill=(148, 213, 86, 255),
                     outline=GREEN_DARK, width=max(1, int(2 * f)))
        for sign in (-1, 1):
            nx = cx + sign * R * 0.13
            ny = cy + R * 0.22
            draw.ellipse((nx - R * 0.05, ny - R * 0.075, nx + R * 0.05, ny + R * 0.075), fill=GREEN_DARK)
        # mouth line
        draw.arc((cx - R * 0.2, cy + R * 0.35, cx + R * 0.2, cy + R * 0.55), 10, 170, fill=GREEN_DARK, width=max(1, int(2 * f)))

    return _supersampled((size, size), painter)


def bird_sprite(radius, kind='red'):
    """A red/bomb/split bird fallback for failed Shell icon extraction."""
    size = int(round(radius * 2.7))
    r = radius
    if kind == 'bomb':
        def paint_bomb(draw, f):
            cx = cy = size * f / 2
            R = r * f
            draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(40, 52, 58, 255),
                         outline=(18, 24, 28, 255), width=max(3, int(3 * f)))
            draw.ellipse((cx - R * 0.58, cy + R * 0.18, cx + R * 0.5, cy + R * 0.68),
                         fill=(78, 91, 94, 255))
            for sign in (-1, 1):
                ex = cx + sign * R * 0.30
                ey = cy - R * 0.20
                draw.ellipse((ex - R * 0.20, ey - R * 0.22, ex + R * 0.20, ey + R * 0.18),
                             fill=(255, 255, 255, 255))
                pr = R * 0.085
                draw.ellipse((ex - pr, ey - pr, ex + pr, ey + pr), fill=INK)
            draw.line((cx - R * 0.55, cy - R * 0.52, cx - R * 0.08, cy - R * 0.34),
                      fill=INK, width=max(3, int(4 * f)))
            draw.line((cx + R * 0.55, cy - R * 0.52, cx + R * 0.08, cy - R * 0.34),
                      fill=INK, width=max(3, int(4 * f)))
            draw.polygon([(cx - R * 0.15, cy + R * 0.1), (cx + R * 0.30, cy + R * 0.2),
                          (cx - R * 0.10, cy + R * 0.36)], fill=(246, 174, 45, 255))
            # fuse
            draw.line((cx + R * 0.15, cy - R * 0.98, cx + R * 0.45, cy - R * 1.35),
                      fill=(156, 144, 120, 255), width=max(2, int(3 * f)))
            draw.ellipse((cx + R * 0.35, cy - R * 1.48, cx + R * 0.62, cy - R * 1.20),
                         fill=(255, 186, 60, 255))
        return _supersampled((size, size), paint_bomb)
    if kind == 'split':
        def paint_split(draw, f):
            cx = cy = size * f / 2
            R = r * f
            draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(86, 176, 236, 255),
                         outline=(36, 104, 158, 255), width=max(2, int(3 * f)))
            draw.ellipse((cx - R * 0.55, cy + R * 0.12, cx + R * 0.52, cy + R * 0.72),
                         fill=(232, 243, 250, 255))
            for sign in (-1, 1):
                ex = cx + sign * R * 0.30
                ey = cy - R * 0.18
                draw.ellipse((ex - R * 0.20, ey - R * 0.22, ex + R * 0.20, ey + R * 0.18),
                             fill=(255, 255, 255, 255))
                pr = R * 0.085
                draw.ellipse((ex - pr, ey - pr, ex + pr, ey + pr), fill=INK)
            draw.polygon([(cx - R * 0.18, cy + R * 0.04), (cx + R * 0.34, cy + R * 0.14),
                          (cx - R * 0.16, cy + R * 0.32)], fill=(246, 174, 45, 255))
            for sign in (-1, 1):
                draw.polygon([(cx + sign * R * 0.85, cy - R * 0.2), (cx + sign * R * 1.3, cy - R * 0.6),
                              (cx + sign * R * 1.05, cy + R * 0.15)], fill=(216, 236, 248, 255),
                             outline=(36, 104, 158, 255))
        return _supersampled((size, size), paint_split)

    def painter(draw, f):
        cx = cy = size * f / 2
        R = r * f
        # tail feathers
        for angle in (150, 180, 210):
            a = math.radians(angle)
            tx, ty = cx + math.cos(a) * R * 1.15, cy + math.sin(a) * R * 1.15
            draw.line((cx, cy, tx, ty), fill=RED_DARK, width=max(4, int(R * 0.22)))
        # body
        draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=RED, outline=RED_DARK, width=max(2, int(3 * f)))
        # belly patch
        draw.ellipse((cx - R * 0.55, cy + R * 0.1, cx + R * 0.5, cy + R * 0.72), fill=(247, 210, 157, 255))
        # head cap / feather tuft
        draw.polygon([(cx - R * 0.2, cy - R * 0.95), (cx - R * 0.05, cy - R * 1.32),
                      (cx + R * 0.1, cy - R * 0.98), (cx + R * 0.34, cy - R * 1.22),
                      (cx + R * 0.32, cy - R * 0.82)], fill=RED_DARK)
        # eyes
        for sign in (-1, 1):
            ex = cx + sign * R * 0.32
            ey = cy - R * 0.18
            draw.ellipse((ex - R * 0.22, ey - R * 0.24, ex + R * 0.22, ey + R * 0.2), fill=(255, 255, 255, 255))
            pr = R * 0.09
            draw.ellipse((ex + sign * R * 0.06 - pr, ey - pr, ex + sign * R * 0.06 + pr, ey + pr), fill=INK)
        # brows
        draw.line((cx - R * 0.6, cy - R * 0.52, cx - R * 0.12, cy - R * 0.36), fill=INK, width=max(3, int(5 * f)))
        draw.line((cx + R * 0.6, cy - R * 0.52, cx + R * 0.12, cy - R * 0.36), fill=INK, width=max(3, int(5 * f)))
        # beak
        draw.polygon([(cx - R * 0.22, cy + R * 0.02), (cx + R * 0.3, cy + R * 0.12),
                      (cx - R * 0.2, cy + R * 0.3)], fill=(246, 174, 45, 255), outline=(166, 99, 22, 255))
        draw.line((cx - R * 0.2, cy + R * 0.16, cx + R * 0.12, cy + R * 0.12), fill=(166, 99, 22, 255), width=max(1, int(1.5 * f)))

    return _supersampled((size, size), painter)


def tnt_sprite(size):
    side = int(round(size))

    def painter(draw, f):
        w = side * f
        draw.rounded_rectangle((2 * f, 2 * f, w - 2 * f, w - 2 * f), radius=5 * f, fill=(199, 56, 47, 255),
                               outline=(107, 26, 22, 255), width=max(2, int(3 * f)))
        draw.rectangle((2 * f, w * 0.35, w - 2 * f, w * 0.64), fill=(243, 229, 190, 255))
        fnt = font(max(9, int(w * 0.28)), bold=True)
        text = 'TNT'
        bbox = draw.textbbox((0, 0), text, font=fnt)
        draw.text(((w - (bbox[2] - bbox[0])) / 2, (w - (bbox[3] - bbox[1])) / 2 - bbox[1]), text,
                  font=fnt, fill=(97, 29, 22, 255))
        # fuse
        draw.line((w * 0.5, 2 * f, w * 0.62, -4 * f), fill=(60, 50, 40, 255), width=max(2, int(2.5 * f)))
        draw.ellipse((w * 0.58, -8 * f, w * 0.7, 0), fill=(255, 191, 64, 255))

    return _supersampled((side, side), painter)


def band_layer(size, left_tip, right_tip, anchor, bird):
    """Rubber bands drawn over the bird; coordinates are local to the band image."""
    width, height = size
    image = Image.new('RGBA', (max(1, width), max(1, height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for tip in (left_tip, right_tip):
        draw.line((tip[0], tip[1], bird[0], bird[1]), fill=(72, 35, 22, 255), width=13)
        draw.line((tip[0], tip[1], bird[0], bird[1]), fill=(155, 87, 50, 255), width=8)
    if anchor is not None:
        draw.line((anchor[0], anchor[1], bird[0], bird[1]), fill=(102, 55, 30, 90), width=4)
    return image


def aim_dots(points, color=(255, 255, 255, 230)):
    if not points:
        return Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    pad = 18
    left, top = min(xs) - pad, min(ys) - pad
    right, bottom = max(xs) + pad, max(ys) + pad
    image = Image.new('RGBA', (max(1, int(right - left)), max(1, int(bottom - top))), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for index, (x, y) in enumerate(points):
        radius = max(2.2, 5.0 - index * 0.28)
        draw.ellipse((x - left - radius, y - top - radius, x - left + radius, y - top + radius), fill=color)
    return image, (int(left), int(top))


def hud_card(width, height, level_name, score, pigs, birds, stars, bird_kind='red'):
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, width - 2, height - 2), radius=18, fill=(16, 37, 30, 218),
                           outline=(105, 214, 165, 150), width=2)
    draw.rounded_rectangle((2, 2, 8, height - 2), radius=3, fill=(105, 214, 165, 230))
    title_f = font(height * 0.25, bold=True)
    body_f = font(height * 0.20)
    draw.text((24, 12), level_name, font=title_f, fill=(240, 250, 244, 255))
    draw.text((24, height * 0.48), f'得分  {score:,}', font=body_f, fill=(255, 226, 140, 255))
    draw.text((width * 0.38, height * 0.48), f'小猪  {pigs}', font=body_f, fill=(168, 230, 164, 255))
    draw.text((width * 0.52, height * 0.48), f'小鸟  {birds}', font=body_f, fill=(255, 190, 180, 255))
    # Two-digit bird counts reach the label column on 800 px wide cards.
    draw.text((width * 0.73, height * 0.48), BIRD_LABELS.get(bird_kind, '红鸟'), font=body_f,
              fill=(180, 228, 255, 255))
    # stars
    for index in range(3):
        cx = width - 36 - index * 30
        cy = height * 0.30
        _star(draw, cx, cy, 11, fill=(255, 205, 74, 255) if index < stars else (78, 101, 88, 255))
    return image


def _star(draw, cx, cy, r, fill):
    points = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        radius = r if index % 2 == 0 else r * 0.45
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=fill, outline=(92, 55, 15, 180))


def banner_frame(width, height, title, subtitle, won, stars=0):
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    tint = (30, 92, 55, 232) if won else (86, 34, 34, 232)
    edge = (128, 226, 147, 230) if won else (238, 139, 128, 230)
    draw.rounded_rectangle((3, 3, width - 3, height - 3), radius=26, fill=tint, outline=edge, width=3)
    title_f = font(height * 0.24, bold=True)
    sub_f = font(height * 0.12)
    bbox = draw.textbbox((0, 0), title, font=title_f)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, height * 0.10), title, font=title_f, fill=CREAM)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_f)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, height * 0.48), subtitle, font=sub_f, fill=(232, 244, 232, 255))
    if won:
        for index in range(3):
            cx = width / 2 + (index - 1) * height * 0.25
            _star(draw, cx, height * 0.73, height * 0.12,
                  fill=(255, 210, 74, 255) if index < stars else (83, 109, 91, 255))
    return image


def effect_frame(kind, elapsed, width, height, radius=0.0):
    if kind == 'pop':
        size = int(max(width, height) * 2.4)
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        cx = cy = size / 2
        t = min(1.0, elapsed / 0.45)
        for index in range(10):
            angle = index * math.tau / 10 + 0.2
            distance = (18 + 50 * t) * max(1.0, size / 100)
            r = max(1.0, (7 - 5 * t) * size / 100)
            x, y = cx + math.cos(angle) * distance, cy + math.sin(angle) * distance
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(240, 248, 240, int(255 * (1 - t))))
        return image
    if kind == 'boom':
        size = int(max(width, height) * 3.4)
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        cx = cy = size / 2
        t = min(1.0, elapsed / 0.55)
        for index in range(16):
            angle = index * math.tau / 16
            distance = (20 + 80 * t) * max(1.0, size / 140)
            r = (16 - 10 * t) * size / 140
            color = (255, 170, 60, int(245 * (1 - t))) if index % 2 else (255, 92, 46, int(235 * (1 - t)))
            x, y = cx + math.cos(angle) * distance, cy + math.sin(angle) * distance
            draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
        r = size * 0.22 * (1 - t)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 240, 190, int(220 * (1 - t))))
        return image
    # block break fragments
    width, height = int(max(width, height * 1.2)), int(max(height, width * 0.8))
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    t = min(1.0, elapsed / 0.55)
    random.seed(width * 31 + height * 17)
    for _ in range(14):
        x = random.uniform(width * 0.15, width * 0.85) + random.uniform(-50, 50) * t
        y = random.uniform(0, height * 0.7) + random.uniform(-60, 90) * t
        w = random.uniform(5, 18) * max(0.6, width / 120)
        h = random.uniform(4, 12) * max(0.6, height / 80)
        color = (181, 126, 66, int(230 * (1 - t))) if random.random() < 0.5 else (111, 71, 33, int(220 * (1 - t)))
        draw.rectangle((x, y, x + w, y + h), fill=color)
    return image

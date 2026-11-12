"""Layered desktop windows that draw and run the Angry Birds game."""
from __future__ import annotations

import ctypes
import math
import os
import struct
import threading
from ctypes import wintypes as W

import comtypes  # noqa: F401  (kept for the Shell dependency footprint)
import win32api
import win32con
import win32gui
import win32process
from PIL import Image, ImageDraw

from . import art, diag
from .display import monitors
from .game import AngryBirdsGame, LEVELS
from .icons import artwork as icon_artwork, select_bird_ids
from .shell import ShellDesktop, atomic_json
from .wallpaper import primary_wallpaper

WS_EX_LAYERED = 0x80000
WS_EX_NOACTIVATE = 0x08000000
SM_SWAPBUTTON = 23


def desktop_listview():
    """Return the (SHELLDLL_DefView, SysListView32) pair that draws the icons."""
    found = []

    def visit(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'SHELLDLL_DefView':
            child = win32gui.FindWindowEx(hwnd, 0, 'SysListView32', None)
            if child:
                found.append((hwnd, child))
        return True

    def top(hwnd, _):
        win32gui.EnumChildWindows(hwnd, visit, None)
        return True

    win32gui.EnumWindows(top, None)
    if not found:
        raise RuntimeError('找不到 Explorer 桌面图标窗口')
    return max(found, key=lambda pair: (bool(win32gui.IsWindowVisible(pair[1])),
                                        int(win32gui.SendMessage(pair[1], 0x1004, 0, 0))))


def map_rect(rect, source_origin, target_origin):
    dx = source_origin[0] - target_origin[0]
    dy = source_origin[1] - target_origin[1]
    return (rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy)


class LayerSurface:
    """One top-down BGRA DIB reused by a layered child window."""

    def __init__(self, hwnd, size, x, y):
        self.hwnd = hwnd
        self.size = size
        self.bitmap = None
        self.old = None
        self.last_frame = None
        self.dc = win32gui.CreateCompatibleDC(0)
        self.bits = ctypes.c_void_p()
        try:
            width, height = size
            header = ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0,
                                                             width * height * 4, 0, 0, 0, 0))
            create = ctypes.windll.gdi32.CreateDIBSection
            create.argtypes = [W.HDC, ctypes.c_void_p, W.UINT, ctypes.POINTER(ctypes.c_void_p), W.HANDLE, W.DWORD]
            create.restype = W.HBITMAP
            self.bitmap = create(self.dc, header, 0, ctypes.byref(self.bits), None, 0)
            if not self.bitmap:
                raise ctypes.WinError()
            self.old = win32gui.SelectObject(self.dc, self.bitmap)
            self.point = (x, y)
        except Exception:
            self.close()
            raise

    def present(self, frame, x=None, y=None):
        if x is not None:
            self.point = (x, y)
        if frame is not self.last_frame:
            data = frame.convert('RGBa').tobytes('raw', 'BGRa')
            ctypes.memmove(self.bits, data, len(data))
            self.last_frame = frame
        win32gui.UpdateLayeredWindow(self.hwnd, 0, self.point, self.size, self.dc, (0, 0), 0, (0, 0, 255, 1), 2)

    def close(self):
        if self.old:
            win32gui.SelectObject(self.dc, self.old)
            self.old = None
        if self.bitmap:
            win32gui.DeleteObject(self.bitmap)
            self.bitmap = None
        if self.dc:
            win32gui.DeleteDC(self.dc)
            self.dc = None


class GamePointer:
    """Aim with the physical left button; release to fire."""

    def __init__(self):
        self.was_down = False

    def update(self, game, x, y, down, on_desktop):
        if on_desktop and down and not self.was_down:
            if game.begin_drag(x, y):
                game.drag_to(x, y)
        elif game.dragging:
            game.drag_to(x, y)
            if not down:
                game.release()
        self.was_down = down


class GameOverlay:
    def __init__(self, desktop):
        self.desktop = desktop
        self.parent, self.listview = desktop_listview()
        self.geometry = desktop.get_geometry()
        self.monitor_state = monitors()
        primary = next(m for m in self.monitor_state if m[4])
        self.primary = primary
        self.primary_bounds = map_rect(primary[2], (0, 0), win32gui.ClientToScreen(self.parent, (0, 0)))
        left, top, right, bottom = self.primary_bounds
        self.width = right - left
        self.height = bottom - top
        self.origin = (left, top)
        self.game = AngryBirdsGame(self.width, self.height)
        self.bird_ids = select_bird_ids(desktop.items(), max(level.birds for level in LEVELS))
        self.bird_sources = []
        self.want_hidden = False
        self.hidden = False
        self.pending_level = None
        self.pending_restart = threading.Event()
        self.pointer = GamePointer()
        self.was_visible = win32gui.IsWindowVisible(self.listview)
        if not self.was_visible:
            raise RuntimeError('桌面图标当前已隐藏，请先在桌面右键菜单中显示图标。')
        self.classname = 'DesktopAngryBirdsOverlay'
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = self.classname
        wc.lpfnWndProc = win32gui.DefWindowProc
        try:
            win32gui.RegisterClass(wc)
        except win32gui.error as exc:
            if exc.winerror != 1410:
                raise
        self.bg_hwnd = None
        self.hud_hwnd = None
        self.banner_hwnd = None
        self.bird_hwnd = None
        self.band_hwnd = None
        self.aim_hwnd = None
        self.queue_hwnd = None
        self.object_windows = {}
        self.surfaces = {}
        self.background_frame = None
        self.hud_key = None
        self.banner_key = None
        self.queue_key = None
        self.last_monitor_check = 0.0
        self.bird_rest_frame = None
        self.frame_cache = {}
        self.queue_frame = None
        self.bg_key = None
        self.font = art.font(max(13, round(15 * primary[3] / 96)))

    # -- window plumbing ---------------------------------------------------
    def _layer(self):
        hwnd = win32gui.CreateWindowEx(
            WS_EX_LAYERED | 0x20 | WS_EX_NOACTIVATE, self.classname, '', win32con.WS_CHILD,
            0, 0, 1, 1, self.parent, 0, win32api.GetModuleHandle(None), None)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
        return hwnd

    def present(self, hwnd, frame, x, y):
        x, y = int(round(x + self.origin[0])), int(round(y + self.origin[1]))
        left, top, right, bottom = self.primary_bounds
        x0, y0 = max(left, x), max(top, y)
        x1, y1 = min(right, x + frame.width), min(bottom, y + frame.height)
        if x0 >= x1 or y0 >= y1:
            frame, x, y = Image.new('RGBA', (1, 1)), left, top
        elif (x0, y0, x1, y1) != (x, y, x + frame.width, y + frame.height):
            frame = frame.crop((x0 - x, y0 - y, x1 - x, y1 - y))
            x, y = x0, y0
        surface = self.surfaces.get(hwnd)
        if surface is not None and surface.size != frame.size:
            surface.close()
            surface = None
        if surface is None:
            surface = LayerSurface(hwnd, frame.size, x, y)
            self.surfaces[hwnd] = surface
        surface.present(frame, x, y)

    def _stack(self):
        # Child z-order: later windows sit above earlier ones.
        for hwnd in (self.bg_hwnd, *self.object_windows.values(), self.queue_hwnd,
                     self.band_hwnd, self.aim_hwnd, self.bird_hwnd, self.hud_hwnd,
                     self.banner_hwnd):
            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    def _create_scene_windows(self):
        self.bg_hwnd = self._layer()
        self.queue_hwnd = self._layer()
        self.band_hwnd = self._layer()
        self.aim_hwnd = self._layer()
        self.bird_hwnd = self._layer()
        self.hud_hwnd = self._layer()
        self.banner_hwnd = self._layer()
        self._sync_object_windows()
        self._stack()

    def _sync_object_windows(self):
        alive = {obj.uid: obj for obj in self.game.objects}
        for uid in list(self.object_windows):
            if uid not in alive:
                win32gui.DestroyWindow(self.object_windows.pop(uid))
        for uid in alive:
            if uid not in self.object_windows:
                self.object_windows[uid] = self._layer()
        self._stack()

    # -- lifecycle ---------------------------------------------------------
    def prepare(self):
        wallpaper = None
        comtypes.CoInitialize()
        try:
            for identity in self.bird_ids:
                try:
                    source = icon_artwork(identity, 128)
                    bounds = source.getchannel('A').getbbox()
                    self.bird_sources.append(source.crop(bounds) if bounds else source)
                except Exception as exc:
                    diag.log(f'bird artwork failed: {identity!r}: {exc!r}')
                    self.bird_sources.append(art.bird_sprite(self.game.bird_radius))
            try:
                wallpaper = primary_wallpaper(self.primary[1], self.desktop.get_geometry())
                if wallpaper is not None:
                    screen, work = self.primary[1], self.primary[2]
                    wallpaper = wallpaper.crop((work[0] - screen[0], work[1] - screen[1],
                                                work[2] - screen[0], work[3] - screen[1]))
            except Exception as exc:
                diag.log(f'wallpaper read failed: {exc!r}')
        finally:
            comtypes.CoUninitialize()
        self.background_frame = art.background(
            self.width, self.height, self.game.ground_y, self.game.sling_x,
            self.game.fork_y, self.game.scale, wallpaper=wallpaper)

    def show(self, snapshot, journal):
        try:
            self._create_scene_windows()
            self.draw(0.0, 0.016)
            snapshot['hidden_listview'] = self.listview
            atomic_json(journal, snapshot)
            win32gui.ShowWindow(self.listview, win32con.SW_HIDE)
            for hwnd in [self.bg_hwnd, self.queue_hwnd, self.band_hwnd, self.aim_hwnd,
                         self.bird_hwnd, self.hud_hwnd, self.banner_hwnd,
                         *self.object_windows.values()]:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            self._stack()
            diag.log(f'angry birds overlay shown: {self.width}x{self.height}, '
                     f'objects={len(self.object_windows)}')
        except Exception:
            self.close()
            raise

    def close(self):
        if self.was_visible and win32gui.IsWindow(self.listview):
            win32gui.ShowWindow(self.listview, win32con.SW_SHOWNA)
        for surface in self.surfaces.values():
            surface.close()
        self.surfaces.clear()
        for hwnd in [self.bg_hwnd, self.queue_hwnd, self.band_hwnd, self.aim_hwnd,
                     self.bird_hwnd, self.hud_hwnd, self.banner_hwnd,
                     *self.object_windows.values()]:
            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.DestroyWindow(hwnd)
        self.object_windows.clear()
        self.bg_hwnd = self.queue_hwnd = self.band_hwnd = self.aim_hwnd = self.bird_hwnd = None
        self.hud_hwnd = self.banner_hwnd = None
        self.frame_cache.clear()

    def request_level(self, index):
        self.pending_level = int(index)

    def request_restart(self):
        self.pending_restart.set()

    def request_next_level(self):
        if self.game.level_index + 1 < len(LEVELS):
            self.pending_level = self.game.level_index + 1

    def set_hidden(self, hidden, now):
        shown = win32con.SW_HIDE if hidden else win32con.SW_SHOWNOACTIVATE
        if hidden:
            for hwnd in [self.bg_hwnd, self.queue_hwnd, self.band_hwnd, self.aim_hwnd,
                         self.bird_hwnd, self.hud_hwnd, self.banner_hwnd,
                         *self.object_windows.values()]:
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            win32gui.ShowWindow(self.listview, win32con.SW_SHOWNA)
        else:
            win32gui.ShowWindow(self.listview, win32con.SW_HIDE)
            for hwnd in [self.bg_hwnd, self.queue_hwnd, self.band_hwnd, self.aim_hwnd,
                         self.bird_hwnd, self.hud_hwnd, self.banner_hwnd,
                         *self.object_windows.values()]:
                if hwnd:
                    win32gui.ShowWindow(hwnd, shown)
            self._stack()
        self.hidden = hidden
        diag.log('game hidden' if hidden else 'game shown again')

    # -- per-frame ---------------------------------------------------------
    def draw(self, now, dt):
        if self.desktop.get_geometry() != self.geometry:
            raise RuntimeError('显示器布局变化，已停止游戏并恢复桌面')
        if now - self.last_monitor_check >= 0.5:
            self.last_monitor_check = now
            if monitors() != self.monitor_state:
                raise RuntimeError('屏幕布局或 DPI 缩放变化，已恢复桌面，请重新开始')
        if self.want_hidden != self.hidden:
            self.set_hidden(self.want_hidden, now)
        if self.hidden:
            return
        if self.pending_level is not None:
            self.game.load_level(self.pending_level)
            self.pending_level = None
            self._drop_frames()
            self._sync_object_windows()
            self.banner_key = None
            self.hud_key = None
        if self.pending_restart.is_set():
            self.pending_restart.clear()
            self.game.load_level(self.game.level_index)
            self._drop_frames()
            self._sync_object_windows()
            self.banner_key = None
            self.hud_key = None
        if self.bg_key is None:
            self.draw_background()
        self.update_pointer(now)
        self.game.step(dt)
        self.draw_objects()
        self.draw_queue()
        self.draw_bird(now)
        self.draw_bands()
        self.draw_aim()
        self.draw_hud()
        self.draw_banner()

    def _drop_frames(self):
        for surface in self.surfaces.values():
            surface.close()
        self.surfaces.clear()
        self.frame_cache.clear()
        self.bg_key = None
        self.queue_key = None

    def draw_background(self):
        if self.background_frame is None:
            return
        win32gui.ShowWindow(self.bg_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.bg_hwnd, self.background_frame, 0, 0)
        self.bg_key = True

    def update_pointer(self, now):
        screen = win32gui.GetCursorPos()
        x, y = win32gui.ScreenToClient(self.parent, screen)
        lx, ly = x - self.origin[0], y - self.origin[1]
        on_desktop = False
        if 0 <= lx <= self.width and 0 <= ly <= self.height:
            hwnd = win32gui.WindowFromPoint(screen)
            top = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) if hwnd else 0
            if top:
                name = win32gui.GetClassName(top)
                on_desktop = name in ('Progman', 'WorkerW')
                if not on_desktop:
                    pid = win32process.GetWindowThreadProcessId(top)[1]
                    # Our own layered children can be the direct hit; their root is WorkerW.  A Tk
                    # toolbar (our pid, TkTopLevel) must not start a drag.
                    if pid == os.getpid() and name not in ('Progman', 'WorkerW'):
                        on_desktop = False
        button = win32con.VK_RBUTTON if win32api.GetSystemMetrics(SM_SWAPBUTTON) else win32con.VK_LBUTTON
        down = bool(win32api.GetAsyncKeyState(button) & 0x8000)
        self.pointer.update(self.game, lx, ly, down, on_desktop)

    # -- drawing -----------------------------------------------------------
    def _frame_for_object(self, obj, now):
        if obj.dead:
            if not obj.effect:
                return None, None
            if obj.effect_t > 0.75:
                return None, None
            if obj.effect == 'break':
                frame = art.effect_frame('break', obj.effect_t, obj.w, obj.h)
            elif obj.effect == 'pop':
                frame = art.effect_frame('pop', obj.effect_t, obj.w, obj.h)
            else:
                frame = art.effect_frame('boom', obj.effect_t, obj.w, obj.h)
            return frame, obj.last_pose
        if obj.kind == 'pig':
            base = art.pig_sprite(obj.radius)
            canvas = int(base.width * 1.12)
            key = ('pig', int(obj.radius), round(math.degrees(obj.angle) / 4) * 4)
            if key not in self.frame_cache:
                self.frame_cache[key] = self._rotated(base, math.degrees(obj.angle), canvas)
            return self.frame_cache[key], (obj.body.position.x, obj.body.position.y, 0.0)
        if obj.kind == 'tnt':
            size = int(max(obj.w, obj.h))
            key = ('tnt', size)
            if key not in self.frame_cache:
                self.frame_cache[key] = art.tnt_sprite(size)
            return self.frame_cache[key], (obj.body.position.x, obj.body.position.y, 0.0)
        base = art.block_sprite(obj.kind, obj.w, obj.h)
        canvas = int(math.hypot(obj.w, obj.h)) + 4
        key = ('block', obj.kind, int(obj.w), int(obj.h), round(math.degrees(obj.angle) / 3) * 3)
        if key not in self.frame_cache:
            self.frame_cache[key] = self._rotated(base, math.degrees(obj.angle), canvas)
        return self.frame_cache[key], (obj.body.position.x, obj.body.position.y, 0.0)

    @staticmethod
    def _rotated(base, degrees, canvas):
        image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
        rotated = base.rotate(-degrees, resample=Image.BICUBIC, expand=True)
        image.alpha_composite(rotated, ((canvas - rotated.width) // 2, (canvas - rotated.height) // 2))
        return image

    def draw_objects(self):
        for obj in self.game.objects:
            hwnd = self.object_windows.get(obj.uid)
            if hwnd is None:
                continue
            frame, pose = self._frame_for_object(obj, 0.0)
            if frame is None:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                continue
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            x, y = pose[0] - frame.width / 2, pose[1] - frame.height / 2
            self.present(hwnd, frame, x, y)

    def draw_bands(self):
        game = self.game
        if game.state not in ('ready', 'flying', 'between'):
            win32gui.ShowWindow(self.band_hwnd, win32con.SW_HIDE)
            return
        # Bands only exist while the bird sits in the fork; once fired they snap back.
        if game.state != 'ready':
            win32gui.ShowWindow(self.band_hwnd, win32con.SW_HIDE)
            return
        s = game.scale
        left_tip = (game.sling_x - 46 * s, game.fork_y)
        right_tip = (game.sling_x + 46 * s, game.fork_y)
        bird = game.drag_point if game.dragging and game.drag_point else game.anchor
        x0 = min(left_tip[0], right_tip[0], bird[0], game.anchor[0]) - 80 * s
        y0 = min(left_tip[1], bird[1], game.anchor[1]) - 60 * s
        x1 = max(left_tip[0], right_tip[0], bird[0], game.anchor[0]) + 80 * s
        y1 = max(left_tip[1], bird[1], game.anchor[1]) + 80 * s
        width, height = int(x1 - x0), int(y1 - y0)
        frame = art.band_layer((width, height),
                               (left_tip[0] - x0, left_tip[1] - y0),
                               (right_tip[0] - x0, right_tip[1] - y0),
                               (game.anchor[0] - x0, game.anchor[1] - y0),
                               (bird[0] - x0, bird[1] - y0))
        win32gui.ShowWindow(self.band_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.band_hwnd, frame, x0, y0)

    def draw_aim(self):
        game = self.game
        if not game.dragging or not game.drag_point:
            win32gui.ShowWindow(self.aim_hwnd, win32con.SW_HIDE)
            return
        vx, vy = game.aim_velocity()
        if abs(vx) + abs(vy) < 10:
            win32gui.ShowWindow(self.aim_hwnd, win32con.SW_HIDE)
            return
        x, y = game.drag_point
        points = []
        for i in range(60):
            t = i * 0.035
            px = x + vx * t
            py = y + vy * t + 0.5 * 1400 * game.scale * t * t
            if py > game.ground_y:
                break
            points.append((px, py))
        if not points:
            win32gui.ShowWindow(self.aim_hwnd, win32con.SW_HIDE)
            return
        frame, origin = art.aim_dots(points)
        win32gui.ShowWindow(self.aim_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.aim_hwnd, frame, origin[0], origin[1])

    def draw_hud(self):
        game = self.game
        stars = game.score_stars()
        key = (game.level_index, game.score, game.pigs_left(), game.birds_left, stars,
               game.state)
        if key == self.hud_key:
            win32gui.ShowWindow(self.hud_hwnd, win32con.SW_SHOWNOACTIVATE)
            return
        self.hud_key = key
        width, height = int(520 * game.scale), int(108 * game.scale)
        frame = art.hud_card(width, height, f'第 {game.level_index + 1} 关 · {game.level.name}',
                             game.score, game.pigs_left(), game.birds_left, stars)
        win32gui.ShowWindow(self.hud_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.hud_hwnd, frame, 18 * game.scale, 16 * game.scale)

    def draw_banner(self):
        game = self.game
        if game.state not in ('won', 'lost'):
            win32gui.ShowWindow(self.banner_hwnd, win32con.SW_HIDE)
            self.banner_key = None
            return
        won = game.state == 'won'
        stars = game.score_stars()
        key = (won, stars, game.level_index)
        if key == self.banner_key:
            win32gui.ShowWindow(self.banner_hwnd, win32con.SW_SHOWNOACTIVATE)
            return
        self.banner_key = key
        width, height = int(780 * game.scale), int(270 * game.scale)
        title = '过关！' if won else '小鸟用完了'
        subtitle = '点击工具栏的“下一关”继续' if won else '点击工具栏的“重玩”再试一次'
        if won and game.level_index + 1 >= len(LEVELS):
            subtitle = '全部关卡完成！点击“重玩”挑战更高分'
        frame = art.banner_frame(width, height, title, subtitle, won, stars)
        x = (self.width - width) / 2
        y = self.height * 0.21
        win32gui.ShowWindow(self.banner_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.banner_hwnd, frame, x, y)

    # -- bird drawing ------------------------------------------------------
    def draw_queue(self):
        """Show the next few real desktop icons waiting behind the slingshot."""
        game = self.game
        count = min(3, max(0, game.level.birds - game.current_bird - 1))
        if game.state not in ('ready', 'flying', 'between') or count <= 0 or not self.bird_sources:
            win32gui.ShowWindow(self.queue_hwnd, win32con.SW_HIDE)
            self.queue_key = None
            return
        s = game.scale
        size = int(54 * s)
        gap = int(70 * s)
        total = count * size + (count - 1) * (gap - size)
        x0 = max(20 * s, game.sling_x - 70 * s - total)
        y0 = game.ground_y - size - 10 * s
        key = (game.level_index, game.current_bird, count, size, round(x0), round(y0))
        if key != self.queue_key:
            self.queue_key = key
            frame = Image.new('RGBA', (int(total + 20 * s), int(size + 20 * s)), (0, 0, 0, 0))
            draw = ImageDraw.Draw(frame)
            for i in range(count):
                index = (game.current_bird + 1 + i) % len(self.bird_sources)
                base = self.bird_sources[index]
                ratio = size / max(base.size)
                thumb = base.resize((max(1, round(base.width * ratio)),
                                     max(1, round(base.height * ratio))), Image.Resampling.LANCZOS)
                x = 10 * s + i * gap + (size - thumb.width) / 2
                y = 10 * s + (size - thumb.height) / 2
                draw.ellipse((x + size * 0.10, y + size - 3 * s, x + size * 0.90, y + size + 5 * s),
                             fill=(0, 0, 0, 65))
                frame.alpha_composite(thumb, (int(x), int(y)))
            self.queue_frame = frame
        win32gui.ShowWindow(self.queue_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.queue_hwnd, self.queue_frame, x0 - 10 * s, y0 - 10 * s)

    def draw_bird(self, now):
        game = self.game
        if game.state == 'ready' and not game.dragging:
            pose = game.anchor
        elif game.state == 'ready' and game.dragging:
            pose = game.drag_point
        elif game.state == 'flying' and game.bird_body is not None:
            pose = (game.bird_body.position.x, game.bird_body.position.y)
        else:
            pose = None
        if pose is None:
            win32gui.ShowWindow(self.bird_hwnd, win32con.SW_HIDE)
            return
        index = game.current_bird % max(1, len(self.bird_sources))
        base = self.bird_sources[index] if self.bird_sources else art.bird_sprite(game.bird_radius)
        diameter = max(1, int(game.bird_radius * 2.4))
        if max(base.size) != diameter:
            ratio = diameter / max(base.size)
            base = base.resize((max(1, round(base.width * ratio)),
                                max(1, round(base.height * ratio))), Image.Resampling.LANCZOS)
        angle = math.degrees(game.bird_body.angle) if game.bird_body is not None and game.state == 'flying' else 0.0
        key = ('bird', index, round(angle / 5) * 5)
        if key not in self.frame_cache:
            self.frame_cache[key] = self._rotated(base, angle, int(max(base.size) * 1.12))
        frame = self.frame_cache[key]
        win32gui.ShowWindow(self.bird_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.present(self.bird_hwnd, frame, pose[0] - frame.width / 2, pose[1] - frame.height / 2)

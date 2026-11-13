"""Tk toolbar and lifecycle for the desktop Angry Birds game."""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
import traceback
import tkinter as tk
from tkinter import messagebox

import win32api
import win32con
import win32gui

from . import config, diag
from .game import LEVELS
from .hotkeys import Hotkeys
from .overlay import GameOverlay
from .paths import runtime_directory
from .runner import GameRunner
from .shell import LayoutSession, ShellDesktop

BG = '#0d1c17'
CARD = '#152a22'
TEXT = '#edf8f1'
MUTED = '#93b7a8'
ACCENT = '#69ddb3'
GOLD = '#f2ca87'

ERROR_ALREADY_EXISTS = 183


def claim_instance_mutex():
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.CreateMutexW(None, False, config.MUTEX)
    if not handle:
        raise ctypes.WinError()
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


class DesktopAngryBirdsApp:
    def __init__(self, root, instance_handle):
        self.root = root
        self.instance_handle = instance_handle
        self.runner = None
        self.session = None
        self.watchdog = None
        self.overlay = None
        self.hotkeys = None
        self.closing = False
        self.deadline = 0.0
        self.journal = runtime_directory() / 'layout.json'
        self.hidden = False
        root.title(config.WINDOW_TITLE)
        root.resizable(False, False)
        root.configure(bg=BG)
        root.attributes('-topmost', True)
        try:
            root.wm_attributes('-toolwindow', True)
        except tk.TclError:
            pass
        if config.ICON_PATH.exists():
            try:
                root.iconbitmap(default=str(config.ICON_PATH))
            except tk.TclError:
                pass
        self._build_toolbar()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Escape>', lambda event: self.close())
        root.after(30, self.start)

    def _button(self, parent, text, command, width=8):
        return tk.Button(parent, text=text, command=command, width=width,
                         font=('Microsoft YaHei UI', 9), relief='flat', bd=0,
                         bg=CARD, fg=TEXT, activebackground='#285542', activeforeground='white',
                         padx=6, pady=5, cursor='hand2')

    def _build_toolbar(self):
        outer = tk.Frame(self.root, bg=BG, padx=10, pady=7)
        outer.pack(fill='both', expand=True)
        top = tk.Frame(outer, bg=BG)
        top.pack(fill='x')
        tk.Label(top, text='桌面图标版愤怒的小鸟', bg=BG, fg=TEXT,
                 font=('Microsoft YaHei UI', 13, 'bold')).pack(side='left', padx=(2, 12))
        self.status = tk.Label(top, text='准备中…', bg=BG, fg=MUTED,
                               font=('Microsoft YaHei UI', 9))
        self.status.pack(side='left', padx=(0, 12))
        self.hint = tk.Label(top, text='按住小鸟向后拉，松手发射', bg=BG, fg=GOLD,
                             font=('Microsoft YaHei UI', 9))
        self.hint.pack(side='right', padx=8)
        buttons = tk.Frame(outer, bg=BG)
        buttons.pack(fill='x', pady=(6, 0))
        self.level_buttons = []
        for index in range(len(LEVELS)):
            button = self._button(buttons, f'{index + 1}', lambda i=index: self.select_level(i), 2)
            button.pack(side='left', padx=2)
            self.level_buttons.append(button)
        tk.Frame(buttons, bg=BG, width=12).pack(side='left')
        self._button(buttons, '重玩', self.restart, 6).pack(side='left', padx=2)
        self._button(buttons, '下一关', self.next_level, 6).pack(side='left', padx=2)
        self.hide_button = self._button(buttons, '隐藏', self.toggle_hidden, 5)
        self.hide_button.pack(side='left', padx=2)
        self._button(buttons, '退出', self.close, 5).pack(side='left', padx=2)

    def _place_toolbar(self):
        self.root.update_idletasks()
        width = max(1250, self.root.winfo_reqwidth())
        height = self.root.winfo_reqheight()
        monitor = win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
        work = win32api.GetMonitorInfo(monitor)['Work']
        x = max(work[0], work[0] + (work[2] - work[0] - width) // 2)
        y = work[1] + 16
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def start(self):
        self._place_toolbar()
        diag.start_session(config.VERSION)
        try:
            self.hotkeys = Hotkeys()
            desktop = ShellDesktop()
            self.session = LayoutSession(desktop, self.journal)
            self.session.restore()
            self.session = LayoutSession(desktop, self.journal)
            self.session.begin(overlay_only=True)
            self.overlay = GameOverlay(desktop)
            self.watchdog = self.spawn_watchdog()
            self.runner = GameRunner(self.overlay)
            self.runner.start()
            self.deadline = time.monotonic() + 30
        except Exception as exc:
            self.fail(exc)
            return
        self.root.after(80, self.poll)

    def spawn_watchdog(self):
        frozen = bool(getattr(sys, 'frozen', False))
        command = [sys.executable]
        if not frozen:
            command.append(str(config.BASE / 'app.pyw'))
        command.extend(['--watchdog', str(self.journal), self.session.snapshot['session_id'], str(os.getpid())])
        environment = {**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'}
        return subprocess.Popen(command, env=environment,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=0x08000000,
                                cwd=str(runtime_directory()))

    def poll(self):
        if self.closing:
            return
        try:
            if self.runner is None:
                return
            if self.runner.error is not None:
                raise self.runner.error
            if not self.runner.shown.is_set():
                if time.monotonic() > self.deadline:
                    raise RuntimeError('等待桌面恢复守护就绪超时。')
                ready = self.journal.with_name(self.journal.stem + '.watchdog.json')
                if ready.exists():
                    data = json.loads(ready.read_text(encoding='utf-8'))
                    if (data.get('session_id') == self.session.snapshot['session_id']
                            and self.runner.prepared.is_set()):
                        if not data.get('ready'):
                            raise RuntimeError('无法启动桌面恢复守护。')
                        self.runner.request_show(self.session.snapshot, self.journal)
            else:
                self.update_status()
            if self.hotkeys is not None:
                while not self.hotkeys.pending.empty():
                    self.hotkeys.pending.get()
                    self.close()
                    return
        except Exception as exc:
            self.fail(exc)
            return
        self.root.after(100, self.poll)

    def update_status(self):
        if self.overlay is None:
            return
        if self.hidden:
            self.status.configure(text='已显示真实桌面，游戏已暂停')
            return
        game = self.overlay.game
        names = {'ready': '瞄准中', 'flying': '小鸟飞行中', 'between': '准备下一只',
                 'won': '过关', 'lost': '未过关'}
        self.status.configure(
            text=f'第 {game.level_index + 1} 关 · {names.get(game.state, game.state)}  '
                 f'得分 {game.score:,}  |  小猪 {game.pigs_left()}  |  小鸟 {game.birds_left}')
        for index, button in enumerate(self.level_buttons):
            button.configure(bg='#285542' if index == game.level_index else CARD,
                             fg=ACCENT if index == game.level_index else TEXT)

    def select_level(self, index):
        if self.overlay is None:
            return
        if self.hidden:
            self.toggle_hidden()
        self.overlay.request_level(index)

    def restart(self):
        if self.overlay is not None:
            self.overlay.request_restart()

    def next_level(self):
        if self.overlay is not None:
            self.overlay.request_next_level()

    def toggle_hidden(self):
        if self.overlay is None:
            return
        self.hidden = not self.hidden
        self.overlay.want_hidden = self.hidden
        self.hide_button.configure(text='显示' if self.hidden else '隐藏')
        self.update_status()

    def fail(self, exc):
        diag.log(f'fatal: {exc!r}', traceback.format_exc())
        self.close()
        try:
            messagebox.showerror('Desktop version of Angry Birds',
                                 f'游戏无法启动或已停止：\n{exc}\n\n桌面图标已恢复。')
        except Exception:
            pass

    def close(self):
        if self.closing:
            return
        self.closing = True
        try:
            if self.runner is not None:
                self.runner.stop()
        except Exception as exc:
            diag.log(f'runner stop: {exc!r}')
        try:
            if self.session is not None:
                self.session.restore()
        except Exception as exc:
            diag.log(f'session restore: {exc!r}')
        try:
            if self.watchdog is not None:
                self.watchdog.terminate()
                self.watchdog.wait(timeout=2)
        except Exception:
            pass
        try:
            if self.hotkeys is not None:
                self.hotkeys.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass
    handle = claim_instance_mutex()
    if handle is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo('Desktop version of Angry Birds', '游戏已经在运行了。')
        root.destroy()
        return
    root = tk.Tk()
    DesktopAngryBirdsApp(root, handle)
    root.mainloop()

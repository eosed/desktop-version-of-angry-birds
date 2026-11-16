"""Application constants."""
from __future__ import annotations

from pathlib import Path

VERSION = '1.7.0'
PRODUCT_NAME = '桌面版愤怒的小鸟'
WINDOW_TITLE = 'Desktop version of Angry Birds'
BASE = Path(__file__).resolve().parent.parent
ICON_PATH = BASE / 'assets' / 'angry-birds.ico'
MUTEX = 'Local\\DesktopAngryBirds'
HOTKEY_ID = 0x5A44
HOTKEY_MODIFIERS = 0x0002 | 0x0001  # MOD_CONTROL | MOD_ALT
HOTKEY_VK = 0x58  # X

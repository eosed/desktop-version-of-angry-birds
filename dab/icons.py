"""Read real desktop icon artwork through the Shell.

The birds in this game are the user's own desktop icons.  Keeping the extraction
isolated here means the renderer only ever sees RGBA images and never has to know
about COM.
"""
from __future__ import annotations

import ctypes
import os
import struct
from ctypes import wintypes as W

import comtypes
import win32gui
from PIL import Image

from .shell import ShellDesktop

SHORTCUT_SUFFIXES = ('.lnk', '.url', '.exe', '.appref-ms', '.msi')


class ImageFactory(comtypes.IUnknown):
    _iid_ = comtypes.GUID('{bcc18b79-ba16-442f-80c4-8a59c30c463b}')
    _methods_ = []


def _unpremultiply(image):
    """Shell bitmaps use premultiplied BGRA; Pillow needs straight alpha."""
    data = bytearray(image.tobytes())
    for index in range(3, len(data), 4):
        alpha = data[index]
        if 0 < alpha < 255:
            scale = 255 / alpha
            data[index - 3] = min(255, round(data[index - 3] * scale))
            data[index - 2] = min(255, round(data[index - 2] * scale))
            data[index - 1] = min(255, round(data[index - 1] * scale))
    return Image.frombytes('RGBA', image.size, bytes(data))


def _bitmap_image(bitmap):
    """Copy an unselected Shell bitmap into a top-down, 32-bit BGRA buffer."""
    get_bits = ctypes.WinDLL('gdi32', use_last_error=True).GetDIBits
    get_bits.argtypes = [W.HDC, W.HBITMAP, W.UINT, W.UINT, ctypes.c_void_p, ctypes.c_void_p, W.UINT]
    get_bits.restype = ctypes.c_int
    header_format = '<IiiHHIIiiII'
    header = ctypes.create_string_buffer(struct.calcsize(header_format))
    struct.pack_into('<I', header, 0, ctypes.sizeof(header))
    dc = win32gui.CreateCompatibleDC(0)
    try:
        if not get_bits(dc, bitmap, 0, 0, None, header, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        _, width, height, *_ = struct.unpack(header_format, header)
        height = abs(height)
        if width <= 0 or height <= 0:
            raise ValueError('Invalid Shell bitmap dimensions')
        pixels = ctypes.create_string_buffer(width * height * 4)
        struct.pack_into(header_format, header, 0, ctypes.sizeof(header),
                         width, -height, 1, 32, 0, ctypes.sizeof(pixels), 0, 0, 0, 0)
        if get_bits(dc, bitmap, 0, height, pixels, header, 0) != height:
            raise ctypes.WinError(ctypes.get_last_error())
        return Image.frombytes('RGBA', (width, height), pixels.raw, 'raw', 'BGRA')
    finally:
        win32gui.DeleteDC(dc)


def artwork(identity, size):
    """Extract the Shell thumbnail for one desktop item as straight-alpha RGBA."""
    factory = ctypes.POINTER(ImageFactory)()
    create = ctypes.windll.shell32.SHCreateItemFromParsingName
    create.argtypes = [W.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(comtypes.GUID),
                       ctypes.POINTER(ctypes.POINTER(ImageFactory))]
    hr = create(identity, None, ctypes.byref(ImageFactory._iid_), ctypes.byref(factory))
    if hr < 0:
        raise OSError(f'Cannot load Shell artwork: {hr & 0xffffffff:08x}')
    bitmap = W.HBITMAP()
    ShellDesktop._invoke(factory, 3, [W.SIZE, W.UINT, ctypes.POINTER(W.HBITMAP)],
                         W.SIZE(size, size), 0, ctypes.byref(bitmap))
    try:
        return _unpremultiply(_bitmap_image(bitmap.value))
    finally:
        if bitmap.value:
            win32gui.DeleteObject(bitmap.value)


def item_tier(identity, is_dir=os.path.isdir):
    """0 = shortcut / program, 1 = other file, 2 = folder, 3 = shell namespace icon."""
    text = identity.lower()
    drive = len(text) > 2 and text[0].isalpha() and text[1] == ':' and text[2] in '\\/'
    is_path = drive or text.startswith('\\\\')
    if not is_path:
        return 3
    if text.endswith(SHORTCUT_SUFFIXES):
        return 0
    try:
        return 2 if is_dir(identity) else 1
    except OSError:
        return 1


def select_bird_ids(items, minimum):
    """Pick desktop icons to use as birds, repeating the best ones if needed."""
    if not items:
        return []
    ordered = sorted(range(len(items)), key=lambda index: (item_tier(items[index]['id']), index))
    ids = [items[index]['id'] for index in ordered]
    return [ids[index % len(ids)] for index in range(max(minimum, 1))]


def select_pig_ids(items, exclude, minimum):
    """Pick other desktop app icons for pigs, excluding the bird icons."""
    if not items:
        return []
    excluded = set(exclude)
    ordered = sorted(range(len(items)), key=lambda index: (item_tier(items[index]['id']), index))
    ids = [items[index]['id'] for index in ordered if items[index]['id'] not in excluded]
    apps = [identity for identity in ids if item_tier(identity) == 0]
    pool = apps or ids
    if not pool:
        return []
    return [pool[index % len(pool)] for index in range(max(minimum, 1))]

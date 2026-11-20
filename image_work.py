"""Bounded image work shared by the display and threaded web requests."""
from collections import OrderedDict
from contextlib import closing
import io
import math
import os
import threading

import pygame
from PIL import Image

from image_rotation import apply_pil

# One large decoder at a time on the 1 GB Pi. Reentrant for cached previews.
DECODE_LOCK = threading.RLock()


def image_to_surface(image):
    """pygame 2.1.2, which the frame runs, has fromstring and not frombytes."""
    data = image.tobytes()
    load = getattr(pygame.image, 'frombytes', None) or pygame.image.fromstring
    return load(data, image.size, image.mode)


def file_key(path):
    stat = os.stat(path)
    return (os.path.abspath(path), stat.st_mtime_ns, stat.st_size, stat.st_ino)


def shrink_image(image, bounds):
    """Ask JPEG's decoder for a reduced image before allocating its pixels.

    Fit the draft target to the photo's aspect first; a tall bounding box
    around a landscape photo otherwise defeats decoder downsampling.
    Other formats safely ignore draft and still shrink before rotation.
    """
    factor = min(1.0, bounds[0] / image.width, bounds[1] / image.height)
    target = (max(1, math.ceil(image.width * factor)), max(1, math.ceil(image.height * factor)))
    image.draft(None, target)
    image.thumbnail(bounds, Image.Resampling.LANCZOS)


class PreviewCache:
    def __init__(self, max_bytes=4 * 1024 * 1024, max_entries=128):
        self.max_bytes, self.max_entries = max_bytes, max_entries
        self.entries = OrderedDict()
        self.bytes = 0
        self.lock = threading.Lock()

    def clear(self):
        with self.lock:
            self.entries.clear()
            self.bytes = 0

    def get(self, path, rotation, factory):
        key = (file_key(path), rotation)
        with self.lock:
            if key in self.entries:
                self.entries.move_to_end(key)
                return io.BytesIO(self.entries[key])
        with DECODE_LOCK:
            with self.lock:
                if key in self.entries:
                    self.entries.move_to_end(key)
                    return io.BytesIO(self.entries[key])
            output = factory()
            try:
                data = output.getvalue()
                with self.lock:
                    if len(data) <= self.max_bytes and self.max_entries > 0:
                        while self.entries and (self.bytes + len(data) > self.max_bytes or len(self.entries) >= self.max_entries):
                            _, old = self.entries.popitem(last=False)
                            self.bytes -= len(old)
                        self.entries[key] = data
                        self.bytes += len(data)
                return output
            except Exception:
                output.close()
                raise


class DisplayImageCache:
    """Keep only the current screen-sized surface, never original photos."""
    def __init__(self):
        self.key = self.value = None
        self.lock = threading.Lock()

    def get(self, path, rotation, screen_size, correction_h, correction_v, scaler):
        with self.lock:
            return self._get(path, rotation, screen_size, correction_h, correction_v, scaler)

    def _get(self, path, rotation, screen_size, correction_h, correction_v, scaler):
        key = (file_key(path), rotation, screen_size, correction_h, correction_v)
        if key == self.key:
            return self.value
        self.key = self.value = None
        target = (max(1, math.ceil(screen_size[0] / correction_h)),
                  max(1, math.ceil(screen_size[1] / correction_v)))
        bounds = target[::-1] if rotation in (90, 270) else target
        with DECODE_LOCK:
            with Image.open(path) as original:
                shrink_image(original, bounds)
                with closing(original.convert('RGBA' if 'A' in original.getbands() or 'transparency' in original.info else 'RGB')) as image:
                    turned = apply_pil(image, rotation)
                    try:
                        surface = image_to_surface(turned)
                    finally:
                        if turned is not image:
                            turned.close()
            value = scaler(surface, *screen_size, correction_h, correction_v)
        self.key, self.value = key, value
        return value

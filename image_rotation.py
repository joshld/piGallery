"""Per-image quarter turns, stored beside the config and applied at display time.

The original file is left unchanged. 90 means clockwise.
"""
import json
import os
from pathlib import Path
import tempfile


def store_path(config_path):
    return Path(config_path).parent / '.cache' / 'image-rotations.json'


def normalize_key(image_key):
    return str(image_key or '').replace('\\', '/').lstrip('/')


def _read(config_path):
    path = store_path(config_path)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {normalize_key(key): int(value) % 360
            for key, value in data.items()
            if normalize_key(key) and int(value) % 360 in (0, 90, 180, 270)}


def _write(config_path, rotations):
    path = store_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = {key: value for key, value in rotations.items() if value}
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(path.parent), delete=False) as output:
            name = output.name
            json.dump(kept, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def get_rotation(config_path, image_key):
    return _read(config_path).get(normalize_key(image_key), 0)


def turn(config_path, image_key, direction):
    key = normalize_key(image_key)
    if not key:
        raise ValueError('No image is loaded')
    if direction not in ('cw', 'ccw'):
        raise ValueError('Rotation must be clockwise or counter-clockwise')
    rotations = _read(config_path)
    delta = 90 if direction == 'cw' else -90
    rotations[key] = (rotations.get(key, 0) + delta) % 360
    _write(config_path, rotations)
    return rotations[key]


def apply_pil(image, degrees):
    degrees = int(degrees or 0) % 360
    if degrees == 0:
        return image
    # Pillow rotates counter-clockwise. expand keeps the whole picture.
    return image.rotate(-degrees, expand=True)

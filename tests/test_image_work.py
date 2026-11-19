import io
import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

from PIL import Image
import pytest

import image_rotation
from image_work import DECODE_LOCK, DisplayImageCache, PreviewCache
import web


@pytest.mark.parametrize('angle,size', [(0, (320, 180)), (90, (101, 180)), (180, (320, 180)), (270, (101, 180))])
def test_preview_rotates_only_thumbnail_pixels(tmp_path, monkeypatch, angle, size):
    path = tmp_path / 'large.jpg'
    with Image.new('RGB', (3200, 1800), 'red') as image:
        image.save(path)
    real = image_rotation.apply_pil
    seen = []

    def rotate(image, degrees):
        seen.append(image.size)
        assert image.width <= 320 and image.height <= 320
        return real(image, degrees)

    monkeypatch.setattr(image_rotation, 'apply_pil', rotate)
    with web.create_image_preview(path, angle) as data, Image.open(data) as result:
        assert result.size == size
    assert seen


def test_preview_cache_bounds_rotation_and_file_invalidation(tmp_path):
    path = tmp_path / 'photo'
    path.write_bytes(b'original')
    cache = PreviewCache(max_bytes=10, max_entries=2)
    factory = Mock(side_effect=lambda: io.BytesIO(b'123456'))
    with cache.get(path, 0, factory):
        pass
    with cache.get(path, 0, factory):
        pass
    assert factory.call_count == 1
    with cache.get(path, 90, factory):
        pass
    assert cache.bytes == 6 and len(cache.entries) == 1
    path.write_bytes(b'changed size')
    with cache.get(path, 90, factory):
        pass
    assert factory.call_count == 3
    with cache.get(path, 0, lambda: io.BytesIO(b'X' * 11)):
        pass
    assert cache.bytes <= 10


def test_concurrent_preview_misses_decode_once_and_warm_hits_do_not_wait(tmp_path):
    path = tmp_path / 'photo'
    path.write_bytes(b'photo')
    cache = PreviewCache()
    factory = Mock(side_effect=lambda: io.BytesIO(b'jpeg'))
    def fetch(_):
        with cache.get(path, 0, factory) as data:
            return data.read()
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(fetch, range(16))) == [b'jpeg'] * 16
    assert factory.call_count == 1
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DECODE_LOCK:
            assert pool.submit(fetch, 1).result(timeout=2) == b'jpeg'


def test_display_cache_keeps_one_reduced_surface_and_invalidates(tmp_path, monkeypatch):
    path = tmp_path / 'photo.png'
    with Image.new('RGBA', (1600, 900), (255, 0, 0, 128)) as image:
        image.save(path)
    cache = DisplayImageCache()
    scaler = Mock(side_effect=lambda surface, *args: (surface, 0, 0, surface.get_width()))
    first = cache.get(path, 90, (320, 180), 1, 1, scaler)
    assert first[0].get_width() <= 320 and first[0].get_height() <= 180
    assert cache.get(path, 90, (320, 180), 1, 1, scaler) is first
    assert scaler.call_count == 1
    assert first[0].get_at((0, 0)).a == 128
    assert cache.get(path, 0, (320, 180), 1, 1, scaler) is not first
    stamp = os.stat(path).st_mtime_ns
    os.utime(path, ns=(stamp + 10000000, stamp + 10000000))
    cache.get(path, 0, (320, 180), 1, 1, scaler)
    cache.get(path, 0, (640, 360), 1.2, 1, scaler)
    assert scaler.call_count == 4


def test_preview_and_full_rotation_share_decoder_limit(tmp_path, monkeypatch):
    path = tmp_path / 'photo.jpg'
    with Image.new('RGB', (1200, 800), 'blue') as image:
        image.save(path)
    active = peak = 0
    real = image_rotation.apply_pil
    def rotate(image, degrees):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            time.sleep(0.01)
            return real(image, degrees)
        finally:
            active -= 1
    monkeypatch.setattr(image_rotation, 'apply_pil', rotate)
    def work(index):
        if index % 2:
            data, _ = web.rotated_image_response(path, 90)
        else:
            data = web.create_image_preview(path, 90)
        data.close()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(work, range(8)))
    assert peak == 1

import ast
import datetime
import io
import logging
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask
from PIL import Image, PngImagePlugin
import pytest

import web


@pytest.fixture
def client(tmp_path):
    app = Flask(__name__)
    app.testing = True
    slideshow = SimpleNamespace(
        current_img='photo.png', folder=str(tmp_path), config={},
        _cached_caption_image=None, _cached_caption=None, force_redraw=False,
        image_display_start_time=0, paused=False, pause_start_time=None,
        display_time_seconds=10, current_index=0, total_images=1,
        current_temp='', current_weather='', manual_display_override=None,
        is_display_on=lambda: True)
    web.init_web(app, slideshow, None, str(tmp_path / 'config.ini'),
                 str(tmp_path / 'gallery.log'), logging.getLogger('test'))
    with app.test_client() as connection:
        yield connection, slideshow


def make_image(path, mode='RGB', caption=None):
    kwargs = {}
    if caption is not None:
        info = PngImagePlugin.PngInfo()
        info.add_text('Comment', caption)
        kwargs['pnginfo'] = info
    with Image.new(mode, (640, 360)) as img:
        img.save(path, **kwargs)


def test_uploaded_badge_count_skips_metadata(client, tmp_path, monkeypatch):
    connection, _ = client
    directory = tmp_path / 'uploaded'
    directory.mkdir()
    make_image(directory / 'one.jpg')
    make_image(directory / '.hidden.jpg')
    (directory / 'folder.png').mkdir()
    monkeypatch.setattr(web, 'get_image_caption', Mock(side_effect=AssertionError('count must not read metadata')))
    response = connection.get('/api/uploaded-images?count_only=true')
    assert response.json == {'total': 1}


@pytest.fixture
def opened_images(monkeypatch):
    """Keep readers alive so garbage collection cannot hide missing closes."""
    images = []
    original = Image.open

    def track(*args, **kwargs):
        image = original(*args, **kwargs)
        images.append(image)
        return image

    monkeypatch.setattr(Image, 'open', track)
    return images


def assert_images_closed(images):
    assert images
    for image in images:
        assert image.fp is None
        with pytest.raises(ValueError):
            image.getpixel((0, 0))


@pytest.mark.parametrize('caption', ['Example caption', None])
def test_caption_reader_closes_early_return_and_no_caption(tmp_path, opened_images, caption):
    path = tmp_path / 'photo.png'
    make_image(path, caption=caption)
    assert web.get_image_caption(str(path)) == caption
    assert_images_closed(opened_images)


def test_repeated_caption_reads_release_each_image(tmp_path, opened_images):
    path = tmp_path / 'photo.png'
    make_image(path, caption='Repeated')
    for _ in range(100):
        assert web.get_image_caption(str(path)) == 'Repeated'
    assert len(opened_images) == 100
    assert_images_closed(opened_images)


def test_caption_reader_closes_when_metadata_fails(tmp_path, opened_images, monkeypatch):
    path = tmp_path / 'photo.jpg'
    make_image(path)
    monkeypatch.setattr(Image.Image, 'getexif', Mock(side_effect=ValueError('bad metadata')))
    assert web.get_image_caption(str(path)) is None
    assert_images_closed(opened_images)


@pytest.mark.parametrize('mode', ['RGB', 'RGBA', 'LA', 'P', 'L'])
def test_preview_modes_and_reader_cleanup(tmp_path, opened_images, mode):
    path = tmp_path / 'photo.png'
    make_image(path, mode)
    buffer = web.create_image_preview(str(path))
    assert not buffer.closed
    # Readers opened by the helper are already closed before response encoding.
    assert_images_closed(opened_images)
    with buffer, Image.open(buffer) as preview:
        assert preview.format == 'JPEG'
        assert preview.size == (320, 180)
        assert preview.mode in ('RGB', 'L')


def test_transparent_preview_has_white_background(tmp_path):
    path = tmp_path / 'transparent.png'
    with Image.new('RGBA', (640, 360), (0, 0, 0, 0)) as image:
        image.save(path)
    with web.create_image_preview(str(path)) as data, Image.open(data) as preview:
        assert min(preview.getpixel((160, 90))) > 245


def test_preview_failure_closes_reader_and_buffer(tmp_path, opened_images, monkeypatch):
    path = tmp_path / 'photo.png'
    make_image(path)
    buffers = []
    original = io.BytesIO

    def track_buffer(*args):
        buffer = original(*args)
        buffers.append(buffer)
        return buffer

    monkeypatch.setattr(web.io, 'BytesIO', track_buffer)
    monkeypatch.setattr(Image.Image, 'save', Mock(side_effect=OSError('encoding failure')))
    with pytest.raises(OSError, match='encoding failure'):
        web.create_image_preview(str(path))
    assert_images_closed(opened_images)
    assert buffers and all(buffer.closed for buffer in buffers)


@pytest.mark.parametrize('mode, extension', [('RGB', 'jpg'), ('P', 'png')])
def test_caption_write_closes_readers_and_preserves_caption(client, tmp_path, opened_images, mode, extension):
    connection, slideshow = client
    slideshow.current_img = 'photo.' + extension
    path = tmp_path / slideshow.current_img
    make_image(path, mode)
    response = connection.post('/api/image/caption', json={'caption': 'Saved caption'})
    assert response.status_code == 200
    assert_images_closed(opened_images)
    assert web.get_image_caption(str(path)) == 'Saved caption'
    assert_images_closed(opened_images)


def test_caption_write_error_closes_readers(client, tmp_path, opened_images, monkeypatch):
    connection, _ = client
    make_image(tmp_path / 'photo.png')
    monkeypatch.setattr(Image.Image, 'save', Mock(side_effect=OSError('disk failure')))
    response = connection.post('/api/image/caption', json={'caption': 'Cannot save'})
    assert response.status_code == 500
    assert_images_closed(opened_images)


def test_metadata_date_reader_closes_on_exception(tmp_path, monkeypatch):
    import contextlib
    source = Path(__file__).resolve().parents[1] / 'gallery.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    slideshow = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Slideshow')
    method = next(node for node in slideshow.body if isinstance(node, ast.FunctionDef) and node.name == 'get_image_date')
    module = ast.Module(body=[method], type_ignores=[])
    reader = Mock()
    reader._getexif.side_effect = ValueError('bad EXIF')
    image = SimpleNamespace(open=lambda _: contextlib.closing(reader))
    namespace = {'os': os, 'datetime': datetime, 'Image': image}
    exec(compile(ast.fix_missing_locations(module), str(source), 'exec'), namespace)
    path = tmp_path / 'photo.jpg'
    make_image(path)
    result = namespace['get_image_date'](SimpleNamespace(folder=str(tmp_path), config={}), path.name, 'date_taken')
    assert isinstance(result, datetime.datetime)
    reader.close.assert_called_once()


def test_uploaded_fullscreen_fallback_preserved(client, tmp_path):
    connection, slideshow = client
    folder = tmp_path / 'uploaded'
    folder.mkdir()
    make_image(folder / 'photo.png')
    slideshow.current_img = 'uploaded/photo.png'
    response = connection.get('/api/image/full')
    assert response.status_code == 200
    assert response.data.startswith(b'\x89PNG')
    response.close()


def test_preview_failure_still_serves_original(client, tmp_path, monkeypatch):
    connection, _ = client
    make_image(tmp_path / 'photo.png')
    monkeypatch.setattr(web, 'create_image_preview', Mock(side_effect=OSError('thumbnail failure')))
    response = connection.get('/api/image/preview')
    assert response.status_code == 200
    assert response.data.startswith(b'\x89PNG')
    response.close()


def test_preview_response_owns_buffer_until_closed(client, tmp_path, monkeypatch):
    connection, _ = client
    make_image(tmp_path / 'photo.png')
    buffer = web.create_image_preview(str(tmp_path / 'photo.png'))
    monkeypatch.setattr(web, 'create_image_preview', lambda _: buffer)
    response = connection.get('/api/image/preview')
    assert response.status_code == 200
    assert not buffer.closed
    assert response.data.startswith(b'\xff\xd8')
    response.close()
    assert buffer.closed


def test_failed_preview_response_closes_buffer(client, tmp_path, monkeypatch):
    import flask
    connection, _ = client
    make_image(tmp_path / 'photo.png')
    buffer = web.create_image_preview(str(tmp_path / 'photo.png'))
    monkeypatch.setattr(web, 'create_image_preview', lambda _: buffer)
    monkeypatch.setattr(flask, 'send_file', Mock(side_effect=RuntimeError('response failure')))
    response = connection.get('/api/image/preview')
    assert response.status_code == 200  # Existing original-image fallback.
    assert buffer.closed
    response.close()


def test_status_exposes_available_memory_and_legacy_alias(client, monkeypatch):
    connection, _ = client
    helpers = SimpleNamespace(get_memory_info=lambda: 400,
                              get_cpu_usage=lambda: 0, get_cpu_temperature=lambda: 40,
                              get_disk_usage=lambda: None)
    monkeypatch.setitem(sys.modules, 'gallery', helpers)
    response = connection.get('/api/status')
    assert response.status_code == 200
    assert response.json['system']['memory_available_mb'] == 400
    assert response.json['system']['memory_free_mb'] == 400

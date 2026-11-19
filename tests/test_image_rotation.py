import io
import logging

from flask import Flask
from PIL import Image
import pytest
from types import SimpleNamespace

import web
from image_rotation import apply_pil, get_rotation, turn


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


def test_quarter_turns_persist_for_one_image(tmp_path):
    config = tmp_path / 'config.ini'
    assert get_rotation(config, 'holiday/photo.jpg') == 0
    assert turn(config, 'holiday/photo.jpg', 'cw') == 90
    assert turn(config, 'holiday\\photo.jpg', 'cw') == 180
    assert turn(config, 'holiday/photo.jpg', 'ccw') == 90
    assert get_rotation(config, 'other.jpg') == 0
    assert turn(config, 'holiday/photo.jpg', 'cw') == 180
    assert turn(config, 'holiday/photo.jpg', 'cw') == 270
    assert turn(config, 'holiday/photo.jpg', 'cw') == 0
    assert get_rotation(config, 'holiday/photo.jpg') == 0


def test_invalid_turn_is_rejected(tmp_path):
    config = tmp_path / 'config.ini'
    try:
        turn(config, 'photo.jpg', 'upside-down')
    except ValueError as error:
        assert 'clockwise' in str(error)
    else:
        raise AssertionError('invalid direction was accepted')
    assert get_rotation(config, 'photo.jpg') == 0


def test_pillow_rotation_is_clockwise_and_keeps_the_picture():
    with Image.new('RGB', (40, 20), (10, 20, 30)) as image:
        image.putpixel((0, 0), (255, 0, 0))
        turned = apply_pil(image, 90)
        assert turned.size == (20, 40)
        assert turned.getpixel((19, 0)) == (255, 0, 0)
        assert apply_pil(image, 0) is image


def test_web_rotate_updates_preview_and_full_image(client, tmp_path):
    connection, slideshow = client
    web.CONFIG_PATH = str(tmp_path / 'config.ini')
    path = tmp_path / 'photo.png'
    with Image.new('RGB', (80, 40), (0, 0, 0)) as image:
        image.putpixel((0, 0), (255, 0, 0))
        image.save(path)
    slideshow.current_img = 'photo.png'
    response = connection.post('/api/image/rotate', json={'direction': 'cw'})
    assert response.status_code == 200
    assert response.json['rotation'] == 90
    assert slideshow.force_redraw
    preview = connection.get('/api/image/preview')
    full = connection.get('/api/image/full')
    assert preview.status_code == 200 and full.status_code == 200
    with Image.open(io.BytesIO(full.data)) as image:
        assert image.size == (40, 80)
    preview.close()
    full.close()
    assert connection.post('/api/image/rotate', json={'direction': 'sideways'}).status_code == 400

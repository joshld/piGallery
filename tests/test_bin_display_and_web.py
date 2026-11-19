import datetime as dt
import json
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask
import pygame
import pytest

from bin_calendar import BRISBANE, BinCalendar, BinConfig, calendar_view
from bin_display import BinCalendarRenderer, BinPageCycle
from bin_web import register_bin_routes


def sample():
    return dict(property_id='123', house_number='24', house_number_suffix=None,
                unit_number=None, street_name='EXAMPLE ST', suburb='MOOROOKA',
                collection_day='FRIDAY', next_red_bin='2026-11-20',
                next_yellow_bin='2026-11-27', next_green_bin='2026-11-20')


def config(**kwargs):
    return BinConfig(dict(enabled=True, property_id='123', **kwargs))


def test_rotation_preserves_photo_time_and_is_configurable():
    cycle = BinPageCycle()
    settings = config(page_interval_seconds=60, page_duration_seconds=10, display_update_seconds=3)
    assert not cycle.tick(0, settings, True)
    assert not cycle.tick(59, settings, True)
    assert cycle.tick(60, settings, True) and cycle.active
    assert not cycle.tick(62, settings, True)
    assert cycle.tick(63, settings, True)
    assert cycle.tick(70, settings, True) and not cycle.active
    assert not cycle.tick(119, settings, True)
    assert cycle.tick(120, settings, True) and cycle.active


def test_manual_page_and_display_off_do_not_replace_photos():
    cycle = BinPageCycle()
    cycle.request(True)
    assert cycle.tick(0, config(), False) and cycle.active
    cycle.request(False)
    assert cycle.tick(1, config(), True) and not cycle.active
    cycle.request(True)
    cycle.tick(2, config(), True)
    assert cycle.tick(3, config(), True, display_on=False)
    assert not cycle.active


def test_disabled_or_unconfigured_calendar_does_not_rotate():
    cycle = BinPageCycle()
    cycle.tick(0, BinConfig(), False)
    cycle.tick(10000, BinConfig(), False)
    assert not cycle.active
    cycle.tick(0, config(), False)
    cycle.tick(10000, config(), False)
    assert not cycle.active


@pytest.mark.parametrize('size', [(1920, 1080), (1280, 720), (800, 480), (480, 800)])
@pytest.mark.parametrize('weeks', [2, 6])
def test_renderer_adapts_to_resolution_and_week_count(size, weeks):
    pygame.font.init()
    screen = pygame.Surface(size)
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    settings = config(upcoming_weeks=weeks)
    renderer = BinCalendarRenderer()
    view = calendar_view(sample(), now, settings, now)
    renderer.draw(screen, view, settings, now)
    assert screen.get_size() == size
    assert len(renderer.fonts) <= 32
    assert screen.get_at((0, 0))[:3] == (13, 23, 38)


def test_renderer_handles_missing_and_offline_data():
    pygame.font.init()
    screen = pygame.Surface((800, 480))
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    renderer = BinCalendarRenderer()
    renderer.draw(screen, calendar_view(None, None, BinConfig(), now), BinConfig(), now)
    view = calendar_view(sample(), now - dt.timedelta(days=3), config(), now, 'offline')
    renderer.draw(screen, view, config(), now)


@pytest.fixture
def api(tmp_path):
    path = tmp_path / 'config.ini'
    path.write_text('[gallery]\ndelay_seconds=30\n[telegram]\nbot_token=untouched\n', encoding='utf-8')
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    client = SimpleNamespace(lookup=Mock(return_value=[sample()]))
    calendar = BinCalendar(path, client=client, clock=lambda: now)
    slideshow = SimpleNamespace(bin_calendar=calendar, show_bin_calendar=Mock(), force_redraw=False)
    app = Flask(__name__)
    app.testing = True
    register_bin_routes(app, slideshow)
    with app.test_client() as connection:
        yield connection, calendar, slideshow, client


def test_web_configuration_schema_and_live_persistence(api):
    connection, calendar, slideshow, _ = api
    response = connection.get('/api/bin-calendar/config')
    assert response.status_code == 200
    assert response.json['config']['show_green'] is False
    assert 'refresh_time' in response.json['schema']
    response = connection.post('/api/bin-calendar/config', json={'enabled': True, 'property_id': '123', 'upcoming_weeks': 3})
    assert response.status_code == 200
    assert calendar.settings.upcoming_weeks == 3 and slideshow.force_redraw
    assert BinCalendar(calendar.config_path).settings.upcoming_weeks == 3
    assert 'bot_token = untouched' in calendar.config_path.read_text()


def test_invalid_web_values_do_not_change_config(api):
    connection, calendar, _, _ = api
    before = calendar.config_path.read_bytes()
    response = connection.post('/api/bin-calendar/config', json={'refresh_time': '25:00'})
    assert response.status_code == 400
    assert calendar.config_path.read_bytes() == before
    assert connection.post('/api/bin-calendar/config', json=['not an object']).status_code == 400


def test_web_lookup_returns_candidates_without_enabling_or_saving(api):
    connection, calendar, _, client = api
    response = connection.post('/api/bin-calendar/lookup', json={'house_number': '24', 'street_name': 'Example Street', 'suburb': 'Moorooka'})
    assert response.status_code == 200
    assert response.json['properties'][0]['property_id'] == '123'
    assert not calendar.settings.enabled and not calendar.settings.property_id
    client.lookup.assert_called_once()


def test_web_refresh_rate_limit_and_no_get_side_effects(api):
    connection, calendar, _, client = api
    connection.post('/api/bin-calendar/config', json={'enabled': True, 'property_id': '123'})
    for _ in range(3):
        assert connection.get('/api/bin-calendar').status_code == 200
    client.lookup.assert_not_called()
    assert connection.post('/api/bin-calendar/refresh').status_code == 202
    assert connection.post('/api/bin-calendar/refresh').status_code == 429
    assert calendar.manual_requested


def test_web_manual_page_uses_existing_slideshow(api):
    connection, _, slideshow, _ = api
    assert connection.post('/api/bin-calendar/display', json={'show': True}).status_code == 400
    connection.post('/api/bin-calendar/config', json={'enabled': True, 'property_id': '123'})
    assert connection.post('/api/bin-calendar/display', json={'show': True}).status_code == 200
    slideshow.show_bin_calendar.assert_called_once_with(True)
    assert connection.post('/api/bin-calendar/display', json={'show': 'false'}).status_code == 400


def test_lookup_errors_do_not_expose_private_request_urls(api):
    connection, _, _, client = api
    client.lookup.side_effect = RuntimeError('https://secret.example/?private-address')
    response = connection.post('/api/bin-calendar/lookup', json={'house_number': '24'})
    assert response.status_code == 502
    assert 'private-address' not in json.dumps(response.json)


def test_gallery_and_calendar_saves_preserve_each_others_settings(api, monkeypatch):
    import configparser
    import web
    _, calendar, slideshow, _ = api
    monkeypatch.setattr(web, 'slideshow_instance', slideshow)
    monkeypatch.setattr(web, 'CONFIG_PATH', str(calendar.config_path))
    calendar.configure({'page_duration_seconds': 20})
    web.save_gallery_config({'delay_seconds': 42})
    calendar.configure({'upcoming_weeks': 4})
    saved = configparser.ConfigParser()
    saved.read(calendar.config_path)
    assert saved['gallery']['delay_seconds'] == '42'
    assert saved['telegram']['bot_token'] == 'untouched'
    assert saved['bin_calendar']['page_duration_seconds'] == '20'
    assert saved['bin_calendar']['upcoming_weeks'] == '4'

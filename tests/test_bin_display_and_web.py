import datetime as dt
import json
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask
import pygame

from bin_calendar import BRISBANE, BinCalendar, BinConfig, calendar_view
from bin_display import BinCalendarRenderer
from bin_web import register_bin_routes


def sample():
    return dict(property_id='123', house_number='24', house_number_suffix=None,
                unit_number=None, street_name='EXAMPLE ST', suburb='MOOROOKA',
                collection_day='FRIDAY', next_red_bin='2026-11-24',
                next_yellow_bin='2026-11-24', next_green_bin='2026-12-01')


def config(**kwargs):
    return BinConfig(dict(enabled=True, property_id='123', **kwargs))


def test_overlay_keeps_the_photo_and_places_each_group():
    pygame.font.init()
    screen = pygame.Surface((1280, 720))
    screen.fill((10, 20, 30))
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    settings = config(show_green=True, show_days_before=14, red_position='bottom-center', yellow_position='bottom-center', green_position='top-right')
    view = calendar_view(sample(), now, settings, now)
    rects = BinCalendarRenderer().draw(screen, view)
    assert screen.get_at((0, 0))[:3] == (10, 20, 30)
    assert len(rects) == 2
    bottom = max(rects, key=lambda rect: rect.centery)
    top = min(rects, key=lambda rect: rect.centery)
    assert bottom.centery > 500 and bottom.width > top.width
    assert top.centerx > 800 and top.centery < 280
    assert {item['when'] for item in view['bins']} >= {'24 Nov', '1 Dec'}


def test_overlay_fits_small_and_portrait_screens():
    pygame.font.init()
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    view = calendar_view(sample(), now, config(show_green=True, show_days_before=14), now)
    renderer = BinCalendarRenderer()
    for size in ((1920, 1080), (800, 480), (480, 800)):
        screen = pygame.Surface(size)
        rects = renderer.draw(screen, view)
        bounds = screen.get_rect()
        assert rects and all(bounds.contains(rect) for rect in rects)
        assert len(renderer.fonts) <= 32


def test_overlay_stays_off_until_the_lead_up():
    pygame.font.init()
    screen = pygame.Surface((1280, 720))
    screen.fill((10, 20, 30))
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    view = calendar_view(sample(), now, config(), now)
    assert all(not item['visible'] for item in view['bins'])
    assert BinCalendarRenderer().draw(screen, view) == []
    assert screen.get_at((640, 40))[:3] == (10, 20, 30)


def test_overlay_uses_photo_display_correction_and_stays_transparent():
    pygame.font.init()
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    view = calendar_view(sample(), now, config(show_days_before=14, show_yellow=False, show_green=False), now)
    renderer = BinCalendarRenderer()
    plain = pygame.Surface((1280, 720))
    plain.fill((10, 20, 30))
    stretched = pygame.Surface((1280, 720))
    stretched.fill((10, 20, 30))
    plain_rects = renderer.draw(plain, view)
    wide_rects = renderer.draw(stretched, view, 1.2, 1)
    assert plain_rects and wide_rects
    assert abs(wide_rects[0].width / plain_rects[0].width - 1.2) < 0.05
    corner = stretched.get_at(wide_rects[0].topleft)[:3]
    assert corner != (10, 20, 30) and corner != (0, 0, 0)
    assert all(channel < original for channel, original in zip(corner, (10, 20, 30)))
    assert any(stretched.get_at((x, y))[:3] != (10, 20, 30)
               for x in range(wide_rects[0].left, wide_rects[0].right, 3)
               for y in range(wide_rects[0].top, wide_rects[0].bottom, 3))


def test_icon_scale_changes_the_drawn_size():
    pygame.font.init()
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    renderer = BinCalendarRenderer()
    normal = pygame.Surface((1280, 720))
    large = pygame.Surface((1280, 720))
    normal_view = calendar_view(sample(), now, config(show_days_before=14, show_yellow=False, show_green=False), now)
    large_view = calendar_view(sample(), now, config(show_days_before=14, show_yellow=False, show_green=False, icon_scale=200), now)
    normal_rects = renderer.draw(normal, normal_view)
    large_rects = renderer.draw(large, large_view)
    assert normal_view['icon_scale'] == 100 and large_view['icon_scale'] == 200
    assert abs(large_rects[0].width / normal_rects[0].width - 2) < 0.08


def test_missing_dates_draw_nothing():
    pygame.font.init()
    screen = pygame.Surface((800, 480))
    screen.fill((10, 20, 30))
    assert BinCalendarRenderer().draw(screen, {'bins': []}) == []
    assert screen.get_at((400, 240))[:3] == (10, 20, 30)


def api_client(tmp_path):
    path = tmp_path / 'config.ini'
    path.write_text('[gallery]\ndelay_seconds=30\n[telegram]\nbot_token=untouched\n', encoding='utf-8')
    now = dt.datetime(2026, 11, 19, 18, tzinfo=BRISBANE)
    client = SimpleNamespace(lookup=Mock(return_value=[sample()]))
    calendar = BinCalendar(path, client=client, clock=lambda: now)
    slideshow = SimpleNamespace(bin_calendar=calendar, force_redraw=False)
    app = Flask(__name__)
    app.testing = True
    register_bin_routes(app, slideshow)
    return app.test_client(), calendar, slideshow, client


def test_web_configuration_schema_and_live_persistence(tmp_path):
    connection, calendar, slideshow, _ = api_client(tmp_path)
    response = connection.get('/api/bin-calendar/config')
    assert response.status_code == 200
    assert response.json['config']['show_green'] is False
    assert 'refresh_days' in response.json['schema']
    assert 'page_duration_seconds' not in response.json['schema']
    response = connection.post('/api/bin-calendar/config', json={
        'enabled': True, 'property_id': '123', 'refresh_days': 2, 'red_position': 'top-left', 'icon_scale': 150})
    assert response.status_code == 200
    assert calendar.settings.refresh_days == 2
    assert calendar.settings.red_position == 'top-left'
    assert calendar.settings.icon_scale == 150
    assert slideshow.force_redraw
    assert BinCalendar(calendar.config_path).settings.refresh_days == 2
    assert 'bot_token = untouched' in calendar.config_path.read_text()


def test_invalid_web_values_do_not_change_config(tmp_path):
    connection, calendar, _, _ = api_client(tmp_path)
    before = calendar.config_path.read_bytes()
    response = connection.post('/api/bin-calendar/config', json={'refresh_time': '25:00'})
    assert response.status_code == 400
    assert calendar.config_path.read_bytes() == before
    assert connection.post('/api/bin-calendar/config', json=['not an object']).status_code == 400


def test_web_lookup_returns_candidates_without_enabling_or_saving(tmp_path):
    connection, calendar, _, client = api_client(tmp_path)
    response = connection.post('/api/bin-calendar/lookup', json={'house_number': '24', 'street_name': 'Example Street', 'suburb': 'Moorooka'})
    assert response.status_code == 200
    assert response.json['properties'][0]['property_id'] == '123'
    assert not calendar.settings.enabled and not calendar.settings.property_id
    client.lookup.assert_called_once()


def test_web_refresh_rate_limit_and_no_get_side_effects(tmp_path):
    connection, calendar, _, client = api_client(tmp_path)
    connection.post('/api/bin-calendar/config', json={'enabled': True, 'property_id': '123'})
    for _ in range(3):
        assert connection.get('/api/bin-calendar').status_code == 200
    client.lookup.assert_not_called()
    assert connection.post('/api/bin-calendar/refresh').status_code == 202
    assert connection.post('/api/bin-calendar/refresh').status_code == 429
    assert calendar.manual_requested


def test_lookup_errors_do_not_expose_private_request_urls(tmp_path):
    connection, _, _, client = api_client(tmp_path)
    client.lookup.side_effect = RuntimeError('https://secret.example/?private-address')
    response = connection.post('/api/bin-calendar/lookup', json={'house_number': '24'})
    assert response.status_code == 502
    assert 'private-address' not in json.dumps(response.json)


def test_gallery_and_calendar_saves_preserve_each_others_settings(tmp_path, monkeypatch):
    import configparser
    import web
    connection, calendar, slideshow, _ = api_client(tmp_path)
    monkeypatch.setattr(web, 'slideshow_instance', slideshow)
    monkeypatch.setattr(web, 'CONFIG_PATH', str(calendar.config_path))
    calendar.configure({'refresh_days': 3})
    web.save_gallery_config({'delay_seconds': 42})
    connection.post('/api/bin-calendar/config', json={'green_position': 'top-right'})
    saved = configparser.ConfigParser()
    saved.read(calendar.config_path)
    assert saved['gallery']['delay_seconds'] == '42'
    assert saved['telegram']['bot_token'] == 'untouched'
    assert saved['bin_calendar']['refresh_days'] == '3'
    assert saved['bin_calendar']['green_position'] == 'top-right'
    assert 'page_duration_seconds' not in saved['bin_calendar']

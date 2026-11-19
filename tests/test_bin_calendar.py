import configparser
import datetime as dt
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bin_calendar import (API_URL, BRISBANE, BinCalendar, BinConfig, ConfigError,
                          CouncilClient, SCHEMA, calendar_view, next_refresh)


def moment(value='2026-11-19T12:00:00+10:00'):
    return dt.datetime.fromisoformat(value)


def record(**changes):
    row = dict(property_id='123', house_number='24', house_number_suffix=None,
               unit_number=None, street_name='EXAMPLE ST', suburb='MOOROOKA',
               collection_day='FRIDAY', next_red_bin='2026-11-20',
               next_yellow_bin='2026-11-27', next_green_bin='2026-11-20')
    row.update(changes)
    return row


def settings(**changes):
    return BinConfig(dict(enabled=True, property_id='123', **changes))


@pytest.mark.parametrize('values', [
    {'upcoming_weeks': 0}, {'upcoming_weeks': 7}, {'refresh_time': '25:00'},
    {'refresh_time': '6:00'}, {'refresh_interval_hours': 0},
    {'retry_initial_seconds': 10}, {'retry_initial_seconds': 8000, 'retry_max_seconds': 7000},
    {'page_duration_seconds': 60, 'page_interval_seconds': 30},
    {'display_update_seconds': True}, {'display_update_seconds': '1.5'},
    {'show_green': 'maybe'}, {'property_id': '12 OR 1=1'},
    {'cache_file': '../config.ini'}, {'cache_file': '/etc/file.json'},
    {'cache_file': 'config.ini'}, {'unknown_field': 10},
])
def test_invalid_settings_rejected(values):
    with pytest.raises(ConfigError):
        BinConfig(values)


def test_enable_requires_property_and_bins():
    with pytest.raises(ConfigError):
        BinConfig({'enabled': True})
    with pytest.raises(ConfigError):
        settings(show_red=False, show_yellow=False, show_green=False)
    assert BinConfig().show_green is False
    assert len(BinConfig.defaults()) == len(SCHEMA)


@pytest.mark.parametrize('last, expected', [
    ('2026-11-19T05:30:00+10:00', '2026-11-19T06:00:00+10:00'),
    ('2026-11-19T06:00:00+10:00', '2026-11-20T06:00:00+10:00'),
    ('2026-12-31T23:30:00+10:00', '2027-01-01T06:00:00+10:00'),
])
def test_daily_schedule_and_year_boundary(last, expected):
    assert next_refresh(moment(last), settings()) == moment(expected)


def test_interval_schedule_uses_configured_frequency():
    assert next_refresh(moment('2026-12-31T22:00:00+10:00'), settings(refresh_mode='interval', refresh_interval_hours=6)) == moment('2027-01-01T04:00:00+10:00')


def test_actual_dates_override_weekday_and_holiday_assumptions():
    now = moment('2026-12-25T12:00:00+10:00')
    row = record(next_red_bin='2026-12-26', next_yellow_bin='2027-01-02')
    view = calendar_view(row, now, settings(), now)
    assert view['next']['date'] == '2026-12-26'
    assert view['next']['day'] == 'Saturday'
    assert view['next']['relative'] == 'TOMORROW'
    assert view['next']['confirmed']
    following = next(event for event in view['events'] if event['date'] == '2027-01-02')
    assert {item['colour']: item['confirmed'] for item in following['bins']} == {'red': False, 'yellow': True}


def test_brisbane_today_when_utc_is_previous_day():
    now = moment('2026-11-19T15:00:00+00:00')
    view = calendar_view(record(), now, settings(), now)
    assert view['next']['relative'] == 'TODAY'
    assert view['next']['days_remaining'] == 0
    assert view['next']['highlight']
    assert view['timezone'] == 'Australia/Brisbane'


def test_no_green_subscription_and_absent_green_date():
    view = calendar_view(record(), moment(), settings(), moment())
    assert not any(item['colour'] == 'green' for event in view['events'] for item in event['bins'])
    view = calendar_view(record(next_green_bin=None), moment(), settings(show_green=True), moment())
    assert not any(item['colour'] == 'green' for event in view['events'] for item in event['bins'])


def test_following_week_contains_labelled_estimates_and_confirmed_dates():
    view = calendar_view(record(), moment(), settings(), moment())
    assert len(view['weeks']) == 2
    assert view['weeks'][1]['label'] == 'FOLLOWING WEEK'
    assert view['has_estimates']
    assert any(not item['confirmed'] for event in view['weeks'][1]['events'] for item in event['bins'])


def test_published_only_mode_does_not_invent_future_dates():
    view = calendar_view(record(), moment(), settings(show_estimates=False), moment())
    assert not view['has_estimates']
    assert all(item['confirmed'] for event in view['events'] for item in event['bins'])
    assert [event['date'] for event in view['events']] == ['2026-11-20', '2026-11-27']


def test_highlights_configurable_and_old_cache_not_projected_forever():
    now = moment('2026-11-20T05:00:00+10:00')
    view = calendar_view(record(), now, settings(highlight_today=False), now)
    assert not view['next']['highlight']
    later = moment('2026-12-20T05:00:00+10:00')
    old = calendar_view(record(), now, settings(), later, 'network unavailable')
    assert old['offline'] and old['stale'] and old['ready']
    assert old['next'] is None


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_address_lookup_uses_verified_fields_and_encoded_parameters():
    session = SimpleNamespace(get=Mock(return_value=Response({'total_count': 1, 'results': [record()]})))
    client = CouncilClient(session)
    result = client.lookup(BinConfig({'house_number': '24', 'street_name': 'Example Street', 'suburb': 'Moorooka'}))
    assert result[0]['property_id'] == '123'
    call = session.get.call_args
    assert call[0] == (API_URL,)
    assert call[1]['params']['where'] == 'house_number="24" AND street_name="EXAMPLE ST" AND suburb="MOOROOKA"'
    assert call[1]['timeout'] == 15


def test_unit_and_number_suffix_lookup():
    session = SimpleNamespace(get=Mock(return_value=Response({'total_count': 0, 'results': []})))
    client = CouncilClient(session)
    client.lookup(BinConfig({'house_number': '24a', 'street_name': 'Example St', 'suburb': 'Moorooka', 'unit_number': '2'}))
    where = session.get.call_args[1]['params']['where']
    assert 'house_number_suffix="A"' in where and 'unit_number="2"' in where


def test_address_quotes_cannot_escape_the_query_literal():
    session = SimpleNamespace(get=Mock(return_value=Response({'total_count': 0, 'results': []})))
    CouncilClient(session).lookup(BinConfig({'house_number': '24', 'street_name': 'EXAMPLE" OR TRUE', 'suburb': 'Moorooka'}))
    assert '\\"' in session.get.call_args[1]['params']['where']


@pytest.mark.parametrize('payload', [
    {'results': []}, {'total_count': 1, 'results': [{}]},
    {'total_count': 1, 'results': [record(next_red_bin='not a date')]},
    {'total_count': 100, 'results': []},
])
def test_bad_api_responses_rejected(payload):
    session = SimpleNamespace(get=Mock(return_value=Response(payload)))
    with pytest.raises(ValueError):
        CouncilClient(session).lookup(settings())


@pytest.fixture
def calendar(tmp_path):
    path = tmp_path / 'config.ini'
    path.write_text('[gallery]\ndelay_seconds=30\n[telegram]\nbot_token=keep-private\n', encoding='utf-8')
    clock = Mock(return_value=moment())
    client = SimpleNamespace(lookup=Mock(return_value=[record()]))
    service = BinCalendar(path, client=client, clock=clock)
    service.configure(dict(enabled=True, property_id='123'))
    return service, clock, client


def test_cache_survives_restart_and_api_failure(calendar):
    service, clock, client = calendar
    assert service.refresh_once()
    saved = service.cache_path.read_bytes()
    client.lookup.side_effect = OSError('network failed')
    clock.return_value += dt.timedelta(days=1)
    assert not service.refresh_once()
    assert service.cache_path.read_bytes() == saved
    assert service.snapshot()['offline'] and service.snapshot()['ready']
    restarted = BinCalendar(service.config_path, client=client, clock=clock)
    assert restarted.snapshot()['ready']
    assert restarted.record['property_id'] == '123'


def test_initial_failure_schedules_backoff_instead_of_spinning(calendar):
    service, clock, client = calendar
    client.lookup.side_effect = OSError('offline')
    for expected in (900, 1800, 3600, 7200, 7200):
        assert not service.refresh_once()
        assert (service._due() - clock()).total_seconds() == expected
        clock.return_value = service._due()


def test_scheduled_cache_load_avoids_unnecessary_fetch(calendar):
    service, clock, client = calendar
    service.refresh_once()
    restarted = BinCalendar(service.config_path, client=client, clock=clock)
    assert restarted._due() > clock()
    for _ in range(10):
        restarted.snapshot()
    assert client.lookup.call_count == 1


def test_ambiguous_address_does_not_choose_a_property(calendar):
    service, _, client = calendar
    client.lookup.return_value = [record(), record(property_id='124')]
    assert not service.refresh_once()
    assert service.record is None


def test_manual_refresh_is_coalesced_and_rate_limited(calendar):
    service, clock, _ = calendar
    assert service.request_refresh()
    assert not service.request_refresh()
    service.refresh_once()
    assert not service.request_refresh()
    clock.return_value += dt.timedelta(seconds=service.settings.manual_refresh_cooldown_seconds)
    assert service.request_refresh()


def test_config_persists_without_changing_existing_sections(calendar):
    service, _, _ = calendar
    service.configure({'page_duration_seconds': 20, 'show_green': False})
    parser = configparser.ConfigParser()
    parser.read(service.config_path)
    assert parser['telegram']['bot_token'] == 'keep-private'
    assert parser['gallery']['delay_seconds'] == '30'
    restarted = BinCalendar(service.config_path)
    assert restarted.settings.page_duration_seconds == 20
    before = service.config_path.read_bytes()
    with pytest.raises(ConfigError):
        service.configure({'refresh_time': '99:99'})
    assert service.config_path.read_bytes() == before


def test_changed_property_never_displays_old_cached_address(calendar):
    service, _, _ = calendar
    service.refresh_once()
    service.configure({'property_id': '124'})
    assert service.record is None
    assert not service.snapshot()['ready']


def test_corrupt_cache_does_not_stop_the_service(calendar):
    service, clock, client = calendar
    service.cache_path.parent.mkdir(parents=True, exist_ok=True)
    service.cache_path.write_text('broken JSON', encoding='utf-8')
    restarted = BinCalendar(service.config_path, client=client, clock=clock)
    assert restarted.record is None
    assert restarted._due() == clock()


def test_invalid_config_disables_only_the_feature(tmp_path):
    path = tmp_path / 'config.ini'
    path.write_text('[bin_calendar]\nenabled=true\npage_duration_seconds=broken\n', encoding='utf-8')
    service = BinCalendar(path)
    assert not service.settings.enabled
    assert service.config_error


def test_reminders_opt_in_published_dates_only_and_once_daily(calendar):
    service, clock, _ = calendar
    service.notifier = Mock()
    clock.return_value = moment('2026-11-19T18:00:00+10:00')
    service.refresh_once()
    service.notify_if_due()
    service.notifier.assert_not_called()
    service.configure({'notify_tomorrow': True})
    service.notify_if_due()
    service.notify_if_due()
    service.notifier.assert_called_once()
    assert 'General waste' in service.notifier.call_args[0][0]
    assert 'Garden waste' not in service.notifier.call_args[0][0]
    state = json.loads(service.cache_path.read_text())
    assert state['last_notification'] == '2026-11-19'


def test_no_notification_busy_loop_without_data(calendar):
    service, clock, _ = calendar
    service.notifier = Mock()
    service.configure({'notify_today': True})
    assert service._notification_due(clock()) is None


def test_worker_failure_uses_configured_clock_check_without_spinning(calendar):
    service, _, client = calendar
    client.lookup.side_effect = OSError('offline')
    service.configure({'scheduler_check_seconds': 17})
    wait_times = []

    def wait(timeout):
        wait_times.append(timeout)
        service.stopping.set()

    service.wake = SimpleNamespace(clear=lambda: None, wait=wait)
    service._run()
    assert wait_times == [17]

import configparser
import datetime as dt
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bin_calendar import (API_URL, BRISBANE, CHECK_SECONDS, MANUAL_COOLDOWN_SECONDS,
                          RETRY_INITIAL_SECONDS, RETRY_MAX_SECONDS, BinCalendar, BinConfig,
                          ConfigError, CouncilClient, SCHEMA, calendar_view, next_refresh)


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
    {'refresh_days': 0}, {'refresh_days': 15}, {'show_days_before': 15}, {'refresh_time': '25:00'},
    {'refresh_time': '6:00'}, {'red_position': 'beside-the-clock'},
    {'show_green': 'maybe'}, {'property_id': '12 OR 1=1'}, {'unknown_field': 10},
    {'icon_scale': 10}, {'icon_scale': 250},
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
    assert BinConfig().red_position == 'top-center'
    assert len(BinConfig.defaults()) == len(SCHEMA)


@pytest.mark.parametrize('last, expected', [
    ('2026-11-19T05:30:00+10:00', '2026-11-19T06:00:00+10:00'),
    ('2026-11-19T06:00:00+10:00', '2026-11-20T06:00:00+10:00'),
    ('2026-12-31T23:30:00+10:00', '2027-01-01T06:00:00+10:00'),
])
def test_daily_schedule_and_year_boundary(last, expected):
    assert next_refresh(moment(last), settings()) == moment(expected)


def test_every_two_days_waits_for_the_gap():
    every_two = settings(refresh_days=2)
    assert next_refresh(moment('2026-11-19T06:00:00+10:00'), every_two) == moment('2026-11-21T06:00:00+10:00')
    assert next_refresh(moment('2026-12-31T22:00:00+10:00'), every_two) == moment('2027-01-02T06:00:00+10:00')


def test_published_dates_are_used_as_printed():
    now = moment('2026-12-25T12:00:00+10:00')
    row = record(next_red_bin='2026-12-26', next_yellow_bin='2027-01-02', next_green_bin=None)
    view = calendar_view(row, now, settings(show_green=True), now)
    assert [(item['colour'], item['date'], item['when']) for item in view['bins']] == [
        ('red', '2026-12-26', 'Tomorrow'),
        ('yellow', '2027-01-02', '2 Jan'),
    ]


def test_brisbane_today_when_utc_is_previous_day():
    now = moment('2026-11-19T15:00:00+00:00')
    view = calendar_view(record(), now, settings(), now)
    assert view['bins'][0]['when'] == 'Today'
    assert view['bins'][0]['days_remaining'] == 0
    assert view['timezone'] == 'Australia/Brisbane'


def test_hidden_bins_and_missing_green_date_are_omitted():
    view = calendar_view(record(), moment(), settings(), moment())
    assert [item['colour'] for item in view['bins']] == ['red', 'yellow']
    view = calendar_view(record(next_green_bin=None), moment(), settings(show_green=True), moment())
    assert [item['colour'] for item in view['bins']] == ['red', 'yellow']


def test_icons_stay_up_for_the_configured_days_before_collection():
    early = moment('2026-11-17T08:00:00+10:00')
    lead = moment('2026-11-18T00:30:00+10:00')
    on_day = moment('2026-11-20T08:00:00+10:00')
    after = moment('2026-11-21T08:00:00+10:00')
    assert not calendar_view(record(), early, settings(), early)['bins'][0]['visible']
    opened = calendar_view(record(), lead, settings(), lead)
    assert opened['show_days_before'] == 2
    assert {item['colour']: item['visible'] for item in opened['bins']} == {'red': True, 'yellow': False}
    assert calendar_view(record(), on_day, settings(), on_day)['bins'][0]['visible']
    assert not calendar_view(record(), after, settings(), after)['bins'][0]['visible']
    longer = calendar_view(record(), early, settings(show_days_before=3), early)
    assert longer['bins'][0]['visible']


def test_each_bin_keeps_its_own_screen_position():
    view = calendar_view(record(), moment(), settings(show_green=True, red_position='bottom-left', green_position='top-right'), moment())
    assert {item['colour']: item['position'] for item in view['bins']} == {
        'red': 'bottom-left', 'yellow': 'top-center', 'green': 'top-right'}


def test_no_record_has_no_icons_and_offline_keeps_saved_dates():
    now = moment()
    assert calendar_view(None, None, settings(), now)['bins'] == []
    offline = calendar_view(record(), now, settings(), now, 'network unavailable')
    assert offline['offline'] and offline['ready']
    assert offline['bins'][0]['date'] == '2026-11-20'


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
    delay = RETRY_INITIAL_SECONDS
    for _ in range(5):
        assert not service.refresh_once()
        assert (service._due() - clock()).total_seconds() == delay
        clock.return_value = service._due()
        delay = min(RETRY_MAX_SECONDS, delay * 2)


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
    clock.return_value += dt.timedelta(seconds=MANUAL_COOLDOWN_SECONDS)
    assert service.request_refresh()


def test_config_persists_without_changing_existing_sections(calendar):
    service, _, _ = calendar
    service.configure({'refresh_days': 3, 'red_position': 'bottom-left', 'show_green': False})
    parser = configparser.ConfigParser()
    parser.read(service.config_path)
    assert parser['telegram']['bot_token'] == 'keep-private'
    assert parser['gallery']['delay_seconds'] == '30'
    restarted = BinCalendar(service.config_path)
    assert restarted.settings.refresh_days == 3
    assert restarted.settings.red_position == 'bottom-left'
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


def test_invalid_config_hides_bins_and_old_extra_keys_are_ignored(tmp_path):
    broken = tmp_path / 'broken.ini'
    broken.write_text('[bin_calendar]\nenabled=true\nrefresh_days=nope\n', encoding='utf-8')
    service = BinCalendar(broken)
    assert not service.settings.enabled
    assert service.config_error

    legacy = tmp_path / 'legacy.ini'
    legacy.write_text(
        '[bin_calendar]\nenabled=true\nproperty_id=123\npage_duration_seconds=broken\n'
        'notify_today=true\nshow_estimates=true\n',
        encoding='utf-8')
    legacy_service = BinCalendar(legacy)
    assert legacy_service.settings.enabled
    assert legacy_service.settings.refresh_days == 1
    assert legacy_service.settings.red_position == 'top-center'
    legacy_service.configure({'refresh_days': 2})
    saved = configparser.ConfigParser()
    saved.read(legacy)
    assert 'page_duration_seconds' not in saved['bin_calendar']
    assert 'notify_today' not in saved['bin_calendar']


def test_worker_waits_instead_of_spinning(calendar):
    service, _, client = calendar
    client.lookup.side_effect = OSError('offline')
    wait_times = []

    def wait(timeout):
        wait_times.append(timeout)
        service.stopping.set()

    service.wake = SimpleNamespace(clear=lambda: None, wait=wait, set=lambda: None)
    service._run()
    assert wait_times == [CHECK_SECONDS]

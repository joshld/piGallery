"""Brisbane Council bin dates, validated settings and an offline-safe cache.

The official dataset publishes one next date per colour, not a full calendar.
Every generated recurrence is explicitly marked as an estimate.
"""
import configparser
import datetime as dt
import json
import logging
import math
import os
from pathlib import Path
import re
import tempfile
import threading

import requests

try:
    from zoneinfo import ZoneInfo
    BRISBANE = ZoneInfo('Australia/Brisbane')
except (ImportError, KeyError):
    # Queensland has no daylight saving. Also supports Python 3.8/Windows
    # installations without an IANA timezone database, without a dependency.
    BRISBANE = dt.timezone(dt.timedelta(hours=10), 'Australia/Brisbane')

API_URL = 'https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/bin-collection-calendar/records'
BIN_FIELDS = {'red': 'next_red_bin', 'yellow': 'next_yellow_bin', 'green': 'next_green_bin'}
BIN_NAMES = {'red': 'General waste', 'yellow': 'Recycling', 'green': 'Garden waste'}


def spec(label, default, kind='str', group='Display', minimum=None, maximum=None, choices=None, help_text=''):
    return dict(label=label, default=default, type=kind, group=group,
                min=minimum, max=maximum, choices=choices, help=help_text)


SCHEMA = {
    'enabled': spec('Enable bin calendar', False, 'bool', 'Address and bins'),
    'house_number': spec('Street number', '', group='Address and bins'),
    'street_name': spec('Street name', '', group='Address and bins', help_text='For example, EXAMPLE STREET or EXAMPLE ST.'),
    'suburb': spec('Suburb', '', group='Address and bins'),
    'unit_number': spec('Unit number (if applicable)', '', group='Address and bins'),
    'property_id': spec('Council property ID', '', group='Address and bins', help_text='Set by address lookup; optional when an exact address is configured.'),
    'show_red': spec('Show general waste (red)', True, 'bool', 'Address and bins'),
    'show_yellow': spec('Show recycling (yellow)', True, 'bool', 'Address and bins'),
    'show_green': spec('Show garden waste (green)', False, 'bool', 'Address and bins', help_text='Enable only if you have a green-waste service.'),
    'refresh_mode': spec('Automatic refresh mode', 'daily', group='Refresh and cache', choices=['daily', 'interval']),
    'refresh_time': spec('Daily refresh time (Brisbane)', '06:00', 'time', 'Refresh and cache'),
    'refresh_interval_hours': spec('Interval-mode refresh frequency (hours)', 24, 'int', 'Refresh and cache', 1, 168),
    'retry_initial_seconds': spec('Initial retry delay (seconds)', 900, 'int', 'Refresh and cache', 60, 86400),
    'retry_max_seconds': spec('Maximum retry delay (seconds)', 7200, 'int', 'Refresh and cache', 60, 172800),
    'request_timeout_seconds': spec('API request timeout (seconds)', 15, 'int', 'Refresh and cache', 3, 60),
    'manual_refresh_cooldown_seconds': spec('Manual refresh cooldown (seconds)', 60, 'int', 'Refresh and cache', 30, 3600),
    'scheduler_check_seconds': spec('Scheduler clock-check frequency (seconds)', 60, 'int', 'Refresh and cache', 1, 3600),
    'stale_after_hours': spec('Mark cached data as old after (hours)', 48, 'int', 'Refresh and cache', 1, 720),
    'forecast_max_cache_age_days': spec('Stop estimates when cache is older than (days)', 14, 'int', 'Refresh and cache', 1, 90),
    'cache_file': spec('Local cache file', '.cache/bin-calendar.json', group='Refresh and cache'),
    'display_update_seconds': spec('Screen update frequency (seconds)', 30, 'int', 'Display', 1, 3600),
    'web_poll_seconds': spec('Web status update frequency (seconds)', 30, 'int', 'Display', 10, 3600),
    'page_interval_seconds': spec('Time between calendar pages (seconds)', 300, 'int', 'Display', 30, 86400),
    'page_duration_seconds': spec('Calendar page duration (seconds)', 15, 'int', 'Display', 5, 120),
    'upcoming_weeks': spec('Upcoming weeks to show', 2, 'int', 'Display', 1, 6),
    'show_estimates': spec('Show clearly labelled regular-service estimates', True, 'bool', 'Display'),
    'red_interval_days': spec('General-waste recurrence for estimates (days)', 7, 'int', 'Display', 1, 31),
    'yellow_interval_days': spec('Recycling recurrence for estimates (days)', 14, 'int', 'Display', 1, 31),
    'green_interval_days': spec('Garden-waste recurrence for estimates (days)', 14, 'int', 'Display', 1, 31),
    'show_address': spec('Show street address on the connected screen', False, 'bool', 'Display'),
    'highlight_today': spec('Highlight collection today', True, 'bool', 'Highlights and reminders'),
    'highlight_tomorrow': spec('Highlight collection tomorrow', True, 'bool', 'Highlights and reminders'),
    'highlight_days_before': spec('Highlight collections within this many days', 2, 'int', 'Highlights and reminders', 0, 7),
    'notify_today': spec('Telegram reminder on collection day', False, 'bool', 'Highlights and reminders'),
    'notify_tomorrow': spec('Telegram reminder the day before', False, 'bool', 'Highlights and reminders'),
    'notification_time': spec('Reminder time (Brisbane)', '18:00', 'time', 'Highlights and reminders'),
}
for _order, _field in enumerate(SCHEMA.values()):
    _field['order'] = _order


class ConfigError(ValueError):
    pass


class BinConfig:
    def __init__(self, values=None):
        values = values or {}
        unknown = set(values) - set(SCHEMA)
        if unknown:
            raise ConfigError('Unknown calendar settings: ' + ', '.join(sorted(unknown)))
        self.values = {}
        for key, field in SCHEMA.items():
            value = values.get(key, field['default'])
            try:
                if field['type'] == 'bool':
                    text = str(value).strip().lower()
                    if text not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                        raise ValueError()
                    value = text in ('true', '1', 'yes', 'on')
                elif field['type'] == 'int':
                    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value).strip()):
                        raise ValueError()
                    value = int(value)
                    if not field['min'] <= value <= field['max']:
                        raise ValueError()
                else:
                    value = str(value).strip()
                    if len(value) > 240 or '\n' in value or '\r' in value or '\0' in value:
                        raise ValueError()
                    if field['type'] == 'time' and not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value):
                        raise ValueError()
                    if field['choices'] and value not in field['choices']:
                        raise ValueError()
            except (TypeError, ValueError):
                raise ConfigError('Invalid value for ' + field['label'])
            self.values[key] = value
        if self.retry_max_seconds < self.retry_initial_seconds:
            raise ConfigError('Maximum retry delay must be at least the initial retry delay')
        if self.page_duration_seconds >= self.page_interval_seconds:
            raise ConfigError('Calendar page duration must be shorter than the time between pages')
        if self.property_id and not re.fullmatch(r'[0-9]{1,16}', self.property_id):
            raise ConfigError('Council property ID must contain digits only')
        cache = Path(self.cache_file)
        if cache.is_absolute() or '..' in cache.parts or not cache.parts or cache.parts[0] != '.cache' or cache.suffix != '.json':
            raise ConfigError('Cache file must be a JSON file inside the application .cache directory')
        if self.enabled and not (self.show_red or self.show_yellow or self.show_green):
            raise ConfigError('Enable at least one bin colour')
        if self.enabled and not self.has_address:
            raise ConfigError('Look up a property or enter its street number, street and suburb first')

    def __getattr__(self, name):
        try:
            return self.values[name]
        except KeyError:
            raise AttributeError(name)

    @property
    def has_address(self):
        return bool(self.property_id or (self.house_number and self.street_name and self.suburb))

    @property
    def identity(self):
        return tuple(self.values[key].upper() for key in ('property_id', 'house_number', 'street_name', 'suburb', 'unit_number'))

    def to_dict(self):
        return dict(self.values)

    @classmethod
    def defaults(cls):
        return {key: str(field['default']).lower() if isinstance(field['default'], bool) else str(field['default'])
                for key, field in SCHEMA.items()}


def now_brisbane():
    return dt.datetime.now(BRISBANE)


def next_refresh(last_success, settings):
    if settings.refresh_mode == 'interval':
        return last_success + dt.timedelta(hours=settings.refresh_interval_hours)
    hour, minute = map(int, settings.refresh_time.split(':'))
    candidate = last_success.astimezone(BRISBANE).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return candidate if candidate > last_success else candidate + dt.timedelta(days=1)


def quote(value):
    """ODSQL double-quoted literals, passed separately as HTTP parameters."""
    return json.dumps(str(value), ensure_ascii=False)


def normalize_street(value):
    words = re.sub(r'\s+', ' ', value.strip().upper()).split()
    suffixes = {'STREET': 'ST', 'ROAD': 'RD', 'AVENUE': 'AVE', 'DRIVE': 'DR', 'COURT': 'CT',
                'CRESCENT': 'CRES', 'TERRACE': 'TCE', 'PARADE': 'PDE', 'PLACE': 'PL',
                'LANE': 'LANE', 'CIRCUIT': 'CCT', 'CLOSE': 'CL', 'BOULEVARD': 'BVD',
                'HIGHWAY': 'HWY', 'ESPLANADE': 'ESP', 'GROVE': 'GR'}
    if words:
        words[-1] = suffixes.get(words[-1], words[-1])
    return ' '.join(words)


def address_label(record):
    number = str(record.get('house_number') or '') + str(record.get('house_number_suffix') or '')
    if record.get('unit_number'):
        number = str(record['unit_number']) + '/' + number
    return ' '.join([number, str(record.get('street_name') or '')]).strip() + ', ' + str(record.get('suburb') or '')


def validate_record(record):
    if not isinstance(record, dict) or not record.get('property_id'):
        raise ValueError('Council record has no property identifier')
    for field in BIN_FIELDS.values():
        if field not in record:
            raise ValueError('Council bin date schema changed')
        if record[field] is not None:
            dt.date.fromisoformat(record[field])
    return record


class CouncilClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.request_lock = threading.Lock()

    def query(self, where, timeout):
        with self.request_lock:
            with self.session.get(API_URL, params={'where': where, 'limit': 20}, timeout=timeout) as response:
                response.raise_for_status()
                payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('results'), list) or 'total_count' not in payload:
            raise ValueError('Council API schema changed')
        if payload['total_count'] > 20:
            raise ValueError('Too many matching addresses; add the unit and exact street name')
        return [validate_record(row) for row in payload['results']]

    def lookup(self, settings):
        if settings.property_id:
            return self.query('property_id=' + quote(settings.property_id), settings.request_timeout_seconds)
        match = re.fullmatch(r'\s*(\d+)\s*([A-Za-z]?)\s*', settings.house_number)
        if not match or not settings.street_name or not settings.suburb:
            raise ConfigError('Enter a street number, street and suburb; use the separate unit field')
        number, suffix = match.groups()
        terms = ['house_number=' + quote(number), 'street_name=' + quote(normalize_street(settings.street_name)),
                 'suburb=' + quote(settings.suburb.upper())]
        if suffix:
            terms.append('house_number_suffix=' + quote(suffix.upper()))
        if settings.unit_number:
            terms.append('unit_number=' + quote(settings.unit_number.upper()))
        return self.query(' AND '.join(terms), settings.request_timeout_seconds)


def calendar_view(record, fetched_at, settings, now, error=None):
    now = now.astimezone(BRISBANE)
    today = now.date()
    age_hours = max(0, (now - fetched_at).total_seconds() / 3600) if fetched_at else None
    stale = fetched_at is not None and age_hours >= settings.stale_after_hours
    horizon = today + dt.timedelta(weeks=settings.upcoming_weeks)
    dates = {}
    for colour, field in BIN_FIELDS.items():
        if not record or not settings.values['show_' + colour] or not record.get(field):
            continue
        published = dt.date.fromisoformat(record[field])
        if today <= published < horizon:
            dates.setdefault(published, []).append({'colour': colour, 'name': BIN_NAMES[colour], 'confirmed': True})
        allow_estimates = settings.show_estimates and age_hours is not None and age_hours <= settings.forecast_max_cache_age_days * 24
        if allow_estimates:
            interval = dt.timedelta(days=settings.values[colour + '_interval_days'])
            candidate = published + interval
            if candidate < today:
                candidate += interval * max(0, math.ceil((today - candidate).days / interval.days))
            while candidate < horizon:
                dates.setdefault(candidate, []).append({'colour': colour, 'name': BIN_NAMES[colour], 'confirmed': False})
                candidate += interval
    events = []
    for day, bins in sorted(dates.items()):
        remaining = (day - today).days
        confirmed = all(item['confirmed'] for item in bins)
        events.append({'date': day.isoformat(), 'day': day.strftime('%A'),
                       'label': day.strftime('%a %d %b %Y'), 'days_remaining': remaining,
                       'relative': 'TODAY' if remaining == 0 else 'TOMORROW' if remaining == 1 else 'IN %d DAYS' % remaining,
                       'highlight': (remaining == 0 and settings.highlight_today) or
                                    (remaining == 1 and settings.highlight_tomorrow) or
                                    (1 < remaining <= settings.highlight_days_before),
                       'confirmed': confirmed, 'bins': bins})
    # Each row is a rolling collection week, starting today, including a
    # following-week row even when published next dates do not cover it yet.
    weeks = []
    for index in range(settings.upcoming_weeks):
        start = today + dt.timedelta(weeks=index)
        finish = start + dt.timedelta(days=6)
        weeks.append({'label': 'COMING WEEK' if index == 0 else 'FOLLOWING WEEK' if index == 1 else 'WEEK %d' % (index + 1),
                      'start': start.isoformat(), 'end': finish.isoformat(),
                      'events': [event for event in events if start.isoformat() <= event['date'] <= finish.isoformat()]})
    return {'enabled': settings.enabled, 'ready': bool(record), 'next': events[0] if events else None,
            'weeks': weeks, 'events': events, 'stale': stale, 'offline': bool(error), 'error': error,
            'fetched_at': fetched_at.isoformat() if fetched_at else None,
            'age_hours': round(age_hours, 1) if age_hours is not None else None,
            'location': address_label(record) if record and settings.show_address else str((record or {}).get('suburb') or ''),
            'has_estimates': any(not item['confirmed'] for event in events for item in event['bins']),
            'timezone': 'Australia/Brisbane', 'source': 'Brisbane City Council · CC BY 4.0'}


class BinCalendar:
    def __init__(self, config_path, logger=None, notifier=None, client=None, clock=None):
        self.config_path = Path(config_path)
        self.logger = logger or logging.getLogger(__name__)
        self.notifier = notifier
        self.client = client or CouncilClient()
        self.clock = clock or now_brisbane
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.thread = None
        self.record = None
        self.fetched_at = None
        self.error = None
        self.config_error = None
        self.last_attempt = None
        self.refreshing = False
        self.manual_requested = False
        self.retry_at = None
        self.failures = 0
        self.last_notification = None
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(self.config_path)
        try:
            self.settings = BinConfig(dict(parser['bin_calendar']) if parser.has_section('bin_calendar') else {})
        except ConfigError as error:
            self.settings = BinConfig()
            self.config_error = str(error)
            self.logger.error('[Bins] Invalid configuration; calendar disabled: %s', error)
        self._load_cache()

    @property
    def cache_path(self):
        path = Path(self.settings.cache_file).expanduser()
        return path if path.is_absolute() else self.config_path.parent / path

    def _load_cache(self):
        try:
            cache = json.loads(self.cache_path.read_text(encoding='utf-8'))
            if cache.get('version') != 1 or tuple(cache.get('identity', [])) != self.settings.identity:
                return
            record = validate_record(cache['record'])
            fetched = dt.datetime.fromisoformat(cache['fetched_at'])
            if fetched.tzinfo is None:
                raise ValueError('Cache timestamp must include a timezone')
            self.record, self.fetched_at = record, fetched
            self.last_notification = cache.get('last_notification')
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError):
            self.logger.warning('[Bins] Cache unavailable or invalid; waiting for an API response')

    def _save_cache(self):
        if not self.record or not self.fetched_at:
            return
        path = self.cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {'version': 1, 'identity': list(self.settings.identity), 'record': self.record,
                   'fetched_at': self.fetched_at.isoformat(), 'last_notification': self.last_notification}
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(path.parent), delete=False) as output:
                name = output.name
                json.dump(payload, output)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def configure(self, changes):
        with self.lock:
            merged = self.settings.to_dict()
            if set(changes) - set(SCHEMA):
                raise ConfigError('Unknown calendar settings')
            merged.update(changes)
            address_keys = ('house_number', 'street_name', 'suburb', 'unit_number')
            if (any(str(merged[key]).strip().upper() != self.settings.values[key].upper() for key in address_keys)
                    and merged['property_id'] == self.settings.property_id):
                merged['property_id'] = ''
            settings = BinConfig(merged)
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(self.config_path)
            parser['bin_calendar'] = {key: str(value).lower() if isinstance(value, bool) else str(value)
                                      for key, value in settings.to_dict().items()}
            # Preserve all other sections, including existing Telegram secrets.
            name = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(self.config_path.parent), delete=False) as output:
                    name = output.name
                    parser.write(output)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(name, self.config_path)
            finally:
                if name and os.path.exists(name):
                    os.unlink(name)
            changed_property = settings.identity != self.settings.identity
            self.settings = settings
            self.config_error = None
            self.retry_at = None
            self.failures = 0
            if changed_property:
                self.record = self.fetched_at = self.last_notification = None
                self.error = None
                self._load_cache()
            self.wake.set()
            return self.settings.to_dict()

    def lookup(self, changes):
        merged = self.settings.to_dict()
        merged.update(changes)
        merged['enabled'] = False
        merged['property_id'] = ''
        return self.client.lookup(BinConfig(merged))

    def request_refresh(self):
        with self.lock:
            now = self.clock()
            if not self.settings.enabled:
                raise ConfigError('Enable and configure the calendar first')
            if self.manual_requested or self.refreshing or (self.last_attempt and (now - self.last_attempt).total_seconds() < self.settings.manual_refresh_cooldown_seconds):
                return False
            self.manual_requested = True
            self.wake.set()
            return True

    def snapshot(self):
        with self.lock:
            view = calendar_view(self.record, self.fetched_at, self.settings, self.clock(), self.error)
            view.update(refreshing=self.refreshing, config_error=self.config_error,
                        next_refresh_at=self._due().isoformat() if self.settings.enabled else None)
            return view

    def _due(self):
        if self.manual_requested:
            return self.clock()
        if self.retry_at:
            return self.retry_at
        return next_refresh(self.fetched_at, self.settings) if self.fetched_at else self.clock()

    def refresh_once(self):
        with self.lock:
            settings = self.settings
            if not settings.enabled or self.refreshing:
                return False
            self.refreshing = True
            self.manual_requested = False
            self.last_attempt = self.clock()
            cached_id = self.record.get('property_id') if self.record else None
        try:
            query_settings = settings
            if not settings.property_id and cached_id:
                query_settings = BinConfig(dict(settings.to_dict(), property_id=cached_id))
            rows = self.client.lookup(query_settings)
            if len(rows) != 1:
                raise ValueError('No unique property match; use address lookup and select the correct property')
            record = validate_record(rows[0])
            if settings.property_id and str(record['property_id']) != settings.property_id:
                raise ValueError('Council returned a different property')
            with self.lock:
                if settings.identity != self.settings.identity:
                    return False
                self.record, self.fetched_at = record, self.clock()
                self.failures = 0
                self.retry_at = None
                self.error = None
                try:
                    self._save_cache()
                except OSError:
                    self.logger.warning('[Bins] Dates updated, but the local cache could not be saved')
            self.logger.info('[Bins] Council collection dates refreshed')
            return True
        except Exception as error:
            with self.lock:
                self.failures += 1
                delay = min(settings.retry_max_seconds, settings.retry_initial_seconds * 2 ** min(self.failures - 1, 20))
                self.retry_at = self.clock() + dt.timedelta(seconds=delay)
                self.error = 'Council data unavailable; retaining last successful dates'
            self.logger.warning('[Bins] Refresh failed (%s); cached dates retained, retry in %ss', type(error).__name__, delay)
            return False
        finally:
            with self.lock:
                self.refreshing = False

    def _notification_due(self, now):
        if not (self.settings.notify_today or self.settings.notify_tomorrow) or not self.notifier or not self.record or self.error:
            return None
        hour, minute = map(int, self.settings.notification_time.split(':'))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if self.last_notification == now.date().isoformat():
            target += dt.timedelta(days=1)
        return target

    def notify_if_due(self):
        with self.lock:
            now = self.clock()
            due = self._notification_due(now)
            if due is None or due > now or not self.record or self.error:
                return
            view = calendar_view(self.record, self.fetched_at, self.settings, now)
            lines = []
            for event in view['events']:
                enabled = (event['days_remaining'] == 0 and self.settings.notify_today) or (event['days_remaining'] == 1 and self.settings.notify_tomorrow)
                bins = [item['name'] for item in event['bins'] if item['confirmed']]
                if enabled and bins:
                    lines.append(event['relative'] + ': ' + ', '.join(bins) + ' — ' + event['label'])
            self.last_notification = now.date().isoformat()
            try:
                self._save_cache()
            except OSError:
                self.logger.warning('[Bins] Could not persist reminder state')
        if lines:
            try:
                self.notifier('\n'.join(lines))
            except Exception as error:
                self.logger.warning('[Bins] Reminder delivery failed (%s)', type(error).__name__)

    def _run(self):
        while not self.stopping.is_set():
            self.wake.clear()
            with self.lock:
                enabled = self.settings.enabled
                due = self._due() if enabled else None
            if enabled and due <= self.clock():
                self.refresh_once()
            if enabled:
                self.notify_if_due()
            with self.lock:
                now = self.clock()
                times = [self._due()] if self.settings.enabled else []
                reminder = self._notification_due(now) if self.settings.enabled else None
                if reminder is not None:
                    times.append(reminder)
                wait = min(self.settings.scheduler_check_seconds, max(0, (min(times) - now).total_seconds())) if times else None
            self.wake.wait(wait)

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name='bin-calendar', daemon=True)
            self.thread.start()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=self.settings.request_timeout_seconds)

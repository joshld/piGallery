"""Brisbane Council bin dates, a short settings list, and an offline-safe cache.

The council dataset publishes the next date for each bin colour. This module
stores that record and does not invent later collection days.
"""
import configparser
import datetime as dt
import json
import logging
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
BIN_LABELS = {'red': 'GENERAL', 'yellow': 'RECYCLING', 'green': 'GREEN'}
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
POSITIONS = (
    'top-left', 'top-center', 'top-right',
    'middle-left', 'center', 'middle-right',
    'bottom-left', 'bottom-center', 'bottom-right',
)
REQUEST_TIMEOUT_SECONDS = 15
RETRY_INITIAL_SECONDS = 900
RETRY_MAX_SECONDS = 7200
MANUAL_COOLDOWN_SECONDS = 60
CHECK_SECONDS = 60
CACHE_FILE = Path('.cache') / 'bin-calendar.json'


def spec(label, default, kind='str', group='Display', minimum=None, maximum=None, choices=None, help_text=''):
    return dict(label=label, default=default, type=kind, group=group,
                min=minimum, max=maximum, choices=choices, help=help_text)


SCHEMA = {
    'enabled': spec('Show bins on the photo frame', False, 'bool', 'Bins'),
    'house_number': spec('Street number', '', group='Address'),
    'street_name': spec('Street name', '', group='Address', help_text='For example, EXAMPLE STREET or EXAMPLE ST.'),
    'suburb': spec('Suburb', '', group='Address'),
    'unit_number': spec('Unit number (if applicable)', '', group='Address'),
    'property_id': spec('Council property ID', '', group='Address', help_text='Filled in by address lookup.'),
    'show_red': spec('General waste (red)', True, 'bool', 'Bins'),
    'show_yellow': spec('Recycling (yellow)', True, 'bool', 'Bins'),
    'show_green': spec('Garden waste (green)', False, 'bool', 'Bins', help_text='Turn on only if this property has a green bin.'),
    'red_position': spec('Where to show the red bin', 'top-center', choices=list(POSITIONS), group='Bins'),
    'yellow_position': spec('Where to show the yellow bin', 'top-center', choices=list(POSITIONS), group='Bins'),
    'green_position': spec('Where to show the green bin', 'top-center', choices=list(POSITIONS), group='Bins'),
    'icon_scale': spec('Icon size', 100, 'int', 'Bins', 50, 200, help_text='Percent of the normal size. 100 is the default.'),
    'show_days_before': spec('Days on screen before collection', 2, 'int', 'Bins', 0, 14, help_text='Icons stay up for this many days before collection, and on collection day.'),
    'refresh_days': spec('Update every (days)', 1, 'int', 'Updates', 1, 14, help_text='1 means daily.'),
    'refresh_time': spec('Update at (Brisbane time)', '06:00', 'time', 'Updates'),
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
        if self.property_id and not re.fullmatch(r'[0-9]{1,16}', self.property_id):
            raise ConfigError('Council property ID must contain digits only')
        if self.enabled and not (self.show_red or self.show_yellow or self.show_green):
            raise ConfigError('Turn on at least one bin')
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
    """Next council check. Daily uses the next clock time. Longer gaps wait that many days."""
    hour, minute = map(int, settings.refresh_time.split(':'))
    local = last_success.astimezone(BRISBANE)
    slot = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    step = dt.timedelta(days=settings.refresh_days)
    if settings.refresh_days == 1 and slot > last_success:
        return slot
    return slot + step


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


def date_label(day, today):
    remaining = (day - today).days
    if remaining == 0:
        return 'Today'
    if remaining == 1:
        return 'Tomorrow'
    return '%d %s' % (day.day, MONTHS[day.month - 1])


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
            return self.query('property_id=' + quote(settings.property_id), REQUEST_TIMEOUT_SECONDS)
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
        return self.query(' AND '.join(terms), REQUEST_TIMEOUT_SECONDS)


def calendar_view(record, fetched_at, settings, now, error=None):
    now = now.astimezone(BRISBANE)
    today = now.date()
    bins = []
    for colour, field in BIN_FIELDS.items():
        if not record or not settings.values['show_' + colour] or not record.get(field):
            continue
        day = dt.date.fromisoformat(record[field])
        remaining = (day - today).days
        bins.append({
            'colour': colour,
            'name': BIN_NAMES[colour],
            'label': BIN_LABELS[colour],
            'date': day.isoformat(),
            'when': date_label(day, today),
            'days_remaining': remaining,
            'visible': 0 <= remaining <= settings.show_days_before,
            'position': settings.values[colour + '_position'],
        })
    return {
        'enabled': settings.enabled,
        'ready': bool(record),
        'show_days_before': settings.show_days_before,
        'icon_scale': settings.icon_scale,
        'bins': bins,
        'offline': bool(error),
        'error': error,
        'fetched_at': fetched_at.isoformat() if fetched_at else None,
        'address': address_label(record) if record else '',
        'timezone': 'Australia/Brisbane',
        'source': 'Brisbane City Council',
    }


class BinCalendar:
    def __init__(self, config_path, logger=None, client=None, clock=None):
        self.config_path = Path(config_path)
        self.logger = logger or logging.getLogger(__name__)
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
        self.revision = 0
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(self.config_path)
        raw = dict(parser['bin_calendar']) if parser.has_section('bin_calendar') else {}
        # Older builds saved a long list of extra keys. Keep the address and
        # bin choices, and ignore everything this screen no longer uses.
        known = {key: value for key, value in raw.items() if key in SCHEMA}
        try:
            self.settings = BinConfig(known)
        except ConfigError as error:
            self.settings = BinConfig()
            self.config_error = str(error)
            self.logger.error('[Bins] Invalid configuration; bins hidden: %s', error)
        self._load_cache()

    @property
    def cache_path(self):
        return self.config_path.parent / CACHE_FILE

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
                   'fetched_at': self.fetched_at.isoformat()}
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
            self.revision += 1
            if changed_property:
                self.record = self.fetched_at = None
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
                raise ConfigError('Turn on bin collection and save an address first')
            if self.manual_requested or self.refreshing or (self.last_attempt and (now - self.last_attempt).total_seconds() < MANUAL_COOLDOWN_SECONDS):
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
                delay = min(RETRY_MAX_SECONDS, RETRY_INITIAL_SECONDS * 2 ** min(self.failures - 1, 20))
                self.retry_at = self.clock() + dt.timedelta(seconds=delay)
                self.error = 'Council data unavailable; retaining last successful dates'
            self.logger.warning('[Bins] Refresh failed (%s); cached dates retained, retry in %ss', type(error).__name__, delay)
            return False
        finally:
            with self.lock:
                if self.refreshing:
                    self.refreshing = False
                    self.revision += 1

    def _run(self):
        while not self.stopping.is_set():
            self.wake.clear()
            with self.lock:
                enabled = self.settings.enabled
                due = self._due() if enabled else None
            if enabled and due <= self.clock():
                self.refresh_once()
            with self.lock:
                now = self.clock()
                due = self._due() if self.settings.enabled else None
                wait = None if due is None else min(CHECK_SECONDS, max(0, (due - now).total_seconds()))
            self.wake.wait(wait)

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name='bin-calendar', daemon=True)
            self.thread.start()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=REQUEST_TIMEOUT_SECONDS)

# Brisbane bin calendar

The calendar is a rotating page inside the existing Pygame slideshow. It uses
the existing `piGallery.service`, photo controls, display schedule and Flask
web interface. No additional systemd unit or Python package is required.

## Setup and web controls

Open `http://cheesecake.local:5000/` and find **Bin Calendar → Calendar settings
and address**. Enter the street number, street and suburb, plus the unit if
applicable. Click **Look up address**, choose the exact property, select the
bin colours, enable the calendar and save. Green waste is off by default and
must only be enabled for a property with that service.

All settings below are editable in that panel. Invalid changes are rejected
before saving. Valid changes are saved atomically to the `[bin_calendar]`
section of `config.ini` and apply live. Manual INI edits take effect after a
gallery service restart. Other configuration sections, including Telegram
credentials, are preserved when saving either gallery or calendar settings.

The **Show on Pi** and **Return to photos** controls temporarily select the
calendar/photo page. Photo navigation dismisses a calendar page. Calendar time
does not consume the current photo's display timer or advance the photo queue.
Automatic pages respect the existing display-on/off schedule.

**Refresh data** queues a background request and is rate-limited. Viewing the
dashboard or calendar status never sends a Council API request.

## Official data and confidence

Source: [Brisbane City Council bin collection calendar](https://data.brisbane.qld.gov.au/explore/dataset/bin-collection-calendar/api/).

Verified API endpoint:
`https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/bin-collection-calendar/records`

The live schema provides `property_id`, `unit_number`, `house_number`,
`house_number_suffix`, `street_name`, `suburb`, `collection_day`,
`next_red_bin`, `next_yellow_bin`, and `next_green_bin`. Street lookup uses the
verified address fields; scheduled updates use the selected property ID.
Ambiguous addresses are never selected automatically.

Only the next date per bin is published in this dataset. Actual date fields
take precedence over weekday assumptions. The unrelated `date_of_collection`
field describes **large-item kerbside collection**, not wheelie-bin dates.

Later weekly/fortnightly recurrences are labelled **expected**, including on
individual bin entries where the same date mixes published and expected bins.
Their intervals are configurable. Disable estimates for published-only dates.
Estimates stop when the cache exceeds the configured age limit. Reminders use
published dates only. The renderer never moves a date merely because it falls
on a public holiday. Council states collections operate on public holidays:
https://www.brisbane.qld.gov.au/bins-waste-and-recycling/waste-and-recycling-bins/bin-collections

The dataset includes green-route dates even for properties without a green
subscription. Bin visibility is therefore an explicit household setting.

Attribution: Brisbane City Council, CC BY 4.0. The local cache contains the
last successful raw record, property identity, timestamp and reminder state.
It is written atomically; failures retain the previous successful response.
Cached/offline/old-data states are visible on both displays.

## Refresh and reliability

Default: daily at **06:00 Australia/Brisbane**. Interval mode uses the configured
hours instead. API failures use bounded exponential backoff. A configurable
clock check handles wall-clock/NTP changes without polling the Council API.
Settings changes and manual refreshes wake the same background worker.

The cache is `.cache/bin-calendar.json` by default, with a configurable JSON
filename within `.cache/`. `config.ini`, `.cache/` and `logs/` are ignored by Git.
Do not add a real address, property ID, cache or Telegram token to public source.
The street address is hidden from the physical display by default.

Telegram reminders are **disabled by default**. If enabled, they use the
existing bot and its system-alert setting, run at the configured Brisbane
time, and are attempted at most once per day. The attempt date is persisted
before delivery to avoid repeat messages after restarts; an unsuccessful
Telegram delivery is not retried that day. Network/API failures suppress bin
reminders rather than sending unverified dates.

The existing service already starts after graphical login/reboot. This
feature does not change that service, display hardware or existing shutdown
schedule. A powered-off Pi cannot refresh data until it starts again.

```sh
sudo systemctl restart piGallery.service
systemctl is-active piGallery.service
systemctl is-enabled piGallery.service
journalctl -u piGallery.service --grep='\[Bins\]' -n 40 --no-pager
curl -X POST http://127.0.0.1:5000/api/bin-calendar/refresh
```

## Tests

```sh
python -m pytest -q tests
python -m flake8 . --select=E9,F63,F7,F82
node --check static/bin-calendar.js
```

Tests cover address parameters/units, duplicate records, actual API schema,
no-green households, date/week/year transitions, Brisbane time, published and
estimated dates, cache restart/failure behaviour, retries and coalescing,
configuration persistence, opt-in reminders, page rotation and multiple screen
sizes. Actual API/property and connected-screen verification is a deployment
step; unit fixtures do not establish that a household's live schedule works.

## Configuration reference

| Setting | Default | Validation / meaning |
| --- | --- | --- |
| enabled | False | bool; Enable bin calendar |
| house_number |  | str; Street number |
| street_name |  | str; Street name |
| suburb |  | str; Suburb |
| unit_number |  | str; Unit number (if applicable) |
| property_id |  | str; Council property ID |
| show_red | True | bool; Show general waste (red) |
| show_yellow | True | bool; Show recycling (yellow) |
| show_green | False | bool; Show garden waste (green) |
| refresh_mode | daily | daily/interval; Automatic refresh mode |
| refresh_time | 06:00 | time; Daily refresh time (Brisbane) |
| refresh_interval_hours | 24 | 1–168; Interval-mode refresh frequency (hours) |
| retry_initial_seconds | 900 | 60–86400; Initial retry delay (seconds) |
| retry_max_seconds | 7200 | 60–172800; Maximum retry delay (seconds) |
| request_timeout_seconds | 15 | 3–60; API request timeout (seconds) |
| manual_refresh_cooldown_seconds | 60 | 30–3600; Manual refresh cooldown (seconds) |
| scheduler_check_seconds | 60 | 1–3600; Scheduler clock-check frequency (seconds) |
| stale_after_hours | 48 | 1–720; Mark cached data as old after (hours) |
| forecast_max_cache_age_days | 14 | 1–90; Stop estimates when cache is older than (days) |
| cache_file | .cache/bin-calendar.json | str; Local cache file |
| display_update_seconds | 30 | 1–3600; Screen update frequency (seconds) |
| web_poll_seconds | 30 | 10–3600; Web status update frequency (seconds) |
| page_interval_seconds | 300 | 30–86400; Time between calendar pages (seconds) |
| page_duration_seconds | 15 | 5–120; Calendar page duration (seconds) |
| upcoming_weeks | 2 | 1–6; Upcoming weeks to show |
| show_estimates | True | bool; Show clearly labelled regular-service estimates |
| red_interval_days | 7 | 1–31; General-waste recurrence for estimates (days) |
| yellow_interval_days | 14 | 1–31; Recycling recurrence for estimates (days) |
| green_interval_days | 14 | 1–31; Garden-waste recurrence for estimates (days) |
| show_address | False | bool; Show street address on the connected screen |
| highlight_today | True | bool; Highlight collection today |
| highlight_tomorrow | True | bool; Highlight collection tomorrow |
| highlight_days_before | 2 | 0–7; Highlight collections within this many days |
| notify_today | False | bool; Telegram reminder on collection day |
| notify_tomorrow | False | bool; Telegram reminder the day before |
| notification_time | 18:00 | time; Reminder time (Brisbane) |

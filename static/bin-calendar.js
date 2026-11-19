/* Independent controls: polling this local API never triggers a Council fetch. */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('bin-calendar-config-form');
    const fields = document.getElementById('bin-calendar-settings');
    const summary = document.getElementById('bin-calendar-summary');
    const message = document.getElementById('bin-calendar-message');
    let schema = {};
    let config = {};
    let timer = null;

    const node = (tag, text, className) => {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    };

    function announce(text, error = false) {
        message.textContent = text;
        message.className = error ? 'bin-message error' : 'bin-message';
    }

    async function api(path, values) {
        const options = values === undefined ? {} : {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(values)
        };
        const response = await fetch('/api/bin-calendar' + path, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Calendar request failed');
        return data;
    }

    function readForm() {
        const values = {};
        for (const [key, field] of Object.entries(schema).sort((a, b) => a[1].order - b[1].order)) {
            const input = form.elements.namedItem(key);
            values[key] = field.type === 'bool' ? input.checked : input.value;
        }
        return values;
    }

    function fillForm(values) {
        for (const [key, value] of Object.entries(values)) {
            const input = form.elements.namedItem(key);
            if (!input) continue;
            if (schema[key].type === 'bool') input.checked = value;
            else input.value = value;
        }
    }

    function renderSettings() {
        fields.replaceChildren();
        const groups = new Map();
        for (const [key, field] of Object.entries(schema).sort((a, b) => a[1].order - b[1].order)) {
            if (!groups.has(field.group)) {
                const group = node('fieldset');
                group.append(node('legend', field.group));
                const grid = node('div', undefined, 'bin-setting-grid');
                group.append(grid);
                fields.append(group);
                groups.set(field.group, grid);
            }
            const label = node('label', undefined, 'bin-setting');
            label.htmlFor = 'bin-setting-' + key;
            label.append(node('span', field.label));
            let input;
            if (field.choices) {
                input = node('select');
                for (const choice of field.choices) {
                    const option = node('option', choice);
                    option.value = choice;
                    input.append(option);
                }
            } else {
                input = node('input');
                input.type = field.type === 'bool' ? 'checkbox' : field.type === 'int' ? 'number' : field.type === 'time' ? 'time' : 'text';
                if (field.min !== null) input.min = field.min;
                if (field.max !== null) input.max = field.max;
                if (field.type === 'int') input.step = '1';
                if (field.type === 'str') input.maxLength = 240;
            }
            input.id = 'bin-setting-' + key;
            input.name = key;
            label.append(input);
            if (field.help) label.append(node('small', field.help));
            groups.get(field.group).append(label);
        }
        fillForm(config);
    }

    function binBadge(bin) {
        return node('span', bin.name + (bin.confirmed ? '' : ' · expected'), 'bin-badge bin-' + bin.colour);
    }

    function renderStatus(status) {
        summary.replaceChildren();
        if (status.config_error) summary.append(node('p', status.config_error, 'bin-message error'));
        if (!status.enabled) {
            summary.append(node('h3', 'Calendar disabled'));
            summary.append(node('p', 'Open settings, look up your address, choose your bins and enable the calendar.'));
        } else if (!status.next) {
            summary.append(node('h3', status.ready ? 'No verified upcoming dates' : 'Waiting for Council data'));
        } else {
            const next = node('div', undefined, 'bin-next');
            next.append(node('p', status.next.confirmed ? status.next.relative : 'EXPECTED · ' + status.next.relative,
                             status.next.highlight && status.next.confirmed ? 'bin-countdown urgent' : 'bin-countdown'));
            next.append(node('h3', status.next.day + ' · ' + status.next.label));
            const badges = node('div', undefined, 'bin-badges');
            status.next.bins.forEach(bin => badges.append(binBadge(bin)));
            next.append(badges);
            summary.append(next);
            for (const week of status.weeks) {
                const row = node('div', undefined, 'bin-week');
                row.append(node('strong', week.label.replaceAll('_', ' ')));
                if (!week.events.length) row.append(node('span', 'Dates not yet published'));
                for (const event of week.events) {
                    const line = node('div', undefined, 'bin-week-event');
                    line.append(node('span', event.label));
                    event.bins.forEach(bin => line.append(binBadge(bin)));
                    row.append(line);
                }
                summary.append(row);
            }
        }
        if (status.offline || status.stale) {
            summary.append(node('p', status.offline ? 'Offline: showing the last successful Council data.' : 'Cached Council data is old.', 'bin-warning'));
        }
        if (status.fetched_at) {
            const updated = new Intl.DateTimeFormat('en-AU', {timeZone: 'Australia/Brisbane', dateStyle: 'medium', timeStyle: 'short'}).format(new Date(status.fetched_at));
            summary.append(node('small', 'Last successful refresh: ' + updated + ' (Brisbane)'));
        }
        document.getElementById('bin-show-page').disabled = !status.enabled;
        document.getElementById('bin-refresh-data').disabled = !status.enabled || status.refreshing;
    }

    async function poll() {
        clearTimeout(timer);
        try { renderStatus(await api('')); }
        catch (error) { announce(error.message, true); }
        timer = setTimeout(poll, config.web_poll_seconds * 1000);
    }

    form.addEventListener('input', event => {
        if (['house_number', 'street_name', 'suburb', 'unit_number'].includes(event.target.name)) {
            form.elements.namedItem('property_id').value = '';
        }
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        try {
            const data = await api('/config', readForm());
            config = data.config;
            fillForm(config);
            renderStatus(data.status);
            announce('Saved on the Pi and applied live. Settings will also load after a restart.');
            poll();
        } catch (error) { announce(error.message, true); }
    });

    document.getElementById('bin-lookup-address').addEventListener('click', async () => {
        const results = document.getElementById('bin-address-results');
        results.replaceChildren();
        const values = readForm();
        const address = Object.fromEntries(['house_number', 'street_name', 'suburb', 'unit_number'].map(key => [key, values[key]]));
        announce('Looking up the address with Brisbane City Council...');
        try {
            const data = await api('/lookup', address);
            announce(data.properties.length ? 'Select the matching property, then save the calendar settings.' : 'No matching property. Check the street number, street spelling and suburb.');
            for (const property of data.properties) {
                const button = node('button', 'Use ' + property.label, 'btn-secondary');
                button.type = 'button';
                button.addEventListener('click', () => {
                    fillForm(Object.assign({}, property, {enabled: true}));
                    results.replaceChildren(node('p', 'Selected: ' + property.label + '. Save to enable the calendar.'));
                });
                results.append(button);
            }
        } catch (error) { announce(error.message, true); }
    });

    document.getElementById('bin-refresh-data').addEventListener('click', async () => {
        try { await api('/refresh', {}); announce('Refresh queued. Cached dates remain available.'); poll(); }
        catch (error) { announce(error.message, true); }
    });
    for (const [id, show] of [['bin-show-page', true], ['bin-hide-page', false]]) {
        document.getElementById(id).addEventListener('click', async () => {
            try { await api('/display', {show}); announce(show ? 'Calendar page requested on the Pi.' : 'Returning to photos.'); }
            catch (error) { announce(error.message, true); }
        });
    }

    api('/config').then(data => {
        schema = data.schema;
        config = data.config;
        renderSettings();
        renderStatus(data.status);
        poll();
    }).catch(error => announce(error.message, true));
});

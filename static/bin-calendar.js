/* Settings for the bin icons. Reading status never calls the council API. */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('bin-calendar-config-form');
    const message = document.getElementById('bin-calendar-message');
    const statusLine = document.getElementById('bin-calendar-status');
    const preview = document.getElementById('bin-screen-preview');
    if (!form || !preview) return;

    const bins = [
        {show: 'show_red', position: 'red_position', colour: 'red', label: 'GENERAL'},
        {show: 'show_yellow', position: 'yellow_position', colour: 'yellow', label: 'RECYCLING'},
        {show: 'show_green', position: 'green_position', colour: 'green', label: 'GREEN'}
    ];
    const fields = ['enabled', 'house_number', 'street_name', 'suburb', 'unit_number', 'property_id',
        'show_red', 'show_yellow', 'show_green', 'red_position', 'yellow_position', 'green_position',
        'show_days_before', 'refresh_days', 'refresh_time'];
    let dates = {};
    let showing = {};
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
        const data = await response.json().catch(() => { throw new Error('Bin settings are unavailable right now.'); });
        if (!response.ok) throw new Error(data.error || 'Calendar request failed');
        return data;
    }

    function readForm() {
        const values = {};
        for (const key of fields) {
            const input = form.elements.namedItem(key);
            values[key] = input.type === 'checkbox' ? input.checked : input.value;
        }
        return values;
    }

    function fillForm(values) {
        for (const [key, value] of Object.entries(values)) {
            const input = form.elements.namedItem(key);
            if (!input) continue;
            if (input.type === 'checkbox') input.checked = Boolean(value);
            else input.value = value;
        }
    }

    function glyph(colour) {
        const icon = node('div', undefined, 'bin-glyph bin-' + colour);
        icon.append(node('span', undefined, 'handle'), node('span', undefined, 'lid'), node('span', undefined, 'body'));
        icon.append(node('span', undefined, 'wheel left'), node('span', undefined, 'wheel right'));
        return icon;
    }

    function renderPreview() {
        preview.replaceChildren();
        const groups = new Map();
        for (const bin of bins) {
            if (!form.elements.namedItem(bin.show).checked) continue;
            const position = form.elements.namedItem(bin.position).value || 'top-center';
            if (!groups.has(position)) groups.set(position, []);
            groups.get(position).push(bin);
        }
        if (!groups.size) {
            preview.append(node('p', 'Turn on at least one bin to show it on the frame.', 'bin-preview-empty'));
            return;
        }
        for (const [position, chosen] of groups) {
            const group = node('div', undefined, 'bin-group');
            group.dataset.pos = position;
            const tiles = node('div', undefined, 'bin-tiles');
            for (const bin of chosen) {
                const tile = node('div', undefined, 'bin-tile' + (showing[bin.colour] === false ? ' waiting' : ''));
                tile.append(glyph(bin.colour));
                tile.append(node('span', bin.label, 'bin-name'));
                tile.append(node('strong', dates[bin.colour] || '—', 'bin-when'));
                tiles.append(tile);
            }
            group.append(tiles);
            preview.append(group);
        }
    }

    function remember(status) {
        dates = {};
        showing = {};
        for (const bin of status.bins || []) {
            dates[bin.colour] = bin.when;
            showing[bin.colour] = bin.visible;
        }
        const onFrame = (status.bins || []).filter(bin => bin.visible).map(bin => bin.name);
        const parts = [];
        if (status.config_error) parts.push(status.config_error);
        else if (!status.enabled) parts.push('Bins stay off until you save an address and turn collection on.');
        else if (!status.ready) parts.push('Saved. Dates appear after the first council update.');
        else if (onFrame.length) parts.push('On the frame now: ' + onFrame.join(', '));
        else if ((status.bins || []).length) parts.push('Hidden until ' + status.show_days_before + ' days before collection. They then stay up through collection day.');
        if (status.offline) parts.push('Showing saved dates. The latest council update did not succeed.');
        else if (status.fetched_at && !status.config_error) {
            const updated = new Intl.DateTimeFormat('en-AU', {
                timeZone: 'Australia/Brisbane', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit'
            }).format(new Date(status.fetched_at));
            parts.push('Updated ' + updated + ' Brisbane time');
        }
        if (status.address) parts.push(status.address);
        statusLine.textContent = parts.join(' · ');
        document.getElementById('bin-refresh-data').disabled = !status.enabled || status.refreshing;
        renderPreview();
    }

    async function poll() {
        clearTimeout(timer);
        try { remember(await api('')); }
        catch (error) { announce(error.message, true); }
        timer = setTimeout(poll, 30000);
    }

    form.addEventListener('input', event => {
        if (['house_number', 'street_name', 'suburb', 'unit_number'].includes(event.target.name)) {
            form.elements.namedItem('property_id').value = '';
        }
        renderPreview();
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const values = readForm();
        if (values.enabled && !values.property_id && !(values.house_number && values.street_name && values.suburb)) {
            announce('Enter a street number, street and suburb, then look up the address.', true);
            return;
        }
        try {
            const data = await api('/config', values);
            fillForm(data.config);
            remember(data.status);
            announce('Saved. The frame will use these icons.');
            poll();
        } catch (error) { announce(error.message, true); }
    });

    document.getElementById('bin-lookup-address').addEventListener('click', async () => {
        const results = document.getElementById('bin-address-results');
        results.replaceChildren();
        const values = readForm();
        const address = Object.fromEntries(['house_number', 'street_name', 'suburb', 'unit_number'].map(key => [key, values[key]]));
        announce('Looking up that address with Brisbane City Council...');
        try {
            const data = await api('/lookup', address);
            if (!data.properties.length) {
                announce('No matching property. Check the street number, street and suburb.', true);
                return;
            }
            announce('Choose the matching property, then save.');
            for (const property of data.properties) {
                const button = node('button', property.label, 'btn-secondary');
                button.type = 'button';
                button.addEventListener('click', () => {
                    fillForm(property);
                    results.replaceChildren(node('p', 'Selected ' + property.label + '. Save to keep it.'));
                });
                results.append(button);
            }
        } catch (error) { announce(error.message, true); }
    });

    document.getElementById('bin-refresh-data').addEventListener('click', async () => {
        try {
            await api('/refresh', {});
            announce('Update queued. Saved dates stay on the frame until the new ones arrive.');
            poll();
        } catch (error) { announce(error.message, true); }
    });

    renderPreview();
    api('/config').then(data => {
        fillForm(data.config);
        remember(data.status);
        poll();
    }).catch(error => {
        announce(error.message, true);
        statusLine.textContent = 'The preview above still works. Dates load when this page is opened from the frame.';
    });
});

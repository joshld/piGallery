"""Bin-calendar routes for the existing piGallery control application."""
from flask import jsonify, request

from bin_calendar import BinConfig, ConfigError, SCHEMA, address_label


def register_bin_routes(app, slideshow):
    def calendar():
        controller = getattr(slideshow, 'bin_calendar', None)
        if controller is None:
            raise ConfigError('Bin calendar is not initialized')
        return controller

    @app.route('/api/bin-calendar')
    def bin_calendar_status():
        try:
            return jsonify(calendar().snapshot())
        except ConfigError as error:
            return jsonify(error=str(error)), 503

    @app.route('/api/bin-calendar/config', methods=['GET', 'POST'])
    def bin_calendar_config():
        try:
            controller = calendar()
            if request.method == 'POST':
                changes = request.get_json(silent=True)
                if not isinstance(changes, dict):
                    raise ConfigError('Settings must be a JSON object')
                controller.configure(changes)
                slideshow.force_redraw = True
            return jsonify(config=controller.settings.to_dict(), schema=SCHEMA, status=controller.snapshot())
        except ConfigError as error:
            return jsonify(error=str(error)), 400
        except OSError:
            return jsonify(error='Could not save the configuration file'), 500

    @app.route('/api/bin-calendar/lookup', methods=['POST'])
    def bin_calendar_lookup():
        try:
            values = request.get_json(silent=True)
            if not isinstance(values, dict):
                raise ConfigError('Enter a street number, street and suburb')
            allowed = ('house_number', 'street_name', 'suburb', 'unit_number')
            if set(values) - set(allowed):
                raise ConfigError('Unexpected address field')
            rows = calendar().lookup(values)
            return jsonify(properties=[{'property_id': str(row['property_id']), 'label': address_label(row),
                                        'house_number': str(row.get('house_number') or '') + str(row.get('house_number_suffix') or ''),
                                        'street_name': row.get('street_name') or '', 'suburb': row.get('suburb') or '',
                                        'unit_number': row.get('unit_number') or ''} for row in rows])
        except ConfigError as error:
            return jsonify(error=str(error)), 400
        except Exception:
            # Requests' exception strings can contain the private address URL.
            return jsonify(error='Council address lookup is unavailable. Check the address or retry later.'), 502

    @app.route('/api/bin-calendar/refresh', methods=['POST'])
    def bin_calendar_refresh():
        try:
            if not calendar().request_refresh():
                return jsonify(error='A refresh was just requested. Wait a minute, then try again.'), 429
            return jsonify(status='queued'), 202
        except ConfigError as error:
            return jsonify(error=str(error)), 400

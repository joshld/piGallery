# Web Interface Setup Guide

## Installation

The web interface has been integrated into your gallery.py script. Follow these steps to get it running:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- flask
- flask-cors
- And other existing dependencies (pygame, requests, geopy)

### 2. Start the Gallery

```bash
python gallery.py
```

When the script starts, you should see:
```
[Web] Starting web server on http://0.0.0.0:5000
[Startup] Web interface available at http://0.0.0.0:5000
```

### 3. Access the Web Interface

#### On the Raspberry Pi itself:
```
http://localhost:5000
```

#### From another device on the same network:
```
http://raspberrypi.local:5000
```
Or use the Pi's IP address:
```
http://192.168.1.xxx:5000
```

To find your Pi's IP address:
```bash
hostname -I
```

### 4. Using the Web Interface

The web interface provides:

#### Status Display
- Current time and date
- Temperature and weather
- Current image info
- Playback state (playing/paused)

#### Playback Controls
- **Previous/Next** - Navigate through images
- **Pause/Resume** - Stop/start the slideshow

#### Display Control
- **Turn On** - Force display on
- **Turn Off** - Force display off  
- **Auto Mode** - Follow the configured schedule

#### Upload Photos
- Drag and drop images directly to the upload area
- Or click to browse and select files
- Supports JPG, JPEG, and PNG

#### Display Settings
- Toggle time display on/off
- Toggle date display on/off
- Toggle temperature display on/off
- Toggle weather display on/off
- Toggle filename display on/off
- **Save Settings** - Persist changes to config.ini

## Troubleshooting

### Can't Access Web Interface

1. **Check if Flask is running:**
   Look for "[Web] Starting web server..." in the console output

2. **Check firewall:**
   ```bash
   sudo ufw allow 5000
   ```

3. **Find correct IP address:**
   ```bash
   hostname -I
   ```

4. **Try different URLs:**
   - http://localhost:5000 (on Pi)
   - http://raspberrypi.local:5000 (mDNS)
   - http://[IP_ADDRESS]:5000 (direct IP)

### Web Interface Loads but Doesn't Work

1. **Check browser console** (F12) for errors
2. **Verify slideshow is running** - you should see status updates
3. **Check Python console** for API errors

### Upload Not Working

1. **Verify images directory exists** and has write permissions
2. **Check file format** - only JPG, JPEG, PNG supported
3. **File size** - very large files may time out

## API Reference

If you want to integrate with other tools:

### GET /api/status
Returns current slideshow status including image, weather, time, etc.

### POST /api/next
Skip to next image.

### POST /api/prev
Go to previous image.

### POST /api/pause
Toggle pause state.

### POST /api/display
Control display power.
Body: `{"action": "on"}` or `{"action": "off"}` or `{"action": "auto"}`

### POST /api/upload
Upload new image.
Form data with 'file' field.

### GET /api/settings
Get current settings.

### POST /api/settings
Update settings.
Body: Settings JSON with optional `"save_to_config": true`

## Security Notes

- The web interface runs on your local network only
- No authentication is currently implemented
- Don't expose port 5000 to the internet without proper security
- Consider using a reverse proxy (nginx) with authentication for remote access

## Future Enhancements

Potential features to add:
- Authentication/login
- HTTPS support
- Delete images via web
- Image favorites/ratings
- Slideshow history
- Multiple slideshows/playlists
- Integration with cloud storage (Google Photos, etc.)

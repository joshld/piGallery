# Web Interface Setup Guide

## Installation

The web interface has been integrated into your gallery.py script. Follow these steps to get it running:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- flask (web server)
- flask-cors (cross-origin resource sharing)
- pygame (graphics and display)
- requests (HTTP requests for weather)
- geopy (location services)
- psutil (system monitoring)
- Pillow (image processing)
- piexif (EXIF metadata handling)

### 2. Verify Setup (Recommended)

Before starting, run the comprehensive setup verification:

```bash
python test_setup.py
```

This will check:
- Python version and environment
- All required dependencies
- File permissions and structure
- Port availability
- Network configuration

### 3. Start the Gallery

```bash
python gallery.py
```

When the script starts successfully, you should see:
```
[Web] Starting web server on http://0.0.0.0:5000
[Startup] Web interface available at http://0.0.0.0:5000
```

### 4. Access the Web Interface

#### On the local computer:
```
http://localhost:5000
```

#### From another device on the same network:
**Via hostname:**
```
http://[HOSTNAME]:5000
```
(e.g., `http://COMPUTER-NAME:5000` on Windows, `http://raspberrypi.local:5000` on Raspberry Pi)

**Via IP address:**
```
http://[IP_ADDRESS]:5000
```

#### Finding your computer's IP address:
**Windows:**
```cmd
ipconfig
```

**Linux/Raspberry Pi:**
```bash
hostname -I
```

**macOS:**
```bash
ipconfig getifaddr en0
```

### 5. Using the Web Interface

The web interface provides:

#### Status Display
- Current time and date
- Temperature and weather
- Current image info and caption
- Playback state (playing/paused)
- System health (CPU, memory, temperature)
- Error log access

#### Playback Controls
- **Previous/Next** - Navigate through images
- **Pause/Resume** - Stop/start the slideshow

#### Display Control
- **Turn On** - Force display on
- **Turn Off** - Force display off
- **Auto Mode** - Follow the configured schedule

#### Image Management
- **View Image Details** - Full resolution and thumbnail views
- **Edit Captions** - Set/edit image captions via metadata
- **Caption Display** - Toggle caption overlay on/off

#### System Control
- **Shutdown System** - Safe system shutdown with countdown
- **Restart System** - Remote restart capability
- **Cancel Operations** - Stop pending shutdown/restart

#### Upload Photos
- Drag and drop images directly to the upload area
- Or click to browse and select files
- Supports JPG, JPEG, and PNG
- Upload progress and status feedback

#### Display Settings
- Toggle time, date, temperature, weather, filename display
- Toggle caption display
- Adjust display timing and behavior
- **Live Preview** - See changes before saving
- **Save Settings** - Persist changes to config.ini

#### Theme Selection
- Multiple color themes (light, dark, custom)
- Theme persistence across sessions

## Troubleshooting

### Can't Access Web Interface

1. **Run setup verification:**
   ```bash
   python test_setup.py
   ```
   This will check all requirements and provide specific guidance.

2. **Check if Flask is running:**
   Look for "[Web] Starting web server..." in the console output

3. **Check firewall settings:**
   **Windows:** Allow port 5000 in Windows Firewall
   **Linux/Raspberry Pi:** `sudo ufw allow 5000`
   **macOS:** Usually no firewall blocking local ports

4. **Find correct IP address:**
   **Windows:** `ipconfig`
   **Linux/Raspberry Pi:** `hostname -I`
   **macOS:** `ipconfig getifaddr en0`

5. **Try different URLs:**
   - `http://localhost:5000` (on the same computer)
   - `http://[HOSTNAME]:5000` (via computer name)
   - `http://[IP_ADDRESS]:5000` (via IP address)

6. **Check port availability:**
   The setup verification script will warn if port 5000 is already in use.

### Web Interface Loads but Doesn't Work

1. **Check browser console** (F12) for errors
2. **Verify slideshow is running** - you should see status updates
3. **Check Python console** for API errors

### Upload Not Working

1. **Verify images directory exists** and has write permissions
2. **Check file format** - only JPG, JPEG, PNG supported
3. **File size** - very large files may time out

## API Reference

The web interface provides 18 REST API endpoints for integration:

### Status & Information
- `GET /api/status` - Current slideshow status (image, weather, system health)
- `GET /api/logs` - Error log entries for debugging

### Playback Control
- `POST /api/next` - Skip to next image
- `POST /api/prev` - Go to previous image
- `POST /api/pause` - Toggle pause/play state

### Image Management
- `GET /api/image/preview` - Current image thumbnail
- `GET /api/image/full` - Current image at full resolution
- `GET /api/image/caption` - Get current image caption
- `POST /api/image/caption` - Set/edit image caption

### System Control
- `POST /api/system/shutdown` - Shutdown system safely
- `POST /api/system/restart` - Restart system
- `POST /api/system/cancel` - Cancel pending shutdown/restart

### Display & Settings
- `POST /api/display` - Control display power
  - Body: `{"action": "on|off|auto"}`
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings
  - Body: Settings JSON, optional `"save_to_config": true`

### File Operations
- `POST /api/upload` - Upload new image
  - Form data with 'file' field (JPG, JPEG, PNG)
- `GET /api/directories` - List available directories

### Usage Examples
```bash
# Get current status
curl http://localhost:5000/api/status

# Skip to next image
curl -X POST http://localhost:5000/api/next

# Upload an image
curl -F "file=@image.jpg" http://localhost:5000/api/upload
```

## Security Notes

- The web interface runs on your local network only
- No authentication is currently implemented
- Don't expose port 5000 to the internet without proper security
- Consider using a reverse proxy (nginx) with authentication for remote access

## Recent Enhancements ✅

**Completed Features:**
- ✅ **Cross-platform support** (Windows, Linux, macOS, Raspberry Pi)
- ✅ **Image caption editing** (set/edit captions via web UI)
- ✅ **System control** (remote shutdown/restart/cancel)
- ✅ **Enhanced error handling** (comprehensive logging and debugging)
- ✅ **Advanced image management** (thumbnails, full-size viewing)
- ✅ **Performance monitoring** (real-time system health)
- ✅ **Automatic shutdown** (power management with smart scheduling)
- ✅ **Theme support** (multiple color schemes)

## Future Enhancements

**High Priority:**
- Delete uploaded images via web UI
- Image sorting and display order options
- Dark mode theme implementation
- Image transition effects (fade, slide)

**Medium Priority:**
- Authentication and security features
- HTTPS support for secure remote access
- Image favorites and ratings system
- Slideshow history and statistics

**Advanced Features:**
- Video file support
- Cloud storage integration (Google Photos, Dropbox)
- Mobile app companion
- Advanced playlist management
- Face detection and organization

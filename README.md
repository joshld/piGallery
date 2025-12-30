
# piGallery
Displays a slideshow of photos on a Raspberry Pi, Windows PC, or any computer with a connected display.

## Features

- 📸 Automatic slideshow with configurable timing
- 🌡️ Weather and time display
- 🌓 Auto display on/off scheduling (with optional automatic shutdown)
- 🎮 **Web interface for remote control**
- 📱 Mobile-friendly control panel
- ⚙️ Live settings adjustment
- 📤 Upload photos via browser
- ⏯️ Pause/resume playback

## Setup Instructions

### 1. Clone or Download the Repository
Download or clone this repository to your local machine.

### 2. Install Python (if not already installed)
Ensure you have Python 3.7 or newer installed. You can download it from [python.org](https://www.python.org/downloads/).

### 3. Install Required Modules
Open a terminal or command prompt in the project directory and run:

```sh
pip install -r requirements.txt
```

This will install the following required modules:
- pygame (graphics and display)
- requests (HTTP requests for weather)
- geopy (location services)
- flask (web server)
- flask-cors (cross-origin resource sharing)
- psutil (system monitoring)
- Pillow (image processing)
- piexif (EXIF metadata handling)

### 4. Prepare Your Images
Place your images in the folder specified by the `images_directory` in `config.ini`. You can change this path as needed.

### 5. Run the Slideshow
To start the slideshow, run:

```sh
python gallery.py
```

You can also specify the delay between images (in seconds):

```sh
python gallery.py --delay 15
```

### 6. Access Web Interface

Once the gallery is running, you can control it from any device on your network:

**Find your computer's IP address:**
- **Windows:** Open Command Prompt and run `ipconfig` - look for IPv4 Address
- **Linux/Raspberry Pi:** Run `hostname -I` in terminal
- **macOS:** Run `ipconfig getifaddr en0` in terminal

**Access URLs:**
- **Local computer:** `http://localhost:5000`
- **Via hostname:** `http://[HOSTNAME]:5000` (e.g., `http://COMPUTER-NAME:5000`)
- **Via IP address:** `http://[YOUR_IP_ADDRESS]:5000`
- **Raspberry Pi (mDNS):** `http://raspberrypi.local:5000`

**From any device:**
- Open the URL above in any browser (Chrome, Firefox, Safari, Edge)
- No app installation needed!

**Web Interface Features:**
- ⏭️ Next/Previous image controls
- ⏸️ Pause/Resume slideshow
- 💡 Turn display on/off manually
- 📊 View current status (time, weather, image)
- ⚙️ Toggle display elements (time, date, weather, etc.)
- 📤 Upload photos directly from your device
- 💾 Save settings to config file

### 7. Configuration

The first time you run the script, it will create a `config.ini` file with default settings. Edit this file to customize:

- `images_directory` - Path to your photos
- `delay_seconds` - Time between images (default: 10)
- `display_off_time` - When to turn display off (default: 23:00)
- `display_on_time` - When to turn display on (default: 05:00)
- `shutdown_on_display_off` - Automatically shutdown Pi at off-time (default: true for power savings)
- `shutdown_countdown_seconds` - Countdown before shutdown (default: 10)
- `location_city_suburb` - Location for weather data
- Display toggles (show_time, show_date, show_temperature, etc.)

### 8. Telegram Notifications (Optional)

piGallery can send notifications to a Telegram channel or chat. This is useful for remote monitoring and alerts.

#### Setup Steps:

1. **Create a Telegram Bot:**
   - Open Telegram and search for [@BotFather](https://t.me/BotFather)
   - Send `/newbot` and follow the instructions
   - Save the bot token you receive (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Get Your Chat ID:**
   
   **For a Private Channel:**
   - Create a private channel in Telegram
   - Add your bot as an administrator (Channel Settings → Administrators → Add Administrator)
   - Give the bot permission to post messages
   - Forward a message from the channel to [@userinfobot](https://t.me/userinfobot) to get the chat ID
   - Or send a message to the channel, then visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":-1001234567890}` (negative number for channels/groups)

   **For a Personal Chat:**
   - Start a chat with your bot
   - Send any message to the bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789}` (positive number for personal chats)

   **For a Group:**
   - Add your bot to the group
   - Make it an administrator (recommended)
   - Get the chat ID the same way (will be negative)

3. **Configure in config.ini:**
   ```ini
   [telegram]
   bot_token = YOUR_BOT_TOKEN_HERE
   chat_id = YOUR_CHAT_ID_HERE
   notify_startup = true
   notify_shutdown = true
   notify_errors = true
   notify_uploads = true
   notify_image_changes = false
   notify_settings_changes = false
   notify_system_alerts = true
   image_notify_frequency = 10
   ```

4. **Notification Types:**
   - **Startup/Shutdown** - When the gallery starts or stops
   - **Errors** - Immediate alerts for critical errors
   - **Uploads** - When new images are uploaded via web interface
   - **Image Changes** - When slideshow advances (configurable frequency)
   - **Settings Changes** - When settings are modified via web interface
   - **System Alerts** - Low memory, high CPU, high temperature warnings

5. **Test:**
   - Start the gallery: `python gallery.py`
   - You should receive a test message: "🤖 piGallery Telegram notifications enabled!"
   - If you don't receive it, check:
     - Bot token is correct
     - Chat ID is correct
     - Bot is added as admin to channel/group (if applicable)
     - Bot has permission to send messages

**Note:** Leave `bot_token` or `chat_id` empty to disable Telegram notifications.

### 9. Code Quality: Linting and Type Checking

You can use `flake8` for code style/linting and `mypy` for type checking.

#### Install flake8 and mypy
```sh
pip install flake8 mypy types-requests
```

#### Run flake8 (style/lint check)
```sh
python3 -m flake8 gallery.py
```

#### Run mypy (type check)
```sh
python3 -m mypy gallery.py
```

#### (Optional) VS Code Integration
- Install the "Python" extension in VS Code for built-in linting and type checking support.
- You can also install the "Flake8" and "Mypy" extensions for enhanced integration.

## Web API Endpoints

If you want to integrate with other systems, the following API endpoints are available:

**Slideshow Control:**
- `GET /api/status` - Get current slideshow status
- `POST /api/next` - Skip to next image
- `POST /api/prev` - Go to previous image
- `POST /api/pause` - Toggle pause state
- `POST /api/display` - Control display (body: `{"action": "on|off|auto"}`)

**Image Management:**
- `GET /api/image/preview` - Get current image thumbnail
- `GET /api/image/full` - Get current image at full resolution
- `GET /api/image/caption` - Get caption from current image metadata
- `POST /api/image/caption` - Set caption in current image metadata

**System Control:**
- `POST /api/system/shutdown` - Shutdown the system
- `POST /api/system/restart` - Restart the system
- `POST /api/system/cancel` - Cancel pending shutdown/restart

**Settings & Upload:**
- `POST /api/upload` - Upload new image (multipart form data)
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings (body: settings JSON)

**Utilities:**
- `GET /api/logs` - Get system logs
- `GET /api/directories` - List directories for folder selection

## Quick Reference

### Access URLs
- **Local computer:** `http://localhost:5000`
- **Via hostname:** `http://[HOSTNAME]:5000` (e.g., `http://COMPUTER-NAME:5000`)
- **Via IP address:** `http://[YOUR_IP]:5000`
- **Raspberry Pi (mDNS):** `http://raspberrypi.local:5000`

**Find your hostname:**
- **Windows:** Run `hostname` in Command Prompt
- **Linux/Raspberry Pi:** Run `hostname` in terminal
- **macOS:** Run `hostname` in terminal

### Web Interface Features
- **Playback:** Previous, Next, Pause/Resume
- **Display Control:** Turn On, Turn Off, Auto Mode
- **Upload:** Drag & drop or click to upload (JPG, JPEG, PNG)
- **Settings:** Toggle time, date, temperature, weather, filename display
- **Save:** Persist changes to config.ini

### Keyboard Shortcuts (on Pi)
- `ESC` - Quit application
- `RIGHT →` - Next image
- `LEFT ←` - Previous image

### Configuration Options
Edit `config.ini`:
- `images_directory` - Photo folder path
- `delay_seconds` - Time per image
- `display_off_time` - When to turn display off (e.g., 23:00)
- `display_on_time` - When to turn display on (e.g., 05:00)
- `shutdown_on_display_off` - Auto shutdown Pi at off-time (true/false)
- `shutdown_countdown_seconds` - Countdown before shutdown (default: 10)
- `location_city_suburb` - Weather location

**Note on Automatic Shutdown:**
- When enabled, the Pi will shut down when `display_off_time` is reached
- A countdown timer is displayed before shutdown
- Telegram notification is sent before shutdown (if configured)
- **Enabled by default** to save power during off-hours
- Disable if you need 24/7 remote access via web interface
- **Power savings**: ~5-6W × 8 hours = 40-48Wh per day (~$15-20/year)

### Troubleshooting
**Can't access web interface?**
- Run verification: `python test_setup.py`
- **Windows:** Allow port 5000 in Windows Firewall (or disable firewall temporarily for testing)
- **Linux/Raspberry Pi:** Allow firewall: `sudo ufw allow 5000`
- Find your IP: `ipconfig` (Windows) or `hostname -I` (Linux/Pi)

**Web loads but doesn't work?**
- Check browser console (F12) for errors
- Check Python console for errors
- Verify slideshow is running

**Upload not working?**
- Check directory permissions
- Verify file format (JPG/PNG only)
- Check file size (large files may timeout)

### Performance
- **Memory:** ~129 MB total (+10 MB for web server)
- **CPU:** ~8% idle
- **Compatible:** Raspberry Pi 3 B+ (1GB RAM) and higher

### Browser Compatibility
✓ Chrome/Chromium | ✓ Firefox | ✓ Safari | ✓ Edge | ✓ Mobile browsers

### Pro Tips
- Bookmark the URL on your phone home screen for quick access
- Use drag-and-drop for fast photo uploads
- Toggle settings to reduce screen clutter
- Pause during parties for manual control
- Auto mode follows your schedule automatically

### 9. Power Management & Auto-Wake Solutions

When `shutdown_on_display_off = true` (recommended for power savings), the Pi will shut down at the configured off-time. To automatically power it back on, you have several options:

#### Option 1: Smart Plug with Timer (Recommended - Easy & Cheap)
**Cost:** $10-25 | **Difficulty:** Easy
- Use a WiFi/Bluetooth smart plug with scheduling
- Set it to turn off at display_off_time + 15 minutes (after shutdown completes)
- Set it to turn on at display_on_time - 5 minutes (before display should turn on)
- **Examples:** TP-Link Kasa, Wemo, Sonoff
- **Pros:** No hardware changes, works with any Pi, remote control via app
- **Cons:** Requires WiFi/hub, costs $10-25

#### Option 2: Mechanical Timer Outlet (Budget Option)
**Cost:** $5-10 | **Difficulty:** Easy  
- Simple 24-hour mechanical timer plug
- Set on/off times with physical pins/dial
- **Pros:** Very cheap, no WiFi needed, reliable
- **Cons:** No remote control, manual adjustment needed for schedule changes
- **Examples:** GE 24-Hour Mechanical Timer

#### Option 3: RTC (Real-Time Clock) HAT + Wake Alarm (Advanced)
**Cost:** $10-20 | **Difficulty:** Moderate
- Install an RTC HAT (e.g., DS3231, PCF8523)
- Configure wake alarm in software
- Pi can wake itself at scheduled time
- **Pros:** No external hardware, precise timing
- **Cons:** Requires hardware installation, software configuration, not all Pi models supported
- **Setup guide:** https://learn.adafruit.com/adding-a-real-time-clock-to-raspberry-pi

#### Option 4: Keep Pi Running (No Power Savings)
**Cost:** $0 | **Power cost:** ~$30-40/year
- Set `shutdown_on_display_off = false`
- Display turns off but Pi stays on
- **Pros:** 24/7 remote access, no wake-up hardware needed
- **Cons:** Wastes power, higher electricity bill

#### Recommended Setup for Maximum Power Savings:
1. Enable automatic shutdown: `shutdown_on_display_off = true`
2. Use a smart plug or mechanical timer
3. Set timer to:
   - **Turn OFF:** 23:15 (15 min after shutdown completes at 23:00)
   - **Turn ON:** 04:55 (5 min before display_on_time at 05:00)
4. Pi boots automatically, gallery starts via systemd service
5. **Total savings:** ~$15-20/year in electricity (pays for timer in 6-12 months)

#### Alternative: Partial Power Savings (Keep Remote Access)
If you need remote access during off-hours but still want some power savings:
- Set `shutdown_on_display_off = false`
- Display powers off via HDMI (saves ~2-3W on the display side)
- Pi stays on consuming ~2-3W
- **Savings:** ~$10-15/year (less but still worthwhile)
- **Benefit:** Full remote access 24/7 for uploads, settings, monitoring

### 10. Notes
- **Cross-platform:** Works on Windows, macOS, Linux, and Raspberry Pi
- **Fullscreen display:** Script hides mouse cursor for clean presentation
- **Weather & time:** Displays current conditions and clock on screen
- **Platform differences:** Some features (like display power control) work best on Raspberry Pi but are gracefully handled on other platforms
- **Web interface:** Accessible on port 5000 by default
- **Image organization:** Supports subfolders - recursively scans all directories
- **File formats:** Supports JPG, JPEG, and PNG images


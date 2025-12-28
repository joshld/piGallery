
# piGallery
Displays a slideshow of photos on a Raspberry Pi (or any computer) with a connected display.

## Features

- 📸 Automatic slideshow with configurable timing
- 🌡️ Weather and time display
- 🌓 Auto display on/off scheduling
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
- pygame
- requests
- geopy
- flask
- flask-cors

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

**On the same network:**
- Open a browser and go to: `http://raspberrypi.local:5000`
- Or use the Pi's IP address: `http://192.168.1.xxx:5000`

**From your phone/tablet/laptop:**
- Simply open the URL above in any browser
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

- `GET /api/status` - Get current slideshow status
- `POST /api/next` - Skip to next image
- `POST /api/prev` - Go to previous image
- `POST /api/pause` - Toggle pause state
- `POST /api/display` - Control display (body: `{"action": "on|off|auto"}`)
- `POST /api/upload` - Upload new image (multipart form data)
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings (body: settings JSON)

## Quick Reference

### Access URLs
- **On Pi:** `http://localhost:5000`
- **Same network:** `http://raspberrypi.local:5000`
- **Direct IP:** `http://192.168.1.xxx:5000` (find with `hostname -I`)

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
- `location_city_suburb` - Weather location

### Troubleshooting
**Can't access web interface?**
- Run verification: `./test_setup.sh`
- Allow firewall: `sudo ufw allow 5000`
- Find Pi IP: `hostname -I`

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

### 9. Feature Tracking & Contributing

piGallery uses **GitHub Issues** for tracking features, bugs, and improvements. All TODO items have been converted to interactive GitHub Issues with checklists that you can check off as you complete tasks.

#### View Planned Features
- **Browse all issues:** https://github.com/joshld/piGallery/issues
- **View by priority:** Look for ⭐ emoji in issue titles
- **Track progress:** Each issue shows completion percentage

#### Key Feature Issues
- **#14** - ⭐ Telegram Integration (commands, remote control)
- **#7** - Image Captions from Metadata
- **#8** - Shutdown Button in Web UI
- **#15** - Color Schemes (Dark Mode)
- **#9** - Image Transitions
- **#10** - Video Support
- **#11** - Error Detection & Reporting
- **#12** - Delete Uploaded Images
- **#16** - Performance Monitoring

#### Using GitHub Issues
```bash
# List all features/issues
gh issue list

# View specific feature details
gh issue view 14

# Check off tasks as you complete them (on GitHub web UI)
# Reference issues in commits
git commit -m "Add Telegram status updates for #14"
```

For more details, see **[GITHUB_TODO_GUIDE.md](GITHUB_TODO_GUIDE.md)** for a complete guide on using GitHub Issues for task tracking.

### 10. Notes
- The script is designed for fullscreen display and will hide the mouse cursor.
- Weather and time information is displayed on the screen.
- Some features (like display power control) are specific to Raspberry Pi and may not work on other platforms.
- The web interface is accessible on port 5000 by default.
- Images can be organized in subfolders - the script will recursively scan all directories.


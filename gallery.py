import pygame
import os
import time
import random
import argparse
import datetime
import requests
import subprocess
from geopy.geocoders import Nominatim
import sys
import threading
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[Warning] psutil not available. System monitoring disabled.")

if sys.version_info < (3, 7):
    print("Python 3.7 or newer is required.")
    sys.exit(1)

# ---------------- Config ----------------
import configparser

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.ini")
DEFAULT_CONFIG = {
    "gallery": {
        "location_city_suburb": "Sydney, Australia",
        "images_directory": "/path/to/your/images/",
        "upload_directory": "",
        "display_off_time": "23:00",
        "display_on_time": "05:00",
        "delay_seconds": "10",
        "window_size": "1024x768",
        "fullscreen": "false",
        "display_correction_horizontal": "1.0",
        "display_correction_vertical": "1.0",
        "ui_text_alpha": "192",
        "image_history_size": "5",
        "weather_update_seconds": "900",
        "show_time": "true",
        "show_date": "true",
        "show_temperature": "true",
        "show_weather_code": "true",
        "show_filename": "true",
        "show_caption": "true",
        "shutdown_on_display_off": "true",
        "shutdown_countdown_seconds": "10"
    },
    "telegram": {
        "bot_token": "",
        "chat_id": "",
        "notify_startup": "true",
        "notify_shutdown": "true",
        "notify_errors": "true",
        "notify_image_changes": "false",
        "notify_uploads": "true",
        "notify_settings_changes": "false",
        "notify_system_alerts": "true",
        "image_notify_frequency": "10"
    }
}

config = configparser.ConfigParser()
if not os.path.exists(CONFIG_PATH):
    # Create new config with all defaults
    config.read_dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "w") as f:
        config.write(f)
else:
    # Read existing config
    config.read(CONFIG_PATH)
    
    # Merge missing keys from defaults (preserve existing values)
    updated = False
    for section, keys in DEFAULT_CONFIG.items():
        if section not in config:
            config[section] = {}
        for key, default_value in keys.items():
            if key not in config[section]:
                config[section][key] = default_value
                updated = True
                print(f"[Config] Adding missing key: [{section}] {key} = {default_value}")
    
    # Write back if any keys were added
    if updated:
        with open(CONFIG_PATH, "w") as f:
            config.write(f)
        print(f"[Config] Updated {CONFIG_PATH} with missing default settings")

GALLERY_CONFIG = config["gallery"] if "gallery" in config else DEFAULT_CONFIG["gallery"]
TELEGRAM_CONFIG = config["telegram"] if "telegram" in config else DEFAULT_CONFIG["telegram"]

print(f"[Startup] Loaded config from {CONFIG_PATH}, using {len(GALLERY_CONFIG)} settings.")

# Print all config.ini settings currently being used
print("[gallery] settings in use:")
for k, v in GALLERY_CONFIG.items():
    print(f"  {k} = {v}")

# ---------------- Logging Setup ----------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "gallery.log")

# Setup rotating file handler (10MB max, keep 1 backups)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=1,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

# Store original streams BEFORE setting up logger
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# Setup logger
logger = logging.getLogger('piGallery')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Note: We don't add a console handler because stdout/stderr redirection
# will handle console output, and we write directly to file_handler to avoid duplication

# Redirect stdout/stderr to logger to capture all print() statements
# Filter out Flask/Werkzeug HTTP request logs to avoid duplication
class StreamToLogger:
    """Redirect stdout/stderr to logger while preserving original behavior"""
    def __init__(self, stream, log_level=logging.INFO):
        self.stream = stream  # Original stream (stdout/stderr)
        self.log_level = log_level
        self.linebuf = ''
    
    def write(self, buf):
        if not buf:
            return
        
        # Convert bytes to string if necessary
        if isinstance(buf, bytes):
            buf = buf.decode('utf-8', errors='replace')
        
        # Handle incomplete lines from previous write
        if self.linebuf:
            buf = self.linebuf + buf
            self.linebuf = ''
        
        # Split buffer into lines
        lines = buf.split('\n')
        
        # If buffer doesn't end with newline, last line is incomplete - save it
        if not buf.endswith('\n') and lines:
            self.linebuf = lines[-1]
            lines = lines[:-1]
        
        # Write each complete line separately (skip empty lines to avoid extra blank lines)
        for line in lines:
            if line.strip():  # Only write non-empty lines
                self.stream.write(line + '\n')
                self.stream.flush()
                
                # Log to file (write directly to file handler to avoid console duplication)
                try:
                    record = logging.LogRecord(
                        name=logger.name,
                        level=self.log_level,
                        pathname='',
                        lineno=0,
                        msg=line,
                        args=(),
                        exc_info=None
                    )
                    file_handler.emit(record)
                except Exception:
                    # If logging fails, don't break the stream
                    pass
    
    def flush(self):
        self.stream.flush()

# Redirect stdout and stderr to logger
sys.stdout = StreamToLogger(_original_stdout, logging.INFO)
sys.stderr = StreamToLogger(_original_stderr, logging.ERROR)

logger.info("=" * 60)
logger.info("piGallery starting up")
logger.info(f"Log file: {LOG_FILE}")


def get_config_value(key, default=None):
    return GALLERY_CONFIG.get(key, default)


# Load additional constants from config.ini, with defaults
def get_float_config(key, default):
    try:
        return float(get_config_value(key, default))
    except Exception:
        return default


def get_int_config(key, default):
    try:
        return int(get_config_value(key, default))
    except Exception:
        return default


def get_bool_config(key, default):
    val = get_config_value(key, str(default)).lower()
    return val in ("1", "true", "yes", "on")


# ---------------- Constants ----------------
# These are now passed via config dictionary to avoid global variables

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


# ---------------- Utility Functions ----------------
def shutdown(timeout_seconds):
    try:
        if pygame.get_init():
            screen = pygame.display.get_surface()
        print(f"[System] Shutdown initiated, timeout={timeout_seconds}s")
        for remaining in range(timeout_seconds, 0, -1):
            if screen:
                screen.fill((0, 0, 0))
                font = pygame.font.SysFont(None, 48)
                text = font.render(f"Shutting down in {remaining} seconds...", True, (255, 255, 255))
                rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                screen.blit(text, rect)
                pygame.display.flip()
            else:
                print(f"Shutting down in {remaining} seconds...")
            time.sleep(1)
        # Requires the script to run with sudo or the user must have shutdown privileges
        # Try Linux shutdown command, catch failure on Windows
        try:
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # On Windows or if command fails
            print("[System] Shutdown command not available")
    except subprocess.CalledProcessError as e:
        print(f"Failed to shutdown: {e}")


def get_coords_from_place(place_name: str):
    geolocator = Nominatim(user_agent="my_geocoder")
    try:
        # Use shorter timeout to avoid blocking startup
        location = geolocator.geocode(place_name, timeout=2)
        return (location.latitude, location.longitude) if location else (None, None)
    except Exception as e:
        print(f"[Geocoding] Error: {e}")
        return (None, None)


def get_weather(lat=51.5072, lon=-0.1276):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        print(f"[Weather] Fetching weather for lat={lat}, lon={lon}")
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        weather = r.json()["current_weather"]
        return float(weather["temperature"]), float(weather["windspeed"]), weather["weathercode"]
    except Exception as e:
        print(f"Weather error: {e}")
        return None, None, None


# ---------------- Telegram Notifications ----------------


class TelegramNotifier:
    """Handles sending notifications to Telegram"""
    
    def __init__(self, config_dict):
        self.config = config_dict
        self.bot_token = config_dict.get('bot_token', '').strip()
        self.chat_id = config_dict.get('chat_id', '').strip()
        self.enabled = bool(self.bot_token and self.chat_id)
        self.image_change_count = 0
        
        if self.enabled:
            try:
                # Test connection
                self._send_message("🤖 piGallery Telegram notifications enabled!")
                print("[Telegram] Notifications enabled and tested successfully")
            except Exception as e:
                print(f"[Telegram] Warning: Failed to send test message: {e}")
                self.enabled = False
        else:
            print("[Telegram] Notifications disabled (bot_token or chat_id not set)")
    
    def _send_message(self, message, parse_mode='HTML'):
        """Internal method to send a message to Telegram"""
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, data=data, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Telegram] Error sending message: {e}")
            return False
    
    def notify_startup(self):
        """Send startup notification"""
        if not self.enabled or not self.config.get('notify_startup', 'true').lower() == 'true':
            return
        message = "🚀 <b>piGallery Started</b>\n" \
                 f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self._send_message(message)
    
    def notify_shutdown(self):
        """Send shutdown notification"""
        if not self.enabled or not self.config.get('notify_shutdown', 'true').lower() == 'true':
            return
        message = "🛑 <b>piGallery Shutting Down</b>\n" \
                 f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self._send_message(message)
    
    def notify_error(self, error_message, context=""):
        """Send error notification (immediate alerts)"""
        if not self.enabled or not self.config.get('notify_errors', 'true').lower() == 'true':
            return
        message = "⚠️ <b>Error Alert</b>\n" \
                 f"❌ {error_message}"
        if context:
            message += f"\n📍 {context}"
        message += f"\n📅 {datetime.datetime.now().strftime('%H:%M:%S')}"
        self._send_message(message)
    
    def notify_image_change(self, image_name, image_index, total_images):
        """Send image change notification (with frequency control)"""
        if not self.enabled or not self.config.get('notify_image_changes', 'false').lower() == 'true':
            return
        
        frequency = int(self.config.get('image_notify_frequency', '10'))
        self.image_change_count += 1
        
        if frequency > 0 and self.image_change_count % frequency != 0:
            return
        
        message = "📸 <b>Image Changed</b>\n" \
                 f"🖼️ {image_name}\n" \
                 f"📊 {image_index} / {total_images}"
        self._send_message(message)
    
    def notify_upload(self, filename):
        """Send upload notification"""
        if not self.enabled or not self.config.get('notify_uploads', 'true').lower() == 'true':
            return
        message = "📤 <b>New Image Uploaded</b>\n" \
                 f"📁 {filename}\n" \
                 f"📅 {datetime.datetime.now().strftime('%H:%M:%S')}"
        self._send_message(message)
    
    def notify_settings_change(self, setting_name, old_value, new_value):
        """Send settings change notification"""
        if not self.enabled or not self.config.get('notify_settings_changes', 'false').lower() == 'true':
            return
        message = "⚙️ <b>Settings Changed</b>\n" \
                 f"🔧 {setting_name}\n" \
                 f"📝 {old_value} → {new_value}"
        self._send_message(message)
    
    def notify_system_alert(self, alert_type, message, value=None):
        """Send system alert (low memory, high CPU, high temp)"""
        if not self.enabled or not self.config.get('notify_system_alerts', 'true').lower() == 'true':
            return
        
        emoji_map = {
            'memory': '💾',
            'cpu': '⚡',
            'temperature': '🌡️',
            'disk': '💿'
        }
        emoji = emoji_map.get(alert_type, '⚠️')
        
        alert_message = f"{emoji} <b>System Alert: {alert_type.upper()}</b>\n" \
                       f"⚠️ {message}"
        if value is not None:
            alert_message += f"\n📊 Current: {value}"
        alert_message += f"\n📅 {datetime.datetime.now().strftime('%H:%M:%S')}"
        self._send_message(alert_message)


# ---------------- System Monitoring ----------------


def get_cpu_temperature():
    """Get CPU temperature (Raspberry Pi specific, very lightweight)"""
    # Try Raspberry Pi vcgencmd first (native, no dependencies)
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], 
                              capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            temp_str = result.stdout.strip()
            # Extract temperature value (format: "temp=45.2'C")
            temp = float(temp_str.split('=')[1].split("'")[0])
            return temp
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
        pass
    
    # Fallback to psutil only if available (for non-Pi systems)
    if PSUTIL_AVAILABLE:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return entries[0].current
        except Exception:
            pass
    
    return None


def get_memory_info():
    """Get memory info - lightweight on Linux, psutil on Windows/Mac"""
    # Try lightweight /proc/meminfo on Linux first
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            # Parse MemAvailable (preferred) or MemFree
            for line in meminfo.split('\n'):
                if line.startswith('MemAvailable:'):
                    # Format: "MemAvailable:    123456 kB"
                    kb = int(line.split()[1])
                    return kb / 1024  # Convert to MB
                elif line.startswith('MemFree:'):
                    kb = int(line.split()[1])
                    return kb / 1024
    except (FileNotFoundError, ValueError, IndexError):
        pass
    
    # Fallback to psutil (works on Windows, Mac, and Linux)
    if PSUTIL_AVAILABLE:
        try:
            mem = psutil.virtual_memory()
            return mem.available / (1024 * 1024)
        except Exception:
            pass
    
    return None


def get_cpu_usage():
    """Get CPU usage - lightweight on Linux, psutil on Windows/Mac"""
    # Try lightweight /proc/stat on Linux first
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            # Format: "cpu  1234 0 5678 9012 0 0 0 0 0 0"
            parts = line.split()
            if len(parts) >= 8:
                # Calculate CPU usage from idle time
                user = int(parts[1])
                nice = int(parts[2])
                system = int(parts[3])
                idle = int(parts[4])
                iowait = int(parts[5])
                
                total = user + nice + system + idle + iowait
                if total > 0:
                    # Return non-idle percentage
                    non_idle = user + nice + system + iowait
                    return (non_idle / total) * 100
    except (FileNotFoundError, ValueError, IndexError):
        pass
    
    # Fallback to psutil (works on Windows, Mac, and Linux)
    if PSUTIL_AVAILABLE:
        try:
            return psutil.cpu_percent(interval=0.1)  # Short interval for lighter check
        except Exception:
            pass
    
    return None


def get_disk_usage(path='/'):
    """Get disk usage - lightweight on Linux, psutil on Windows/Mac"""
    # Try lightweight df command on Linux first
    try:
        result = subprocess.run(['df', '-B', '1', path], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # Parse the header and data line
                # Format: "Filesystem      1B-blocks       Used Available Use% Mounted on"
                #         "/dev/mmcblk0p2 7122513920 5904424960 835575808  88% /"
                parts = lines[1].split()
                if len(parts) >= 4:
                    total = int(parts[1])
                    used = int(parts[2])
                    available = int(parts[3])
                    percent_used = (used / total) * 100 if total > 0 else 0
                    return {
                        'total': total,
                        'used': used,
                        'available': available,
                        'percent_used': percent_used
                    }
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
        pass
    
    # Fallback to psutil (works on Windows, Mac, and Linux)
    if PSUTIL_AVAILABLE:
        try:
            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'available': usage.free,
                'percent_used': usage.percent
            }
        except Exception:
            pass
    
    return None


def monitor_system_resources(telegram_notifier, check_interval=120):
    """Monitor system resources using lightweight native OS commands"""
    # Alert thresholds
    MEMORY_THRESHOLD_MB = 100  # Alert if less than 100 MB free
    CPU_THRESHOLD_PERCENT = 80  # Alert if CPU > 80% for sustained period
    TEMP_THRESHOLD_C = 80  # Alert if temperature > 80°C
    
    # State tracking to avoid spam
    last_alert_time = {
        'memory': 0,
        'cpu': 0,
        'temperature': 0
    }
    alert_cooldown = 300  # 5 minutes between alerts of same type
    cpu_high_count = 0  # Count consecutive high CPU readings
    last_cpu_total = None  # For calculating CPU delta
    
    print("[System Monitor] Starting lightweight system resource monitoring")
    
    while True:
        try:
            now = time.time()
            
            # Check memory (lightweight /proc/meminfo)
            free_mb = get_memory_info()
            if free_mb is not None and free_mb < MEMORY_THRESHOLD_MB:
                if now - last_alert_time['memory'] > alert_cooldown:
                    telegram_notifier.notify_system_alert(
                        'memory',
                        f"Low memory: {free_mb:.1f} MB free (threshold: {MEMORY_THRESHOLD_MB} MB)",
                        f"{free_mb:.1f} MB free"
                    )
                    last_alert_time['memory'] = now
            
            # Check CPU (lightweight /proc/stat, non-blocking)
            cpu_percent = get_cpu_usage()
            if cpu_percent is not None:
                if cpu_percent > CPU_THRESHOLD_PERCENT:
                    cpu_high_count += 1
                    # Alert if high for 3 consecutive checks
                    if cpu_high_count >= 3 and now - last_alert_time['cpu'] > alert_cooldown:
                        telegram_notifier.notify_system_alert(
                            'cpu',
                            f"High CPU usage: {cpu_percent:.1f}% (threshold: {CPU_THRESHOLD_PERCENT}%)",
                            f"{cpu_percent:.1f}%"
                        )
                        last_alert_time['cpu'] = now
                        cpu_high_count = 0
                else:
                    cpu_high_count = 0
            
            # Check temperature (lightweight vcgencmd on Pi)
            temp = get_cpu_temperature()
            if temp is not None and temp > TEMP_THRESHOLD_C:
                if now - last_alert_time['temperature'] > alert_cooldown:
                    telegram_notifier.notify_system_alert(
                        'temperature',
                        f"High temperature: {temp:.1f}°C (threshold: {TEMP_THRESHOLD_C}°C)",
                        f"{temp:.1f}°C"
                    )
                    last_alert_time['temperature'] = now
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"[System Monitor] Error: {e}")
            time.sleep(check_interval)


def scale_image(img, screen_w, screen_h, correction_h=1.0, correction_v=1.0):
    """
    Scale image to fit screen while maintaining aspect ratio.
    correction_h: Horizontal correction factor (default 1.0)
    correction_v: Vertical correction factor (default 1.0)
    """
    img_w, img_h = img.get_size()
    img_aspect = img_w / img_h
    
    # Calculate effective screen dimensions accounting for hardware correction
    effective_screen_w = screen_w / correction_h if correction_h != 1.0 else screen_w
    effective_screen_h = screen_h / correction_v if correction_v != 1.0 else screen_h
    screen_aspect = effective_screen_w / effective_screen_h

    if img_aspect > screen_aspect:
        scale = effective_screen_w / img_w
    else:
        scale = effective_screen_h / img_h

    base_w = int(img_w * scale)
    base_h = int(img_h * scale)
    
    # Apply corrections
    new_w = int(base_w * correction_h)
    new_h = int(base_h * correction_v)
    
    # Ensure final dimensions don't exceed screen bounds
    if new_w > screen_w:
        scale_factor = screen_w / new_w
        new_w = screen_w
        new_h = int(new_h * scale_factor)
    if new_h > screen_h:
        scale_factor = screen_h / new_h
        new_h = screen_h
        new_w = int(new_w * scale_factor)
    
    img_scaled = pygame.transform.scale(img, (new_w, new_h))
    x_offset = (screen_w - new_w) // 2
    y_offset = (screen_h - new_h) // 2
    return img_scaled, x_offset, y_offset, new_w


# ---------------- Web Server Setup ----------------
app = Flask(__name__, static_folder='static')
CORS(app)

# Global reference to slideshow instance (set in main)
slideshow_instance = None
telegram_notifier = None
power_action_in_progress = False  # Prevent multiple shutdown/restart requests
power_action_cancel_event = None  # Event to cancel ongoing power action


# ---------------- Slideshow Class ----------------
class Slideshow:
    def __init__(self, folder, screen, display_time_seconds, config_dict, telegram_notifier=None):
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()
        self.display_time_seconds = display_time_seconds
        self.config = config_dict
        
        self.screen_w, self.screen_h = screen.get_size()
        print(f"[Display] Detected resolution: {self.screen_w}x{self.screen_h}")

        # Calculate optimal aspect ratios based on screen dimensions if not specified
        screen_aspect = self.screen_w / self.screen_h

        self.telegram = telegram_notifier

        self.images = []
        self.folder = folder

        self.history = []
        self.forward_stack = []
        self.current_index = -1
        self.current_img = None
        self.total_images = 0
        
        # Web control state
        self.paused = False
        self.manual_display_override = None  # None = auto, True = force on, False = force off
        self.control_lock = threading.Lock()
        self.force_redraw = False
        
        # Countdown tracking for web UI
        self.image_display_start_time = time.time()
        self.time_remaining = display_time_seconds

        self.fonts = {
            "filename": pygame.font.SysFont("Arial", 14),
            "time": pygame.font.SysFont(None, 132),
            "date": pygame.font.SysFont(None, 72),
            "temp": pygame.font.SysFont(None, 132),
            "weather": pygame.font.SysFont(None, 72),
            "caption": pygame.font.SysFont(None, 48),  # Caption font - medium size for readability
        }
        
        # Cache for current image caption to avoid re-reading on every frame
        self._cached_caption = None
        self._cached_caption_image = None

        self.text_color = (255, 255, 255)

        # Weather - geocode asynchronously to avoid blocking startup
        self.city_suburb = config_dict.get('location_city_suburb', 'Sydney, Australia')
        self.lat, self.long = 51.5072, 0.1276  # Default coordinates (London)
        show_temp = config_dict.get('show_temperature', 'true').lower() == 'true'
        show_weather = config_dict.get('show_weather_code', 'true').lower() == 'true'
        if show_temp or show_weather:
            # Try geocoding but don't block - will retry later if needed
            try:
                print(f"[Startup] Geocoding {self.city_suburb}...")
                self.lat, self.long = get_coords_from_place(self.city_suburb)
                if self.lat is None or self.long is None:
                    print(f"[Warning] Could not geocode {self.city_suburb}, using default coordinates")
                    self.lat, self.long = 51.5072, 0.1276
                else:
                    print(f"[Startup] Geocoded {self.city_suburb} to lat={self.lat}, lon={self.long}")
            except Exception as e:
                print(f"[Warning] Geocoding failed: {e}, using default coordinates")
                self.lat, self.long = 51.5072, 0.1276
        self.current_temp = ""
        self.current_weather = ""
        self.last_weather_update = 0

    def update_weather(self):
        now = time.time()
        weather_update_interval = int(self.config.get('weather_update_seconds', '900'))
        if now - self.last_weather_update > weather_update_interval:
            temp, wind, code = get_weather(self.lat, self.long)
            if temp is not None and code is not None:
                self.current_temp = f"{temp}°C"
                weather_desc = WEATHER_CODES.get(code, f"Unknown ({code})")
                self.current_weather = weather_desc
                print(f"[Weather] Updated: {self.current_temp}, {self.current_weather}")
            self.last_weather_update = now

    def draw_blank_screen(self):
        self.screen.fill((0, 0, 0))

    def draw_image(self):
        # Skip if file is missing, but prevent infinite loops
        attempts = 0
        max_attempts = 10
        while self.current_img and attempts < max_attempts:
            img_path = os.path.join(self.folder, self.current_img)
            if os.path.exists(img_path):
                break
            print(f"Missing file: {self.current_img}, skipping...")
            self.next_image()
            attempts += 1
        
        if attempts >= max_attempts:
            error_msg = f"Too many missing files, stopping image search"
            print(f"[Error] {error_msg}")
            if self.telegram:
                self.telegram.notify_error(error_msg, f"Directory: {self.folder}")
            self.current_img = None

        self.screen.fill((0, 0, 0))
        new_w = 0
        
        # Show status message if no images found
        if not self.current_img:
            if not os.path.exists(self.folder):
                status_msg = f"No images found in directory: {self.folder}"
            elif len(self.images) == 0 and len(self.history) == 0:
                status_msg = f"No images found in: {self.folder}"
            else:
                status_msg = "Loading images..."
            
            # Draw status message in center of screen
            status_font = pygame.font.SysFont(None, 32)
            status_surf = status_font.render(status_msg, True, (255, 255, 255))
            status_rect = status_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
            self.screen.blit(status_surf, status_rect)
            # Only print once, not every frame
            if not hasattr(self, '_last_status_msg') or self._last_status_msg != status_msg:
                print(f"[Slideshow] {status_msg}")
                self._last_status_msg = status_msg
        
        if self.current_img:
            # Check if this is an uploaded image (starts with "uploaded/")
            if self.current_img.startswith("uploaded/"):
                # Get upload directory
                upload_dir = self.config.get('upload_directory', '').strip()
                if upload_dir:
                    upload_dir = os.path.expanduser(upload_dir)
                    # Remove "uploaded/" prefix to get actual path
                    actual_path = self.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                    img_path = os.path.join(upload_dir, actual_path)
                else:
                    # Fallback: treat as subdirectory of main folder
                    img_path = os.path.join(self.folder, self.current_img)
            else:
                # Regular image in main directory
                img_path = os.path.join(self.folder, self.current_img)

            try:
                img = pygame.image.load(img_path)
                # Get display correction factors for displays with hardware stretching
                # This compensates for displays where resolution doesn't match physical aspect ratio
                try:
                    correction_h = float(self.config.get('display_correction_horizontal', '1.0'))
                except (ValueError, TypeError):
                    correction_h = 1.0
                
                try:
                    correction_v = float(self.config.get('display_correction_vertical', '1.0'))
                except (ValueError, TypeError):
                    correction_v = 1.0

                img_scaled, x_off, y_off, new_w = scale_image(img, self.screen_w, self.screen_h, correction_h, correction_v)
                
                self.screen.blit(img_scaled, (x_off, y_off))
                print(f"[Slideshow] Drawing {self.current_img} scaled to {new_w}x{img_scaled.get_height()}")
            except pygame.error as e:
                error_msg = f"Failed to load image {self.current_img}: {e}"
                print(f"[Error] {error_msg}")
                if self.telegram:
                    self.telegram.notify_error(error_msg, f"Path: {img_path}")
                self.current_img = None

        now = datetime.datetime.now()

        # filename
        show_filename = self.config.get('show_filename', 'true').lower() == 'true'
        if show_filename and self.current_img:
            text = f"{self.current_img} ({new_w}x{self.screen_h})"
            surf = self.fonts["filename"].render(text, True, self.text_color)
            rect = surf.get_rect(bottomright=(self.screen_w - 10, self.screen_h - 10))
            self.screen.blit(surf, rect)

        # time
        show_time = self.config.get('show_time', 'true').lower() == 'true'
        if show_time:
            time_surf = self.fonts["time"].render(now.strftime("%I:%M"), True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            time_surf.set_alpha(text_alpha)
            
            # Draw background
            padding = 8
            x_pos, y_pos = 10, 10
            bg_rect = pygame.Rect(x_pos - padding, y_pos - padding // 2, 
                                 time_surf.get_width() + (padding * 2), 
                                 time_surf.get_height() + padding)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(100)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, (bg_rect.x, bg_rect.y))
            
            self.screen.blit(time_surf, (x_pos, y_pos))

        # date
        show_date = self.config.get('show_date', 'true').lower() == 'true'
        if show_date:
            date_surf = self.fonts["date"].render(now.strftime("%d %b %y"), True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            date_surf.set_alpha(text_alpha)
            
            # Draw background
            padding = 8
            x_pos, y_pos = 10, 90
            bg_rect = pygame.Rect(x_pos - padding, y_pos - padding // 2, 
                                 date_surf.get_width() + (padding * 2), 
                                 date_surf.get_height() + padding)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(100)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, (bg_rect.x, bg_rect.y))
            
            self.screen.blit(date_surf, (x_pos, y_pos))

        # weather
        show_temperature = self.config.get('show_temperature', 'true').lower() == 'true'
        show_weather_code = self.config.get('show_weather_code', 'true').lower() == 'true'
        if show_temperature or show_weather_code:
            self.update_weather()
        if show_temperature and self.current_temp:
            temp_surf = self.fonts["temp"].render(self.current_temp, True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            temp_surf.set_alpha(text_alpha)
            
            # Draw background
            padding = 8
            x_pos = self.screen_w - temp_surf.get_width() - 10
            y_pos = 10
            bg_rect = pygame.Rect(x_pos - padding, y_pos - padding // 2, 
                                 temp_surf.get_width() + (padding * 2), 
                                 temp_surf.get_height() + padding)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(100)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, (bg_rect.x, bg_rect.y))
            
            self.screen.blit(temp_surf, (x_pos, y_pos))
        if show_weather_code and self.current_weather:
            weather_surf = self.fonts["weather"].render(self.current_weather, True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            weather_surf.set_alpha(text_alpha)
            
            # Draw background
            padding = 8
            x_pos = self.screen_w - weather_surf.get_width() - 10
            y_pos = 90
            bg_rect = pygame.Rect(x_pos - padding, y_pos - padding // 2, 
                                 weather_surf.get_width() + (padding * 2), 
                                 weather_surf.get_height() + padding)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(100)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, (bg_rect.x, bg_rect.y))
            
            self.screen.blit(weather_surf, (x_pos, y_pos))
        
        # caption overlay
        show_caption = self.config.get('show_caption', 'true').lower() == 'true'
        if show_caption and self.current_img:
            # Check if we need to reload caption (image changed)
            if self._cached_caption_image != self.current_img:
                # Get image path
                if self.current_img.startswith("uploaded/"):
                    upload_dir = self.config.get('upload_directory', '').strip()
                    if upload_dir:
                        upload_dir = os.path.expanduser(upload_dir)
                        actual_path = self.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                        img_path = os.path.join(upload_dir, actual_path)
                    else:
                        img_path = os.path.join(self.folder, self.current_img)
                else:
                    img_path = os.path.join(self.folder, self.current_img)
                
                # Read caption from metadata
                self._cached_caption = get_image_caption(img_path)
                self._cached_caption_image = self.current_img
            
            # Display caption if it exists
            if self._cached_caption:
                # Word wrap caption if it's too long (max ~60 chars per line for readability)
                max_chars_per_line = 60
                words = self._cached_caption.split()
                lines = []
                current_line = ""
                
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_chars_per_line:
                        current_line += (" " if current_line else "") + word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                
                # Limit to 3 lines max to avoid taking up too much screen space
                if len(lines) > 3:
                    lines = lines[:3]
                    lines[2] = lines[2][:57] + "..."
                
                # Render each line  
                line_height = 45  # Reduced from 55 for tighter line spacing
                # Position caption extremely close to bottom edge
                # Very minimal padding (5px) - caption sits just above filename
                start_y = self.screen_h - (len(lines) * line_height) - 5
                
                for i, line in enumerate(lines):
                    caption_surf = self.fonts["caption"].render(line, True, self.text_color)
                    text_alpha = int(self.config.get('ui_text_alpha', '192'))
                    caption_surf.set_alpha(text_alpha)
                    # Center horizontally
                    x_pos = (self.screen_w - caption_surf.get_width()) // 2
                    y_pos = start_y + (i * line_height)
                    
                    # Draw semi-transparent dark background behind text for better readability
                    padding = 10  # Padding around text
                    bg_rect = pygame.Rect(
                        x_pos - padding,
                        y_pos - padding // 2,
                        caption_surf.get_width() + (padding * 2),
                        caption_surf.get_height() + padding
                    )
                    # Create semi-transparent surface for background
                    bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
                    bg_surface.set_alpha(100)  # More transparent (0=transparent, 255=opaque)
                    bg_surface.fill((0, 0, 0))  # Black background
                    self.screen.blit(bg_surface, (bg_rect.x, bg_rect.y))
                    
                    # Draw text on top of background
                    self.screen.blit(caption_surf, (x_pos, y_pos))

    def refresh_images(self):
        # Check if directory exists
        if not os.path.exists(self.folder):
            print(f"[Error] Images directory does not exist: {self.folder}")
            return
        if not os.path.isdir(self.folder):
            print(f"[Error] Images path is not a directory: {self.folder}")
            return
        
        # Recursively scan for images (supports subfolders)
        new_images = []
        try:
            # Scan main images directory
            for root, _, files in os.walk(self.folder):
                for f in files:
                    if f.lower().endswith((".jpg", ".jpeg", ".png")):
                        # Store relative path from base folder
                        rel_path = os.path.relpath(os.path.join(root, f), self.folder)
                        # Check if image is already in queue, history, or is current image
                        if rel_path not in self.images and rel_path not in self.history and rel_path != self.current_img:
                            new_images.append(rel_path)
            
            # Also scan upload directory if it's separate from images directory
            upload_dir = self.config.get('upload_directory', '').strip()
            if upload_dir:
                upload_dir = os.path.expanduser(upload_dir)
                if os.path.exists(upload_dir) and os.path.isdir(upload_dir):
                    # Check if upload_dir is within self.folder (already scanned by os.walk)
                    try:
                        # Normalize paths for comparison
                        main_folder_abs = os.path.abspath(self.folder)
                        upload_dir_abs = os.path.abspath(upload_dir)
                        
                        # Check if upload_dir is a subdirectory of main folder
                        common_path = os.path.commonpath([main_folder_abs, upload_dir_abs])
                        is_subdirectory = os.path.abspath(common_path) == main_folder_abs
                    except (ValueError, OSError):
                        # Paths are on different drives (Windows) or can't be compared
                        is_subdirectory = False
                    
                    if not is_subdirectory:
                        # Upload directory is separate, scan it too
                        print(f"[Slideshow] Also scanning upload directory: {upload_dir}")
                        for root, _, files in os.walk(upload_dir):
                            for f in files:
                                if f.lower().endswith((".jpg", ".jpeg", ".png")):
                                    # Store as relative path from upload_dir, with "uploaded/" prefix
                                    rel_path = os.path.relpath(os.path.join(root, f), upload_dir)
                                    # Use a prefix to distinguish uploaded images
                                    upload_rel_path = os.path.join("uploaded", rel_path).replace("\\", "/")
                                    # Check if image is already in queue, history, or is current image
                                    if upload_rel_path not in self.images and upload_rel_path not in self.history and upload_rel_path != self.current_img:
                                        new_images.append(upload_rel_path)
        except PermissionError as e:
            print(f"[Error] Permission denied accessing {self.folder}: {e}")
            return
        except Exception as e:
            print(f"[Error] Failed to scan images directory: {e}")
            return
            
        if new_images:
            random.shuffle(new_images)
            self.images.extend(new_images)
        self.total_images = len(self.images) + len(self.history)
        print(f"[Slideshow] Found {len(new_images)} new images, total queue={self.total_images}")

    def next_image(self):
        if self.forward_stack:
            self.current_img = self.forward_stack.pop()
        elif self.current_index < len(self.history) - 1:
            self.current_index += 1
            self.current_img = self.history[self.current_index]
        else:
            # Refresh images every time we reach the end
            if not self.images:
                self.refresh_images()

            if self.images:
                self.current_img = self.images.pop()
                self.history.append(self.current_img)
                self.current_index = len(self.history) - 1
            elif self.history:
                # If no new images, loop through history
                self.current_index = 0
                self.current_img = self.history[self.current_index]
            else:
                # Nothing at all, do nothing
                self.current_img = None
        print(f"[Slideshow] Next image {self.current_index+1}/{self.total_images}: {self.current_img}")
        # Notify Telegram of image change
        if self.telegram and self.current_img:
            self.telegram.notify_image_change(self.current_img, self.current_index + 1, self.total_images)

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.forward_stack.append(self.history[self.current_index])
            self.current_img = self.history[self.current_index]
            print(f"[Slideshow] Previous image {self.current_index+1}/{self.total_images}: {self.current_img}")
            # Notify Telegram of image change
            if self.telegram and self.current_img:
                self.telegram.notify_image_change(self.current_img, self.current_index + 1, self.total_images)

    def is_display_on(self):
        # Check for manual override first
        if self.manual_display_override is not None:
            return self.manual_display_override
            
        now = datetime.datetime.now().time()
        display_off_time = self.config.get('display_off_time', '23:00')
        display_on_time = self.config.get('display_on_time', '05:00')
        
        try:
            off_time = datetime.datetime.strptime(display_off_time, "%H:%M").time()
            on_time = datetime.datetime.strptime(display_on_time, "%H:%M").time()
        except ValueError as e:
            print(f"[Error] Invalid time format in config: {e}")
            return True  # Default to always on if config is invalid

        if on_time < off_time:  # normal case (e.g., 07:00–23:00)
            return on_time <= now < off_time
        else:  # crosses midnight (e.g., 22:00–06:00)
            return not (off_time <= now < on_time)

    def set_display_power(self, on: bool):
        try:
            # Check current state
            result = subprocess.run(
                ["vcgencmd", "display_power"],
                capture_output=True,
                text=True
            )
            current_state = int(result.stdout.strip().split('=')[1])
            print(f"[Display] Requesting display {'ON' if on else 'OFF'}, current state={current_state}")
            if on and current_state == 0:
                os.system("vcgencmd display_power 1")
            elif not on and current_state == 1:
                os.system("vcgencmd display_power 0")
            # else: already in desired state
        except FileNotFoundError:
            # Not on Raspberry Pi - silently skip
            pass
        except Exception as e:
            print(f"Failed to set display power: {e}")

    def run(self):
        print("[Slideshow] Starting slideshow loop...")
        print(f"[Slideshow] Images directory: {self.folder}")
        print(f"[Slideshow] Directory exists: {os.path.exists(self.folder)}")
        
        # Try to load initial images
        if not self.images and len(self.history) == 0:
            self.refresh_images()
        
        clock = pygame.time.Clock()
        display_was_on = True
        
        while True:
            display_should_be_on = self.is_display_on()
            
            # Check if we need to force a redraw (settings changed) without advancing image
            if self.force_redraw:
                if display_should_be_on:
                    self.set_display_power(True)
                    self.draw_image()
                    pygame.display.flip()
                else:
                    self.draw_blank_screen()
                    pygame.display.flip()
                    self.set_display_power(False)
                self.force_redraw = False
                # Continue to wait loop without advancing image
            elif display_should_be_on:
                self.set_display_power(True)

                # Only advance if not paused
                if not self.paused:
                    self.next_image()
                    self.draw_image()
                    pygame.display.flip()
                    # Reset countdown timer
                    self.image_display_start_time = time.time()
                
                display_was_on = True
            else:
                if display_was_on:
                    print("[Display] Display off time reached, blanking screen")
                    display_was_on = False
                self.draw_blank_screen()
                pygame.display.flip()
                self.set_display_power(False)
                
                # Optional automatic shutdown if configured
                # ONLY trigger automatic shutdown if this is a scheduled display off, not manual override
                shutdown_enabled = self.config.get('shutdown_on_display_off', 'false').lower() == 'true'
                is_scheduled_off = self.manual_display_override is None  # None means automatic, not manual
                if shutdown_enabled and is_scheduled_off:
                    countdown_seconds = int(self.config.get('shutdown_countdown_seconds', '10'))
                    # Notify via Telegram before shutting down
                    if self.telegram:
                        self.telegram.notify_system_alert(
                            'shutdown',
                            f'Automatic shutdown in {countdown_seconds} seconds (display off time reached)',
                            f'{countdown_seconds}s countdown'
                        )
                    shutdown(countdown_seconds)

            # Wait for display_time_seconds, handling events (original structure)
            start_time = time.time()
            while time.time() - start_time < self.display_time_seconds:
                # Check for forced redraw during wait (for settings changes)
                if self.force_redraw:
                    # Break out of delay loop to immediately process display state change
                    break

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        raise SystemExit
                    if event.type == pygame.KEYDOWN:
                        print(f"[Input] Key pressed: {pygame.key.name(event.key)}")
                        if event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            raise SystemExit
                        elif event.key == pygame.K_RIGHT:
                            start_time = 0
                            break
                        elif event.key == pygame.K_LEFT:
                            with self.control_lock:
                                self.prev_image()
                                if display_should_be_on:
                                    self.draw_image()
                                    pygame.display.flip()
                                start_time = 0
                                break
                clock.tick(60)


# ---------------- Logging Functions ----------------

def get_logs(lines=200):
    """Get logs from journalctl (systemd) or log file (cross-platform)"""
    logs = []
    
    # Try journalctl first (Linux with systemd)
    if sys.platform == 'linux':
        # Check if running as systemd service
        try:
            # Try to get service name from environment or use default
            service_name = os.environ.get('SERVICE_NAME', 'piGallery.service')
            result = subprocess.run(
                ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip().split('\n')
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass  # Fall through to file reading
    
    # Fallback: Read from log file (works everywhere)
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                # Return last N lines
                return [line.rstrip('\n') for line in all_lines[-lines:]]
        except Exception as e:
            logger.warning(f"Error reading log file: {e}")
            return [f"Error reading log file: {e}"]
    
    return ["No logs available"]


# ---------------- Web API Endpoints ----------------

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/status')
def api_status():
    """Get current slideshow status"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    # Get system stats
    system_stats = {}
    try:
        memory = get_memory_info()
        if memory is not None:
            system_stats['memory_free_mb'] = round(memory, 1)
        
        cpu = get_cpu_usage()
        if cpu is not None:
            system_stats['cpu_percent'] = round(cpu, 1)
        
        temp = get_cpu_temperature()
        if temp is not None:
            system_stats['cpu_temp'] = round(temp, 1)
        
        disk = get_disk_usage()
        if disk is not None:
            system_stats['disk_free_gb'] = round(disk['available'] / (1024 * 1024 * 1024), 2)
            system_stats['disk_used_percent'] = round(disk['percent_used'], 1)
    except Exception as e:
        print(f"[API] Error getting system stats: {e}")
    
    # Calculate time remaining until next image
    elapsed = time.time() - slideshow_instance.image_display_start_time
    time_remaining = max(0, slideshow_instance.display_time_seconds - int(elapsed))
    
    response = {
        'current_image': slideshow_instance.current_img,
        'current_index': slideshow_instance.current_index + 1,
        'total_images': slideshow_instance.total_images,
        'temperature': slideshow_instance.current_temp,
        'weather': slideshow_instance.current_weather,
        'time': datetime.datetime.now().strftime("%I:%M %p"),
        'date': datetime.datetime.now().strftime("%d %b %Y"),
        'paused': slideshow_instance.paused,
        'display_on': slideshow_instance.is_display_on(),
        'manual_override': slideshow_instance.manual_display_override,
        'time_remaining': time_remaining,
        'delay_seconds': slideshow_instance.display_time_seconds
    }
    
    if system_stats:
        response['system'] = system_stats
    
    return jsonify(response)

@app.route('/api/logs')
def api_logs():
    """Get application logs"""
    lines = request.args.get('lines', 200, type=int)
    # Limit to reasonable range
    lines = max(50, min(1000, lines))
    
    try:
        log_lines = get_logs(lines)
        return jsonify({
            'status': 'ok',
            'lines': log_lines,
            'count': len(log_lines)
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/directories', methods=['GET'])
def api_directories():
    """List directories for folder selection"""
    path = request.args.get('path', '')
    
    if not path:
        # Return root directories
        if sys.platform == 'win32':
            # Windows: list drive letters
            import string
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
            return jsonify({'directories': drives, 'current_path': ''})
        else:
            # Unix/Linux: start from home directory
            home = os.path.expanduser('~')
            return jsonify({'directories': [home, '/'], 'current_path': ''})
    
    # Expand user path (~)
    path = os.path.expanduser(path)
    
    if not os.path.exists(path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    if not os.path.isdir(path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    try:
        # List directories only
        dirs = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                dirs.append(item)
        
        dirs.sort()
        return jsonify({
            'directories': dirs,
            'current_path': path,
            'parent_path': os.path.dirname(path) if path != os.path.dirname(path) else None
        })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_image_path():
    """Helper function to get the current image path"""
    if slideshow_instance is None or not slideshow_instance.current_img:
        return None
    
    # Check if this is an uploaded image
    if slideshow_instance.current_img.startswith("uploaded/"):
        upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
        if upload_dir:
            upload_dir = os.path.expanduser(upload_dir)
            actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
            img_path = os.path.join(upload_dir, actual_path)
        else:
            img_path = os.path.join(slideshow_instance.folder, slideshow_instance.current_img)
    else:
        img_path = os.path.join(slideshow_instance.folder, slideshow_instance.current_img)
    
    return img_path if os.path.exists(img_path) else None

def get_image_caption(img_path):
    """Read caption from image metadata (EXIF/IPTC/XMP)
    Returns caption string or None if not found"""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        from PIL import IptcImagePlugin
        
        if not os.path.exists(img_path):
            return None
        
        img = Image.open(img_path)
        caption = None
        
        # Try EXIF UserComment (tag 37510) - this is the "Comments" field
        # Use piexif for better UserComment reading support
        try:
            import piexif
            with open(img_path, 'rb') as f:
                exif_dict = piexif.load(f.read())
            if 'Exif' in exif_dict and piexif.ExifIFD.UserComment in exif_dict['Exif']:
                comment_data = exif_dict['Exif'][piexif.ExifIFD.UserComment]
                if comment_data:
                    if isinstance(comment_data, bytes):
                        # UserComment format: encoding prefix (e.g., "ASCII\0\0\0" or "UNICODE\0\0\0\0") + text
                        # Try to decode, skipping encoding prefix if present
                        try:
                            # Check for common encoding prefixes
                            if comment_data.startswith(b'ASCII\x00\x00\x00'):
                                caption = comment_data[8:].decode('ascii', errors='replace').strip()
                            elif comment_data.startswith(b'UNICODE\x00\x00\x00\x00'):
                                caption = comment_data[12:].decode('utf-16', errors='replace').strip()
                            elif comment_data.startswith(b'JIS\x00\x00\x00\x00\x00'):
                                caption = comment_data[8:].decode('shift_jis', errors='replace').strip()
                            else:
                                # Try UTF-8 directly
                                caption = comment_data.decode('utf-8', errors='replace').strip()
                            if caption:
                                return caption
                        except Exception:
                            pass
                    elif isinstance(comment_data, str):
                        return comment_data.strip()
        except ImportError:
            # piexif not available, try PIL
            pass
        except Exception:
            pass
        
        # Fallback: Try PIL's getexif() for UserComment
        try:
            exif = img.getexif()
            if exif and 37510 in exif:
                caption = exif[37510]
                if caption:
                    if isinstance(caption, str):
                        return caption.strip()
                    elif isinstance(caption, bytes):
                        # Try to decode, handling encoding prefix
                        if caption.startswith(b'ASCII\x00\x00\x00'):
                            return caption[8:].decode('ascii', errors='replace').strip()
                        else:
                            return caption.decode('utf-8', errors='replace').strip()
        except Exception:
            pass
        
        # Try EXIF ImageDescription (tag 270) as fallback
        try:
            exif = img.getexif()
            if exif:
                # EXIF ImageDescription is tag 270
                if 270 in exif:
                    caption = exif[270]
                    if caption and isinstance(caption, str) and caption.strip():
                        return caption.strip()
        except Exception:
            pass
        
        # Try IPTC Caption-Abstract
        try:
            iptc = IptcImagePlugin.getiptcinfo(img)
            if iptc:
                # IPTC Caption-Abstract is tag (2, 120)
                if (2, 120) in iptc:
                    caption_data = iptc[(2, 120)]
                    if caption_data:
                        # IPTC data can be bytes, string, or list
                        if isinstance(caption_data, bytes):
                            caption = caption_data.decode('utf-8', errors='replace').strip()
                        elif isinstance(caption_data, str):
                            caption = caption_data.strip()
                        elif isinstance(caption_data, (list, tuple)) and len(caption_data) > 0:
                            # Take first element if it's a list
                            first_item = caption_data[0]
                            if isinstance(first_item, bytes):
                                caption = first_item.decode('utf-8', errors='replace').strip()
                            elif isinstance(first_item, str):
                                caption = first_item.strip()
                            else:
                                caption = str(first_item).strip()
                        else:
                            caption = str(caption_data).strip()
                        
                        if caption and len(caption) > 0:
                            return caption
        except Exception as e:
            # Silently fail IPTC reading - not all images have IPTC data
            pass
        
        # Try XMP (if available via Pillow)
        try:
            # XMP data might be in the image info
            if hasattr(img, 'info') and 'exif' in img.info:
                # Some XMP data might be embedded in EXIF
                pass
        except Exception:
            pass
        
        return None
    except Exception as e:
        print(f"[Caption] Error reading caption from {img_path}: {e}")
        return None

def set_image_caption(img_path, caption):
    """Write caption to image metadata (EXIF/IPTC)
    Returns True if successful, False otherwise
    
    Note: PIL's EXIF writing is limited. For best results, use piexif library.
    This function will try piexif first, then fall back to PIL's basic capabilities."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        if not os.path.exists(img_path):
            return False
        
        # Try using piexif library (better EXIF support)
        try:
            import piexif
            import tempfile
            import shutil
            
            # Read current EXIF data (or create new if none exists)
            try:
                with open(img_path, 'rb') as f:
                    exif_dict = piexif.load(f.read())
            except Exception:
                # No existing EXIF, create new dict
                exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
            
            # Set UserComment (tag 37510 in Exif IFD) - this is the "Comments" field in image viewers
            # UserComment format: 8-byte encoding identifier + text bytes
            # Format: "ASCII\0\0\0" + text (for ASCII) or "UNICODE\0\0\0\0" + text (for Unicode)
            if 'Exif' not in exif_dict:
                exif_dict['Exif'] = {}
            
            if caption:
                # Use ASCII encoding prefix for better compatibility
                # Format: "ASCII\0\0\0" (8 bytes) + text bytes
                caption_bytes = caption.encode('utf-8')
                user_comment = b'ASCII\x00\x00\x00' + caption_bytes
            else:
                user_comment = b'ASCII\x00\x00\x00'
            
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment
            
            # Convert EXIF dict to bytes
            exif_bytes = piexif.dump(exif_dict)
            
            # Read original image data
            with open(img_path, 'rb') as f:
                img_data = f.read()
            
            # Create temporary file for output
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            try:
                os.close(temp_fd)
                
                # Insert EXIF into image and write to temp file
                piexif.insert(exif_bytes, img_data, temp_path)
                
                # Replace original file with updated one
                shutil.move(temp_path, img_path)
                return True
            except Exception as e:
                # Clean up temp file on error
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
                raise e
        except ImportError:
            # piexif not available, try PIL's basic approach
            # Note: PIL's EXIF writing is very limited
            print("[Caption] piexif not available. Install with: pip install piexif for better EXIF support.")
            
            # For now, we'll save a note that piexif is recommended
            # PIL can read EXIF but writing is problematic without piexif
            return False
        except Exception as e:
            print(f"[Caption] Error using piexif: {e}, trying PIL fallback...")
            # Fall through to PIL attempt below
            pass
        
        # Fallback: Try PIL (limited support)
        try:
            img = Image.open(img_path)
            img_format = img.format or 'JPEG'
            
            # PIL's EXIF writing is very limited - we can't easily modify existing EXIF
            # For now, just return False and recommend piexif
            print(f"[Caption] PIL cannot reliably write EXIF. Install piexif for full support.")
            return False
        except Exception as e:
            print(f"[Caption] Error with PIL fallback: {e}")
            return False
            
    except Exception as e:
        print(f"[Caption] Error setting caption for {img_path}: {e}")
        return False

@app.route('/api/image/preview')
def api_image_preview():
    """Get current image as thumbnail preview"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    if not slideshow_instance.current_img:
        return jsonify({'error': 'No image loaded'}), 404
    
    try:
        from PIL import Image
        from flask import send_file
        import io
        
        img_path = get_image_path()
        if not img_path:
            return jsonify({'error': 'Image file not found'}), 404
        
        # Create thumbnail (max 400x400, maintains aspect ratio)
        img = Image.open(img_path)
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        img_bytes.seek(0)
        
        return send_file(img_bytes, mimetype='image/jpeg')
    except ImportError:
        # Fallback: serve original image if PIL not available
        img_path = get_image_path()
        if img_path:
            if slideshow_instance.current_img.startswith("uploaded/"):
                upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
                if upload_dir:
                    upload_dir = os.path.expanduser(upload_dir)
                    actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                    return send_from_directory(upload_dir, actual_path)
            else:
                return send_from_directory(slideshow_instance.folder, slideshow_instance.current_img)
        return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        print(f"[Web] Error generating preview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/full')
def api_image_full():
    """Get current image at full resolution"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    if not slideshow_instance.current_img:
        return jsonify({'error': 'No image loaded'}), 404
    
    try:
        img_path = get_image_path()
        if not img_path:
            return jsonify({'error': 'Image file not found'}), 404
        
        if slideshow_instance.current_img.startswith("uploaded/"):
            upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
            if upload_dir:
                upload_dir = os.path.expanduser(upload_dir)
                actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                return send_from_directory(upload_dir, actual_path)
        else:
            return send_from_directory(slideshow_instance.folder, slideshow_instance.current_img)
    except Exception as e:
        print(f"[Web] Error serving full image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/caption', methods=['GET'])
def api_get_caption():
    """Get caption from current image metadata"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    if not slideshow_instance.current_img:
        return jsonify({'error': 'No image loaded'}), 404
    
    try:
        img_path = get_image_path()
        if not img_path:
            return jsonify({'error': 'Image file not found'}), 404
        
        caption = get_image_caption(img_path)
        return jsonify({'status': 'ok', 'caption': caption or ''})
    except Exception as e:
        print(f"[Web] Error getting caption: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/caption', methods=['POST'])
def api_set_caption():
    """Set caption in current image metadata"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    if not slideshow_instance.current_img:
        return jsonify({'error': 'No image loaded'}), 404
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        caption = data.get('caption', '').strip()
        img_path = get_image_path()
        if not img_path:
            return jsonify({'error': 'Image file not found'}), 404
        
        # Check if file is writable
        if not os.access(img_path, os.W_OK):
            return jsonify({'error': 'Image file is not writable'}), 403
        
        success = set_image_caption(img_path, caption)
        if success:
            # Clear cached caption so it reloads on next draw
            if slideshow_instance._cached_caption_image == slideshow_instance.current_img:
                slideshow_instance._cached_caption = None
                slideshow_instance._cached_caption_image = None
            # Force redraw to show updated caption immediately
            slideshow_instance.force_redraw = True
            return jsonify({'status': 'ok', 'message': 'Caption saved successfully'})
        else:
            return jsonify({'error': 'Failed to save caption. Make sure piexif is installed: pip install piexif'}), 500
    except Exception as e:
        print(f"[Web] Error setting caption: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/next', methods=['POST'])
def api_next():
    """Go to next image"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    with slideshow_instance.control_lock:
        slideshow_instance.next_image()
        slideshow_instance.force_redraw = True  # Force immediate redraw
        slideshow_instance.image_display_start_time = time.time()  # Reset countdown
    
    return jsonify({'status': 'ok', 'current_image': slideshow_instance.current_img})

@app.route('/api/prev', methods=['POST'])
def api_prev():
    """Go to previous image"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    with slideshow_instance.control_lock:
        slideshow_instance.prev_image()
        slideshow_instance.force_redraw = True  # Force immediate redraw
        slideshow_instance.image_display_start_time = time.time()  # Reset countdown
    
    return jsonify({'status': 'ok', 'current_image': slideshow_instance.current_img})

@app.route('/api/pause', methods=['POST'])
def api_pause():
    """Toggle pause state"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    slideshow_instance.paused = not slideshow_instance.paused
    status = 'paused' if slideshow_instance.paused else 'playing'
    print(f"[Web] Slideshow {status}")
    
    return jsonify({'status': 'ok', 'paused': slideshow_instance.paused})

@app.route('/api/display', methods=['POST'])
def api_display():
    """Control display on/off"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    data = request.json
    action = data.get('action')  # 'on', 'off', or 'auto'
    
    if action == 'on':
        slideshow_instance.manual_display_override = True
    elif action == 'off':
        slideshow_instance.manual_display_override = False
    elif action == 'auto':
        slideshow_instance.manual_display_override = None
    else:
        return jsonify({'error': 'Invalid action'}), 400
    
    # Force immediate redraw to apply display changes
    slideshow_instance.force_redraw = True
    
    print(f"[Web] Display set to: {action}")
    return jsonify({'status': 'ok', 'action': action})

@app.route('/api/system/shutdown', methods=['POST'])
def api_shutdown():
    """Shutdown the system"""
    global power_action_in_progress, power_action_cancel_event
    
    # Check if a power action is already in progress
    if power_action_in_progress:
        return jsonify({'error': 'A shutdown or restart is already in progress'}), 409
    
    data = request.json or {}
    countdown = int(data.get('countdown', 10))
    
    print(f"[Web] Shutdown requested with {countdown}s countdown")
    
    # Set flag to prevent multiple requests
    power_action_in_progress = True
    
    # Create cancel event
    import threading
    power_action_cancel_event = threading.Event()
    
    # Send notification if telegram is enabled
    if telegram_notifier:
        telegram_notifier.notify_system_alert(
            'shutdown',
            f'Manual shutdown initiated from web UI (countdown: {countdown}s)'
        )
    
    # Start shutdown in a separate thread to allow response to be sent
    def do_shutdown():
        global power_action_in_progress, power_action_cancel_event
        import time
        time.sleep(0.5)  # Give time for response to be sent
        
        try:
            if pygame.get_init():
                screen = pygame.display.get_surface()
            print(f"[System] Shutdown initiated, countdown={countdown}s")
            
            # Countdown with cancel check
            for remaining in range(countdown, 0, -1):
                if power_action_cancel_event and power_action_cancel_event.is_set():
                    print("[System] Shutdown cancelled")
                    if screen:
                        screen.fill((0, 0, 0))
                        font = pygame.font.SysFont(None, 48)
                        text = font.render("Shutdown cancelled", True, (255, 255, 255))
                        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                        screen.blit(text, rect)
                        pygame.display.flip()
                        time.sleep(1)  # Brief message, then immediately restore
                    
                    # Force redraw to show image again immediately
                    if slideshow_instance:
                        slideshow_instance.force_redraw = True
                        # Trigger immediate redraw by drawing now
                        try:
                            slideshow_instance.draw_image()
                            pygame.display.flip()
                        except:
                            pass  # If draw fails, force_redraw will handle it on next loop
                    
                    power_action_in_progress = False
                    power_action_cancel_event = None
                    return
                
                if screen:
                    screen.fill((0, 0, 0))
                    font = pygame.font.SysFont(None, 48)
                    text = font.render(f"Shutting down in {remaining} seconds...", True, (255, 255, 255))
                    rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                    screen.blit(text, rect)
                    pygame.display.flip()
                else:
                    print(f"Shutting down in {remaining} seconds...")
                time.sleep(1)
            
            # Execute shutdown - try Linux command, catch failure on Windows
            try:
                subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # On Windows or if command fails
                print("[System] Shutdown command not available")
        except subprocess.CalledProcessError as e:
            print(f"Failed to shutdown: {e}")
            power_action_in_progress = False
            power_action_cancel_event = None
    
    thread = threading.Thread(target=do_shutdown, daemon=True)
    thread.start()
    
    return jsonify({'status': 'ok', 'message': f'Shutdown initiated with {countdown}s countdown'})

@app.route('/api/system/restart', methods=['POST'])
def api_restart():
    """Restart the system"""
    global power_action_in_progress, power_action_cancel_event
    
    # Check if a power action is already in progress
    if power_action_in_progress:
        return jsonify({'error': 'A shutdown or restart is already in progress'}), 409
    
    data = request.json or {}
    countdown = int(data.get('countdown', 10))
    
    print(f"[Web] Restart requested with {countdown}s countdown")
    
    # Set flag to prevent multiple requests
    power_action_in_progress = True
    
    # Create cancel event
    import threading
    power_action_cancel_event = threading.Event()
    
    # Send notification if telegram is enabled
    if telegram_notifier:
        telegram_notifier.notify_system_alert(
            'restart',
            f'Manual restart initiated from web UI (countdown: {countdown}s)'
        )
    
    # Start restart in a separate thread
    def do_restart():
        global power_action_in_progress, power_action_cancel_event
        import time
        time.sleep(0.5)  # Give time for response to be sent
        
        try:
            if pygame.get_init():
                screen = pygame.display.get_surface()
            print(f"[System] Restart initiated, countdown={countdown}s")
            
            # Countdown with cancel check
            for remaining in range(countdown, 0, -1):
                if power_action_cancel_event and power_action_cancel_event.is_set():
                    print("[System] Restart cancelled")
                    if screen:
                        screen.fill((0, 0, 0))
                        font = pygame.font.SysFont(None, 48)
                        text = font.render("Restart cancelled", True, (255, 255, 255))
                        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                        screen.blit(text, rect)
                        pygame.display.flip()
                        time.sleep(1)  # Brief message, then immediately restore
                    
                    # Force redraw to show image again immediately
                    if slideshow_instance:
                        slideshow_instance.force_redraw = True
                        # Trigger immediate redraw by drawing now
                        try:
                            slideshow_instance.draw_image()
                            pygame.display.flip()
                        except:
                            pass  # If draw fails, force_redraw will handle it on next loop
                    
                    power_action_in_progress = False
                    power_action_cancel_event = None
                    return
                
                if screen:
                    screen.fill((0, 0, 0))
                    font = pygame.font.SysFont(None, 48)
                    text = font.render(f"Restarting in {remaining} seconds...", True, (255, 255, 255))
                    rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                    screen.blit(text, rect)
                    pygame.display.flip()
                else:
                    print(f"Restarting in {remaining} seconds...")
                time.sleep(1)
            
            # Restart command - try Linux command, catch failure on Windows
            try:
                subprocess.run(["sudo", "reboot"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # On Windows or if command fails
                print("[System] Restart command not available")
        except subprocess.CalledProcessError as e:
            print(f"Failed to restart: {e}")
            power_action_in_progress = False
            power_action_cancel_event = None
    
    thread = threading.Thread(target=do_restart, daemon=True)
    thread.start()
    
    return jsonify({'status': 'ok', 'message': f'Restart initiated with {countdown}s countdown'})

@app.route('/api/system/cancel', methods=['POST'])
def api_cancel_power_action():
    """Cancel ongoing shutdown or restart"""
    global power_action_in_progress

    if not power_action_in_progress:
        return jsonify({'error': 'No power action in progress'}), 400
    
    if power_action_cancel_event:
        power_action_cancel_event.set()
        print("[Web] Power action cancelled by user")
        # Note: Don't clear power_action_cancel_event here - let the thread detect and clear it
        # We can reset the flag now so user can start another action if needed
        power_action_in_progress = False
        return jsonify({'status': 'ok', 'message': 'Power action cancelled'})
    else:
        return jsonify({'error': 'Cannot cancel at this time'}), 400

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload new image to separate upload directory"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        return jsonify({'error': 'Invalid file type. Only JPG and PNG allowed'}), 400
    
    filename = secure_filename(file.filename)
    
    # Determine upload directory
    upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
    if not upload_dir:
        # Default: create 'uploaded' subdirectory in images directory
        upload_dir = os.path.join(slideshow_instance.folder, 'uploaded')
    else:
        # Use configured upload directory
        upload_dir = os.path.expanduser(upload_dir)  # Support ~ for home directory
    
    # Create upload directory if it doesn't exist
    try:
        os.makedirs(upload_dir, exist_ok=True)
        # Verify directory was actually created
        if not os.path.exists(upload_dir):
            return jsonify({'error': f'Failed to create upload directory: {upload_dir}'}), 500
        if not os.path.isdir(upload_dir):
            return jsonify({'error': f'Upload path exists but is not a directory: {upload_dir}'}), 500
        print(f"[Web] Upload directory: {upload_dir}")
    except PermissionError as e:
        return jsonify({'error': f'Permission denied creating upload directory: {e}'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to create upload directory: {e}'}), 500
    
    # Verify directory is writable
    try:
        test_file = os.path.join(upload_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception as e:
        return jsonify({'error': f'Upload directory is not writable: {e}'}), 500
    
    # Save file to upload directory
    filepath = os.path.join(upload_dir, filename)
    
    # Handle filename conflicts (add number if exists)
    base_name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base_name}_{counter}{ext}"
        filepath = os.path.join(upload_dir, filename)
        counter += 1
    
    try:
        file.save(filepath)
        print(f"[Web] Uploaded new image: {filename} to {upload_dir}")
    except Exception as e:
        error_msg = f'Failed to save file: {e}'
        if telegram_notifier:
            telegram_notifier.notify_error(error_msg, f"Upload: {filename}")
        return jsonify({'error': error_msg}), 500
    
    # If caption provided, save it to image metadata
    caption = request.form.get('caption', '').strip()
    if caption:
        try:
            success = set_image_caption(filepath, caption)
            if success:
                print(f"[Web] Added caption to uploaded image: {filename}")
            else:
                print(f"[Web] Warning: Failed to save caption to {filename}")
        except Exception as e:
            print(f"[Web] Error saving caption to {filename}: {e}")
            # Don't fail the upload if caption saving fails
    
    # Refresh images to include the new upload (refresh_images scans recursively)
    slideshow_instance.refresh_images()
    
    # Notify Telegram of upload
    if telegram_notifier:
        telegram_notifier.notify_upload(filename)
    
    return jsonify({'status': 'ok', 'filename': filename, 'upload_dir': upload_dir, 'caption_added': bool(caption)})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings"""
    if slideshow_instance is None:
        return jsonify({'error': 'Slideshow not initialized'}), 503
    
    if request.method == 'GET':
        return jsonify({
            'show_time': slideshow_instance.config.get('show_time', 'true'),
            'show_date': slideshow_instance.config.get('show_date', 'true'),
            'show_temperature': slideshow_instance.config.get('show_temperature', 'true'),
            'show_weather_code': slideshow_instance.config.get('show_weather_code', 'true'),
            'show_filename': slideshow_instance.config.get('show_filename', 'true'),
            'show_caption': slideshow_instance.config.get('show_caption', 'true'),
            'delay_seconds': slideshow_instance.display_time_seconds,
            'display_off_time': slideshow_instance.config.get('display_off_time', '23:00'),
            'display_on_time': slideshow_instance.config.get('display_on_time', '05:00'),
            'location_city_suburb': slideshow_instance.config.get('location_city_suburb', 'Sydney, Australia'),
            'display_correction_horizontal': slideshow_instance.config.get('display_correction_horizontal', '1.0'),
            'display_correction_vertical': slideshow_instance.config.get('display_correction_vertical', '1.0'),
            'ui_text_alpha': slideshow_instance.config.get('ui_text_alpha', '192'),
            'weather_update_seconds': slideshow_instance.config.get('weather_update_seconds', '900'),
            'upload_directory': slideshow_instance.config.get('upload_directory', ''),
            'images_directory': slideshow_instance.folder,
            'shutdown_on_display_off': slideshow_instance.config.get('shutdown_on_display_off', 'true'),
            'shutdown_countdown_seconds': slideshow_instance.config.get('shutdown_countdown_seconds', '10')
        })
    
    elif request.method == 'POST':
        data = request.json
        
        # Track changes for Telegram notifications
        # Update config values
        if 'show_time' in data:
            old_val = slideshow_instance.config.get('show_time', 'true')
            new_val = str(data['show_time']).lower()
            slideshow_instance.config['show_time'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('show_time', old_val, new_val)
        if 'show_date' in data:
            old_val = slideshow_instance.config.get('show_date', 'true')
            new_val = str(data['show_date']).lower()
            slideshow_instance.config['show_date'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('show_date', old_val, new_val)
        if 'show_temperature' in data:
            old_val = slideshow_instance.config.get('show_temperature', 'true')
            new_val = str(data['show_temperature']).lower()
            slideshow_instance.config['show_temperature'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('show_temperature', old_val, new_val)
        if 'show_weather_code' in data:
            old_val = slideshow_instance.config.get('show_weather_code', 'true')
            new_val = str(data['show_weather_code']).lower()
            slideshow_instance.config['show_weather_code'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('show_weather_code', old_val, new_val)
        if 'show_filename' in data:
            old_val = slideshow_instance.config.get('show_filename', 'true')
            new_val = str(data['show_filename']).lower()
            slideshow_instance.config['show_filename'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('show_filename', old_val, new_val)
        if 'show_caption' in data:
            old_val = slideshow_instance.config.get('show_caption', 'true')
            new_val = str(data['show_caption']).lower()
            slideshow_instance.config['show_caption'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('show_caption', old_val, new_val)
        if 'delay_seconds' in data:
            old_val = slideshow_instance.display_time_seconds
            new_val = int(data['delay_seconds'])
            slideshow_instance.display_time_seconds = new_val
            # Reset countdown timer when delay changes
            slideshow_instance.image_display_start_time = time.time()
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('delay_seconds', str(old_val), str(new_val))
        if 'display_off_time' in data:
            old_val = slideshow_instance.config.get('display_off_time', '23:00')
            new_val = data['display_off_time']
            slideshow_instance.config['display_off_time'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('display_off_time', old_val, new_val)
        if 'display_on_time' in data:
            old_val = slideshow_instance.config.get('display_on_time', '05:00')
            new_val = data['display_on_time']
            slideshow_instance.config['display_on_time'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('display_on_time', old_val, new_val)
        if 'location_city_suburb' in data:
            old_val = slideshow_instance.config.get('location_city_suburb', 'Sydney, Australia')
            new_val = data['location_city_suburb']
            slideshow_instance.config['location_city_suburb'] = new_val
            # Re-geocode the location
            slideshow_instance.city_suburb = new_val
            lat, lon = get_coords_from_place(new_val)
            if lat and lon:
                slideshow_instance.lat = lat
                slideshow_instance.long = lon
                print(f"[Web] Updated location to {new_val}: lat={lat}, lon={lon}")
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('location_city_suburb', old_val, new_val)
        if 'display_correction_horizontal' in data:
            old_val = slideshow_instance.config.get('display_correction_horizontal', '1.0')
            new_val = str(data['display_correction_horizontal'])
            slideshow_instance.config['display_correction_horizontal'] = new_val
            # Force redraw when correction changes
            slideshow_instance.force_redraw = True
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('display_correction_horizontal', old_val, new_val)
        if 'display_correction_vertical' in data:
            old_val = slideshow_instance.config.get('display_correction_vertical', '1.0')
            new_val = str(data['display_correction_vertical'])
            slideshow_instance.config['display_correction_vertical'] = new_val
            # Force redraw when correction changes
            slideshow_instance.force_redraw = True
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('display_correction_vertical', old_val, new_val)
        if 'ui_text_alpha' in data:
            old_val = slideshow_instance.config.get('ui_text_alpha', '192')
            new_val = str(int(data['ui_text_alpha']))
            slideshow_instance.config['ui_text_alpha'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('ui_text_alpha', old_val, new_val)
        if 'weather_update_seconds' in data:
            old_val = slideshow_instance.config.get('weather_update_seconds', '900')
            new_val = str(int(data['weather_update_seconds']))
            slideshow_instance.config['weather_update_seconds'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('weather_update_seconds', old_val, new_val)
        if 'upload_directory' in data:
            old_val = slideshow_instance.config.get('upload_directory', '')
            new_val = data['upload_directory'].strip()
            slideshow_instance.config['upload_directory'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('upload_directory', old_val or '(empty)', new_val or '(empty)')
        if 'shutdown_on_display_off' in data:
            old_val = slideshow_instance.config.get('shutdown_on_display_off', 'true')
            new_val = str(data['shutdown_on_display_off']).lower()
            slideshow_instance.config['shutdown_on_display_off'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('shutdown_on_display_off', old_val, new_val)
        if 'shutdown_countdown_seconds' in data:
            old_val = slideshow_instance.config.get('shutdown_countdown_seconds', '10')
            new_val = str(int(data['shutdown_countdown_seconds']))
            slideshow_instance.config['shutdown_countdown_seconds'] = new_val
            if telegram_notifier and old_val != new_val:
                telegram_notifier.notify_settings_change('shutdown_countdown_seconds', old_val, new_val)
        if 'images_directory' in data:
            # Update images directory (requires restart to take full effect)
            old_val = slideshow_instance.folder
            new_dir = data['images_directory'].strip()
            # Only refresh if the directory actually changed
            if new_dir != old_val:
                if os.path.exists(new_dir) and os.path.isdir(new_dir):
                    slideshow_instance.folder = new_dir
                    slideshow_instance.config['images_directory'] = new_dir
                    # Refresh images from new directory
                    slideshow_instance.images = []
                    slideshow_instance.history = []
                    slideshow_instance.current_index = -1
                    slideshow_instance.refresh_images()
                    if slideshow_instance.images:
                        slideshow_instance.next_image()
                    print(f"[Web] Images directory changed to: {new_dir}")
                    if telegram_notifier and old_val != new_dir:
                        telegram_notifier.notify_settings_change('images_directory', old_val, new_dir)
                else:
                    return jsonify({'error': 'Invalid directory path'}), 400
            else:
                # Directory hasn't changed, just update config without refreshing
                slideshow_instance.config['images_directory'] = new_dir
        
        # Force a redraw to apply settings immediately
        slideshow_instance.force_redraw = True

        # If display correction changed, need to reload current image
        if 'display_correction_horizontal' in data or 'display_correction_vertical' in data:
            # Clear cached image so it reloads with new scaling
            if hasattr(slideshow_instance, '_cached_image_name'):
                slideshow_instance._cached_image_name = None
        
        # Optionally save to config.ini
        save_to_config = data.get('save_to_config', False)
        if save_to_config:
            config = configparser.ConfigParser()
            if os.path.exists(CONFIG_PATH):
                config.read(CONFIG_PATH)
            
            if 'gallery' not in config:
                config['gallery'] = {}
            
            # Update config file
            for key in ['show_time', 'show_date', 'show_temperature', 'show_weather_code', 
                       'show_filename', 'show_caption', 'display_off_time', 'display_on_time',
                       'location_city_suburb', 'display_correction_horizontal', 'display_correction_vertical',
                       'ui_text_alpha', 'weather_update_seconds', 'upload_directory', 'images_directory',
                       'shutdown_on_display_off', 'shutdown_countdown_seconds']:
                if key in data:
                    config['gallery'][key] = str(data[key])
            
            if 'delay_seconds' in data:
                config['gallery']['delay_seconds'] = str(data['delay_seconds'])
            
            with open(CONFIG_PATH, 'w') as f:
                config.write(f)
            
            print("[Web] Settings saved to config.ini")
        
        print(f"[Web] Settings updated: {data}")
        return jsonify({'status': 'ok'})


def start_web_server(host='0.0.0.0', port=5000):
    """Start Flask web server in background thread"""
    print(f"[Web] Starting web server on http://{host}:{port}")
    
    # Optionally make Flask quieter by disabling Werkzeug request logging
    # Uncomment the next line to suppress HTTP request logs in console/logs
    # logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app.run(host=host, port=port, debug=False, threaded=True)


# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser(description="Fullscreen slideshow")
    parser.add_argument("--delay", type=int, help="Display time per image in seconds (integer)")
    parser.add_argument(
        "--window-size",
        type=str,
        help="Window size as WIDTHxHEIGHT, e.g. 1280x720. Default is 1024x768."
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Display in fullscreen mode (overrides --window-size if both are set)"
    )
    parser.add_argument(
        "--location-city-suburb",
        type=str,
        help="Location for weather lookups (default from config.ini)"
    )
    parser.add_argument(
        "--images-directory",
        type=str,
        help="Directory containing images (default from config.ini)"
    )
    parser.add_argument(
        "--display-off-time",
        type=str,
        help="Time to turn display off (default from config.ini)"
    )
    parser.add_argument(
        "--display-on-time",
        type=str,
        help="Time to turn display on (default from config.ini)"
    )
    args = parser.parse_args()

    # Load config values, overridden by command-line args if provided
    location_city_suburb = args.location_city_suburb or get_config_value("location_city_suburb")
    images_directory = args.images_directory or get_config_value("images_directory")
    display_off_time = args.display_off_time or get_config_value("display_off_time")
    display_on_time = args.display_on_time or get_config_value("display_on_time")

    # Delay
    if args.delay is not None:
        display_time_seconds = args.delay
    else:
        try:
            display_time_seconds = get_int_config("delay_seconds", 10)
        except Exception:
            display_time_seconds = 10

    # Window size and fullscreen
    fullscreen = args.fullscreen
    window_size_str = args.window_size or get_config_value("window_size", "1024x768")
    fullscreen_config = get_bool_config("fullscreen", True)
    if not fullscreen:
        if window_size_str.lower() == "fullscreen":
            fullscreen = True
        elif fullscreen_config:
            fullscreen = True

    if not fullscreen:
        try:
            width, height = map(int, window_size_str.lower().split("x"))
            window_size = (width, height)
        except Exception:
            print("Invalid window size format. Use WIDTHxHEIGHT, e.g. 1280x720. Falling back to 1024x768.")
            window_size = (1024, 768)

    print(f"[Startup] Overriding config: images_directory={images_directory}, "
          f"delay={display_time_seconds}s, fullscreen={fullscreen}")

    # Pygame setup
    pygame.init()
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode(window_size)
    pygame.mouse.set_visible(False)

    # Create config dictionary for Slideshow
    slideshow_config = {
        'location_city_suburb': location_city_suburb,
        'display_off_time': display_off_time,
        'display_on_time': display_on_time,
        'show_time': get_config_value('show_time', 'true'),
        'show_date': get_config_value('show_date', 'true'),
        'show_temperature': get_config_value('show_temperature', 'true'),
        'show_weather_code': get_config_value('show_weather_code', 'true'),
        'show_filename': get_config_value('show_filename', 'true'),
        'show_caption': get_config_value('show_caption', 'true'),
        'ui_text_alpha': get_config_value('ui_text_alpha', '192'),
        'weather_update_seconds': get_config_value('weather_update_seconds', '900'),
        'display_correction_horizontal': get_config_value('display_correction_horizontal', '1.0'),
        'display_correction_vertical': get_config_value('display_correction_vertical', '1.0'),
        'image_history_size': get_config_value('image_history_size', '5'),
        'shutdown_on_display_off': get_config_value('shutdown_on_display_off', 'true'),
        'shutdown_countdown_seconds': get_config_value('shutdown_countdown_seconds', '10')
    }

    # Initialize Telegram notifier
    global telegram_notifier
    telegram_notifier = TelegramNotifier(TELEGRAM_CONFIG)

    # Pass config values to Slideshow
    slideshow = Slideshow(images_directory, screen, display_time_seconds, slideshow_config, telegram_notifier)
    
    # Set global reference for web API
    global slideshow_instance
    slideshow_instance = slideshow
    
    # Send startup notification
    if telegram_notifier:
        telegram_notifier.notify_startup()
    
    # Start web server in background thread
    web_thread = threading.Thread(target=start_web_server, kwargs={'host': '0.0.0.0', 'port': 5000}, daemon=True)
    web_thread.start()
    print("[Startup] Web interface available at http://0.0.0.0:5000")
    
    # Start system monitoring in background thread (lightweight, works without psutil)
    if telegram_notifier:
        monitor_thread = threading.Thread(
            target=monitor_system_resources, 
            args=(telegram_notifier,),
            kwargs={'check_interval': 120},  # Check every 2 minutes (lighter)
            daemon=True
        )
        monitor_thread.start()
        print("[Startup] System monitoring started (lightweight mode)")
    
    # Run slideshow (this blocks)
    try:
        slideshow.run()
    except KeyboardInterrupt:
        print("\n[Shutdown] Interrupted by user")
    finally:
        # Send shutdown notification
        if telegram_notifier:
            telegram_notifier.notify_shutdown()


if __name__ == "__main__":
    main()

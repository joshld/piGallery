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
        "display_off_time": "23:00",
        "display_on_time": "05:00",
        "delay_seconds": "10",
        "window_size": "1024x768",
        "fullscreen": "false",
        "aspect_ratio_landscape": "1.5",
        "aspect_ratio_portrait": "0.667",
        "ui_text_alpha": "192",
        "image_history_size": "5",
        "weather_update_seconds": "900",
        "show_time": "true",
        "show_date": "true",
        "show_temperature": "true",
        "show_weather_code": "true",
        "show_filename": "true"
    }
}

config = configparser.ConfigParser()
if not os.path.exists(CONFIG_PATH):
    config.read_dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "w") as f:
        config.write(f)
else:
    config.read(CONFIG_PATH)

GALLERY_CONFIG = config["gallery"] if "gallery" in config else DEFAULT_CONFIG["gallery"]

print(f"[Startup] Loaded config from {CONFIG_PATH}, using {len(GALLERY_CONFIG)} settings.")

# Print all config.ini settings currently being used
print("[gallery] settings in use:")
for k, v in GALLERY_CONFIG.items():
    print(f"  {k} = {v}")


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
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
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


def scale_image(img, screen_w, screen_h, ar_landscape=1.5, ar_portrait=0.667):
    img_w, img_h = img.get_size()
    if img_w >= img_h:
        scale_factor = screen_h / img_h
        scaled_width = img_w * scale_factor
        target_width = scaled_width * (screen_w / screen_h / ar_portrait)
        new_w = int(min(target_width, screen_w))
        img_scaled = pygame.transform.scale(img, (new_w, screen_h))
    else:
        scale_factor = screen_h / img_h
        scaled_width = img_w * scale_factor
        target_width = scaled_width * (screen_w / screen_h / ar_landscape)
        new_w = int(min(target_width, screen_w))
        img_scaled = pygame.transform.scale(img, (new_w, screen_h))
    x_offset = (screen_w - new_w) // 2
    y_offset = 0
    return img_scaled, x_offset, y_offset, new_w


# ---------------- Slideshow Class ----------------
class Slideshow:
    def __init__(self, folder, screen, display_time_seconds, config_dict):
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()
        self.display_time_seconds = display_time_seconds
        self.config = config_dict

        self.images = []
        self.folder = folder

        self.history = []
        self.forward_stack = []
        self.current_index = -1
        self.current_img = None
        self.total_images = 0

        self.fonts = {
            "filename": pygame.font.SysFont("Arial", 14),
            "time": pygame.font.SysFont(None, 96),
            "date": pygame.font.SysFont(None, 42),
            "temp": pygame.font.SysFont(None, 96),
            "weather": pygame.font.SysFont(None, 42),
        }

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
            print(f"[Error] Too many missing files, stopping image search")
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
            print(f"[Slideshow] {status_msg}")
        
        if self.current_img:
            img_path = os.path.join(self.folder, self.current_img)
            try:
                img = pygame.image.load(img_path)
                ar_landscape = float(self.config.get('aspect_ratio_landscape', '1.5'))
                ar_portrait = float(self.config.get('aspect_ratio_portrait', '0.667'))
                img_scaled, x_off, y_off, new_w = scale_image(img, self.screen_w, self.screen_h, ar_landscape, ar_portrait)
                self.screen.blit(img_scaled, (x_off, y_off))
                print(f"[Slideshow] Drawing {self.current_img} scaled to {new_w}x{self.screen_h}")
            except pygame.error as e:
                print(f"[Error] Failed to load image {self.current_img}: {e}")
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
            self.screen.blit(time_surf, (10, 10))

        # date
        show_date = self.config.get('show_date', 'true').lower() == 'true'
        if show_date:
            date_surf = self.fonts["date"].render(now.strftime("%d %b %y"), True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            date_surf.set_alpha(text_alpha)
            self.screen.blit(date_surf, (10, 72))

        # weather
        show_temperature = self.config.get('show_temperature', 'true').lower() == 'true'
        show_weather_code = self.config.get('show_weather_code', 'true').lower() == 'true'
        if show_temperature or show_weather_code:
            self.update_weather()
        if show_temperature and self.current_temp:
            temp_surf = self.fonts["temp"].render(self.current_temp, True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            temp_surf.set_alpha(text_alpha)
            self.screen.blit(temp_surf, (self.screen_w - temp_surf.get_width() - 10, 10))
        if show_weather_code and self.current_weather:
            weather_surf = self.fonts["weather"].render(self.current_weather, True, self.text_color)
            text_alpha = int(self.config.get('ui_text_alpha', '192'))
            weather_surf.set_alpha(text_alpha)
            self.screen.blit(weather_surf, (self.screen_w - weather_surf.get_width() - 10, 72))

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
            for root, _, files in os.walk(self.folder):
                for f in files:
                    if f.lower().endswith((".jpg", ".jpeg", ".png")):
                        # Store relative path from base folder
                        rel_path = os.path.relpath(os.path.join(root, f), self.folder)
                        if rel_path not in self.history and rel_path != self.current_img:
                            new_images.append(rel_path)
        except PermissionError as e:
            print(f"[Error] Permission denied accessing {self.folder}: {e}")
            return
        except Exception as e:
            print(f"[Error] Failed to scan images directory: {e}")
            return
            
        if new_images:
            random.shuffle(new_images)
            self.images.extend(new_images)
        print(f"[Slideshow] Found {len(new_images)} new images, total queue={len(self.images)}")

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
                    self.total_images = len(self.images)

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

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.forward_stack.append(self.history[self.current_index])
            self.current_img = self.history[self.current_index]
            print(f"[Slideshow] Previous image {self.current_index+1}/{self.total_images}: {self.current_img}")

    def is_display_on(self):
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
            if display_should_be_on:
                self.set_display_power(True)
                self.next_image()
                self.draw_image()
                pygame.display.flip()
                display_was_on = True
            else:
                if display_was_on:
                    print("[Display] Display off time reached, blanking screen")
                    display_was_on = False
                self.draw_blank_screen()
                pygame.display.flip()
                self.set_display_power(False)
                # Removed automatic shutdown - just blank the display

            start_time = time.time()
            while time.time() - start_time < self.display_time_seconds:
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
                            self.prev_image()
                            start_time = 0
                            break
                clock.tick(60)


# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser(description="Fullscreen slideshow")
    parser.add_argument("--delay", type=float, help="Display time per image in seconds")
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
            display_time_seconds = float(get_config_value("delay_seconds", 10))
        except Exception:
            display_time_seconds = 10

    # Window size and fullscreen
    fullscreen = args.fullscreen
    window_size_str = args.window_size or get_config_value("window_size", "1024x768")
    fullscreen_config = get_config_value("fullscreen", "false").lower() == "true"
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
        'ui_text_alpha': get_config_value('ui_text_alpha', '192'),
        'weather_update_seconds': get_config_value('weather_update_seconds', '900'),
        'aspect_ratio_landscape': get_config_value('aspect_ratio_landscape', '1.5'),
        'aspect_ratio_portrait': get_config_value('aspect_ratio_portrait', '0.667'),
        'image_history_size': get_config_value('image_history_size', '5')
    }

    # Pass config values to Slideshow
    slideshow = Slideshow(images_directory, screen, display_time_seconds, slideshow_config)
    slideshow.run()


if __name__ == "__main__":
    main()

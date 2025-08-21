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
        "delay": "10",
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
AR_LANDSCAPE = get_float_config("aspect_ratio_landscape", 1.5)
AR_PORTRAIT = get_float_config("aspect_ratio_portrait", 0.667)
TEXT_ALPHA = get_int_config("ui_text_alpha", 192)
HISTORY_SIZE = get_int_config("image_history_size", 5)
WEATHER_UPDATE_SECONDS = get_int_config("weather_update_seconds", 15 * 60)
# LOCATION_CITY_SUBURB, IMAGES_DIRECTORY, DISPLAY_OFF_TIME, DISPLAY_ON_TIME are now loaded from config.ini

# Text overlay display toggles
SHOW_TIME = get_bool_config("show_time", True)
SHOW_DATE = get_bool_config("show_date", True)
SHOW_TEMPERATURE = get_bool_config("show_temperature", True)
SHOW_WEATHER_CODE = get_bool_config("show_weather_code", True)
SHOW_FILENAME = get_bool_config("show_filename", True)

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
    location = geolocator.geocode(place_name, timeout=3)
    return (location.latitude, location.longitude) if location else (None, None)


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


def scale_image(img, screen_w, screen_h):
    img_w, img_h = img.get_size()
    if img_w >= img_h:
        scale_factor = screen_h / img_h
        scaled_width = img_w * scale_factor
        target_width = scaled_width * (screen_w / screen_h / AR_PORTRAIT)
        new_w = int(min(target_width, screen_w))
        img_scaled = pygame.transform.scale(img, (new_w, screen_h))
    else:
        scale_factor = screen_h / img_h
        scaled_width = img_w * scale_factor
        target_width = scaled_width * (screen_w / screen_h / AR_LANDSCAPE)
        new_w = int(min(target_width, screen_w))
        img_scaled = pygame.transform.scale(img, (new_w, screen_h))
    x_offset = (screen_w - new_w) // 2
    y_offset = 0
    return img_scaled, x_offset, y_offset, new_w


# ---------------- Slideshow Class ----------------
class Slideshow:
    def __init__(self, folder, screen, display_time_seconds):
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()
        self.display_time_seconds = display_time_seconds

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

        # Weather
        self.city_suburb = LOCATION_CITY_SUBURB
        self.lat, self.long = 51.5072, 0.1276
        if SHOW_TEMPERATURE or SHOW_WEATHER_CODE:
            self.lat, self.long = get_coords_from_place(self.city_suburb)
        self.current_temp = ""
        self.current_weather = ""
        self.last_weather_update = 0

    def update_weather(self):
        now = time.time()
        if now - self.last_weather_update > WEATHER_UPDATE_SECONDS:
            temp, wind, code = get_weather(self.lat, self.long)
            if temp is not None:
                self.current_temp = f"{temp}°C"
                self.current_weather = f"{WEATHER_CODES[code]}"
                print(f"[Weather] Updated: {self.current_temp}, {self.current_weather}")
            self.last_weather_update = now

    def draw_blank_screen(self):
        self.screen.fill((0, 0, 0))

    def draw_image(self):
        # Skip if file is missing
        while self.current_img:
            img_path = os.path.join(self.folder, self.current_img)
            if os.path.exists(img_path):
                break
            print(f"Missing file: {self.current_img}, skipping...")
            self.next_image()

        self.screen.fill((0, 0, 0))
        new_w = 0
        if self.current_img:
            img_path = os.path.join(self.folder, self.current_img)
            img = pygame.image.load(img_path)
            img_scaled, x_off, y_off, new_w = scale_image(img, self.screen_w, self.screen_h)
            self.screen.blit(img_scaled, (x_off, y_off))
            print(f"[Slideshow] Drawing {self.current_img} scaled to {new_w}x{self.screen_h}")

        now = datetime.datetime.now()

        # filename
        if SHOW_FILENAME:
            text = f"{self.current_img} ({new_w}x{self.screen_h})"
            surf = self.fonts["filename"].render(text, True, self.text_color)
            rect = surf.get_rect(bottomright=(self.screen_w - 10, self.screen_h - 10))
            self.screen.blit(surf, rect)

        # time
        if SHOW_TIME:
            time_surf = self.fonts["time"].render(now.strftime("%I:%M"), True, self.text_color)
            time_surf.set_alpha(TEXT_ALPHA)
            self.screen.blit(time_surf, (10, 10))

        # date
        if SHOW_DATE:
            date_surf = self.fonts["date"].render(now.strftime("%d %b %y"), True, self.text_color)
            date_surf.set_alpha(TEXT_ALPHA)
            self.screen.blit(date_surf, (10, 72))

        # weather
        if SHOW_TEMPERATURE or SHOW_WEATHER_CODE:
            self.update_weather()
        if SHOW_TEMPERATURE:
            temp_surf = self.fonts["temp"].render(self.current_temp, True, self.text_color)
            temp_surf.set_alpha(TEXT_ALPHA)
            self.screen.blit(temp_surf, (self.screen_w - temp_surf.get_width() - 10, 10))
        if SHOW_WEATHER_CODE:
            weather_surf = self.fonts["weather"].render(self.current_weather, True, self.text_color)
            weather_surf.set_alpha(TEXT_ALPHA)
            self.screen.blit(weather_surf, (self.screen_w - weather_surf.get_width() - 10, 72))

    def refresh_images(self):
        # Recursively scan for images (supports subfolders)
        new_images = []
        for root, _, files in os.walk(self.folder):
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg", ".png")):
                    # Store relative path from base folder
                    rel_path = os.path.relpath(os.path.join(root, f), self.folder)
                    if rel_path not in self.history and rel_path != self.current_img:
                        new_images.append(rel_path)
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
            print(f"[Slideshow] Previous image {self.current_index+1}/{len(self.history)}: {self.current_img}")

    def is_display_on(self):
        now = datetime.datetime.now().time()
        off_time = datetime.datetime.strptime(DISPLAY_OFF_TIME, "%H:%M").time()
        on_time = datetime.datetime.strptime(DISPLAY_ON_TIME, "%H:%M").time()

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
        clock = pygame.time.Clock()
        while True:
            if self.is_display_on():
                self.set_display_power(True)
                self.next_image()
                self.draw_image()
                pygame.display.flip()
            else:
                self.draw_blank_screen()
                pygame.display.flip()
                self.set_display_power(False)
                shutdown(10)

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

    global LOCATION_CITY_SUBURB, DISPLAY_OFF_TIME, DISPLAY_ON_TIME
    LOCATION_CITY_SUBURB = location_city_suburb
    DISPLAY_OFF_TIME = display_off_time
    DISPLAY_ON_TIME = display_on_time

    # Pass config values to Slideshow
    slideshow = Slideshow(images_directory, screen, display_time_seconds)
    slideshow.run()


if __name__ == "__main__":
    main()

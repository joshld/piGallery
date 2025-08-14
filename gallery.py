import pygame
import os
import time
import random
import argparse
import datetime
import requests
from geopy.geocoders import Nominatim

# ---------------- Constants ----------------
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

AR_LANDSCAPE = 1.5
AR_PORTRAIT = 0.667
TEXT_ALPHA = 192
HISTORY_SIZE = 5
WEATHER_UPDATE_INTERVAL = 15 * 60  # seconds
LOCATION_CITY_SUBURB = "City, Country"
IMAGES_DIRECTORY = "/your/images/directory/"


# ---------------- Utility Functions ----------------
def get_coords_from_place(place_name: str):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.geocode(place_name, timeout=3)
    return (location.latitude, location.longitude) if location else (None, None)


def get_weather(lat=51.5072, lon=-0.1276):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
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
    def __init__(self, folder, screen, display_time):
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()
        self.display_time = display_time

        self.images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        random.shuffle(self.images)
        self.folder = folder

        self.history = []
        self.forward_stack = []
        self.current_index = -1
        self.current_img = None

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
        self.lat, self.long = get_coords_from_place(self.city_suburb)
        self.current_temp = ""
        self.current_weather = ""
        self.last_weather_update = 0

    def update_weather(self):
        now = time.time()
        if now - self.last_weather_update > WEATHER_UPDATE_INTERVAL:
            temp, wind, code = get_weather(self.lat, self.long)
            if temp is not None:
                self.current_temp = f"{temp}°C"
                self.current_weather = f"{WEATHER_CODES[code]}"
            self.last_weather_update = now

    def draw_image(self):
        img_path = os.path.join(self.folder, self.current_img)
        img = pygame.image.load(img_path)
        img_scaled, x_off, y_off, new_w = scale_image(img, self.screen_w, self.screen_h)
        self.screen.fill((0, 0, 0))
        self.screen.blit(img_scaled, (x_off, y_off))

        # filename
        text = f"{self.current_img} ({new_w}x{self.screen_h})"
        surf = self.fonts["filename"].render(text, True, self.text_color)
        rect = surf.get_rect(bottomright=(self.screen_w - 10, self.screen_h - 10))
        self.screen.blit(surf, rect)

        # time/date
        now = datetime.datetime.now()
        time_surf = self.fonts["time"].render(now.strftime("%I:%M"), True, self.text_color)
        time_surf.set_alpha(TEXT_ALPHA)
        self.screen.blit(time_surf, (10, 10))
        date_surf = self.fonts["date"].render(now.strftime("%d %b %y"), True, self.text_color)
        date_surf.set_alpha(TEXT_ALPHA)
        self.screen.blit(date_surf, (10, 72))

        # weather
        self.update_weather()
        temp_surf = self.fonts["temp"].render(self.current_temp, True, self.text_color)
        temp_surf.set_alpha(TEXT_ALPHA)
        self.screen.blit(temp_surf, (self.screen_w - temp_surf.get_width() - 10, 10))
        weather_surf = self.fonts["weather"].render(self.current_weather, True, self.text_color)
        weather_surf.set_alpha(TEXT_ALPHA)
        self.screen.blit(weather_surf, (self.screen_w - weather_surf.get_width() - 10, 72))

    def next_image(self):
        if self.forward_stack:
            self.current_img = self.forward_stack.pop()
        elif self.current_index < len(self.history) - 1:
            self.current_index += 1
            self.current_img = self.history[self.current_index]
        else:
            if not self.images:
                random.shuffle(self.images)
            self.current_img = self.images.pop()
            self.history.append(self.current_img)
            if len(self.history) > HISTORY_SIZE:
                self.history.pop(0)
            self.current_index = len(self.history) - 1

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.forward_stack.append(self.history[self.current_index])
            self.current_img = self.history[self.current_index]

    def run(self):
        clock = pygame.time.Clock()
        while True:
            self.next_image()
            self.draw_image()
            pygame.display.flip()
            start_time = time.time()
            while time.time() - start_time < self.display_time:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        raise SystemExit
                    if event.type == pygame.KEYDOWN:
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
    parser.add_argument("--delay", type=float, default=10, help="Display time per image in seconds")
    args = parser.parse_args()
    display_time = args.delay

    # Folder with images
    image_folder = IMAGES_DIRECTORY

    # Pygame setup
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)

    slideshow = Slideshow(image_folder, screen, display_time)
    slideshow.run()


if __name__ == "__main__":
    main()

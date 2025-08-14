import pygame
import os
import time
import random
import argparse
import datetime
import requests
from geopy.geocoders import Nominatim


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


def get_coords_from_place(place_name):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.geocode(place_name, timeout=3)
    if location:
        return float(location.latitude), float(location.longitude)
    else:
        return None


def get_location():
    response = requests.get("https://ipinfo.io/json")
    data = response.json()
    lat, lon = data["loc"].split(",")
    return float(lat), float(lon)


def get_weather(lat=51.5072, lon=-0.1276):  # London coords
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        weather = data["current_weather"]
        temp = weather["temperature"]
        wind = weather["windspeed"]
        code = weather["weathercode"]
        return float(temp), float(wind), code
    except Exception as e:
        return f"Weather error: {e}"


#latitude, longitude = get_location()
#print(f"Acquired location: lat: {latitude}, long: {longitude}")

city_suburb = "City, Country"
lat, long = get_coords_from_place(city_suburb)
print(f"Coords for {city_suburb}: lat: {lat}, long: {long}")

temp, wind, code = get_weather(lat, long)
print(f"Current weather for {city_suburb}: {temp}°C, {wind} km/h, {WEATHER_CODES[code]}")
current_temp = f"{temp}°C"
current_weather = f"{WEATHER_CODES[code]}"
last_weather_update = time.time()
weather_update_interval = 15 * 60

parser = argparse.ArgumentParser(description="Fullscreen slideshow")
parser.add_argument("--delay", type=float, default=10,
                    help="Time in seconds to display each image")
args = parser.parse_args()
DISPLAY_TIME = args.delay

# Folder with images
image_folder = "/your/images/directory/"
images = [f for f in os.listdir(image_folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

# Initialize Pygame fullscreen
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)  # hide cursor
SCREEN_W, SCREEN_H = screen.get_size()

# Fonts
pygame.font.init()
font_filename = pygame.font.SysFont('Arial', 14)
font_time = pygame.font.SysFont(None, 96)
font_date = pygame.font.SysFont(None, 42)
font_temp = pygame.font.SysFont(None, 96)
font_weather = pygame.font.SysFont(None, 42)
text_color = (255, 255, 255)  # white

# Typical aspect ratios
AR_landscape = 1.5
# AR_landscape = 1.8
AR_portrait = 0.667
# AR_portrait = 0.1
AR_screen = SCREEN_W / SCREEN_H

clock = pygame.time.Clock()

random.shuffle(images)
history = []      # stores last 5 shown
forward_stack = []  # stores images after going back
current_img = None
current_index = -1  # position in history when navigating

# Loop through images indefinitely
while True:
    # Determine which image to show
    if forward_stack:  # going forward from back history
        current_img = forward_stack.pop()
    elif current_index < len(history) - 1:  # going forward inside history
        current_index += 1
        current_img = history[current_index]
    else:
        if not images:  # reshuffle when we run out
            random.shuffle(images)
        current_img = images.pop()
        history.append(current_img)
        if len(history) > 5:
            history.pop(0)
        current_index = len(history) - 1

    # Load and scale image
    img_path = os.path.join(image_folder, current_img)
    img = pygame.image.load(img_path)
    img_w, img_h = img.get_size()

    if img_w >= img_h:
        scale_factor = SCREEN_H / img_h
        scaled_width = img_w * scale_factor
        target_width = scaled_width * (AR_screen / AR_portrait)
        new_w = int(min(target_width, SCREEN_W))
        img_scaled = pygame.transform.scale(img, (new_w, SCREEN_H))
        x_offset = (SCREEN_W - new_w) // 2
        y_offset = 0
    else:
        scale_factor = SCREEN_H / img_h
        scaled_width = img_w * scale_factor
        target_width = scaled_width * (AR_screen / AR_landscape)
        new_w = int(min(target_width, SCREEN_W))
        img_scaled = pygame.transform.scale(img, (new_w, SCREEN_H))
        x_offset = (SCREEN_W - new_w) // 2
        y_offset = 0

    # Draw image
    screen.fill((0, 0, 0))
    screen.blit(img_scaled, (x_offset, y_offset))

    # Display filename and resolution at bottom center
    text = f"{current_img} ({new_w}x{SCREEN_H})"
    text_surface = font_filename.render(text, True, text_color)
    text_rect = text_surface.get_rect(bottomright=(SCREEN_W - 10, SCREEN_H - 10))
    screen.blit(text_surface, text_rect)

    # Display current time in top-left
    date_time = datetime.datetime.now()
    current_time = date_time.strftime("%I:%M")
    time_surface = font_time.render(current_time, True, text_color).convert_alpha()
    time_surface.set_alpha(128)
    screen.blit(time_surface, (10, 10))
    current_date = date_time.strftime("%d %b %y")
    date_surface = font_date.render(current_date, True, text_color).convert_alpha()
    date_surface.set_alpha(128)
    screen.blit(date_surface, (10, 72))

    # Display weather in top-right
    now = time.time()
    if now - last_weather_update > weather_update_interval:
        temp, wind, code = get_weather(lat, long)
        current_temp = f"{temp}°C"
        current_weather = f"{WEATHER_CODES[code]}"

    temp_surface = font_temp.render(current_temp, True, text_color).convert_alpha()
    temp_surface.set_alpha(128)
    temp_rect = temp_surface.get_rect(topright=(SCREEN_W - 10, 10))
    screen.blit(temp_surface, temp_rect)
    weather_surface = font_weather.render(current_weather, True, text_color).convert_alpha()
    weather_surface.set_alpha(128)
    weather_rect = weather_surface.get_rect(topright=(SCREEN_W - 10, 72))
    screen.blit(weather_surface, weather_rect)

    pygame.display.flip()

    start_time = time.time()
    while time.time() - start_time < DISPLAY_TIME:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:  # Only check keys here
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit
                elif event.key == pygame.K_RIGHT:  # Next image
                    start_time = 0  # exit inner loop early
                    break
                elif event.key == pygame.K_LEFT:   # back
                    if current_index > 0:
                        current_index -= 1
                        current_img = history[current_index]
                        forward_stack.append(current_img)
                        start_time = 0
                        break
            clock.tick(60)

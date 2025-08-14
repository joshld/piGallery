import pygame
import os
import time
import random
import argparse
import datetime
import requests
from geopy.geocoders import Nominatim

def get_coords_from_place(place_name):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.geocode(place_name)
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
        return f"{temp}°C, Wind {wind} km/h"
    except Exception as e:
        return f"Weather error: {e}"

#latitude, longitude = get_location()
#print(f"Acquired location: lat: {latitude}, long: {longitude}")

city_suburb = "City, Country"
lat, long = get_coords_from_place(city_suburb)
print(f"Coords for {city_suburb}: lat: {lat}, long: {long}")

weather = get_weather(lat, long)
print(f"Current weather for {city_suburb}: {weather}") 

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
text_color = (255, 255, 255)  # white

# Typical aspect ratios
AR_landscape = 1.5
AR_portrait = 0.667
AR_screen = SCREEN_W / SCREEN_H

# Loop through images indefinitely
while True:
    random.shuffle(images)
    for img_file in images:
        img_path = os.path.join(image_folder, img_file)
        img = pygame.image.load(img_path)
        img_w, img_h = img.get_size()

        if img_w >= img_h:
            # Landscape → scale height, width adjusted
            scale_factor = SCREEN_H / img_h
            scaled_width = img_w * scale_factor
            target_width = scaled_width * (AR_screen / AR_portrait)
            new_w = int(min(target_width, SCREEN_W))
            img_scaled = pygame.transform.scale(img, (new_w, SCREEN_H))
            x_offset = (SCREEN_W - new_w) // 2
            y_offset = 0
        else:
            # Portrait → scale height, width adjusted
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
        text = f"{img_file} ({new_w}x{SCREEN_H})"
        text_surface = font_filename.render(text, True, text_color)
        text_rect = text_surface.get_rect(bottomright=(SCREEN_W - 10, SCREEN_H - 10))
        screen.blit(text_surface, text_rect)

        # Display current time at top-left
        current_time = datetime.datetime.now().strftime("%H:%M")
        time_surface = font_time.render(current_time, True, text_color)
        screen.blit(time_surface, (10, 10))

        pygame.display.flip()
        time.sleep(DISPLAY_TIME)


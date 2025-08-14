
# piGallery
Displays a slideshow of photos on a Raspberry Pi (or any computer) with a connected display.

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

### 4. Prepare Your Images
Place your images in the folder specified by the `IMAGES_DIRECTORY` variable in `gallery.py`. You can change this path as needed.

### 5. Run the Slideshow
To start the slideshow, run:

```sh
python gallery.py
```

You can also specify the delay between images (in seconds):

```sh
python gallery.py --delay 15
```


### 6. Code Quality: Linting and Type Checking

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


### 7. Notes
- The script is designed for fullscreen display and will hide the mouse cursor.
- Weather and time information is displayed on the screen.
- Some features (like display power control) are specific to Raspberry Pi and may not work on other platforms.

#!/usr/bin/env python3
"""
Photo Frame Web Interface - Setup Verification
Cross-platform setup verification script
"""

import os
import sys
import subprocess
import socket

def main():
    print('============================================')
    print('Photo Frame Web Interface - Setup Verification')
    print('============================================')
    print()

    # Check Python version
    print('1. Checking Python version...')
    try:
        version_info = sys.version_info
        version_str = f'{version_info.major}.{version_info.minor}.{version_info.micro}'
        print(f'Python version: {version_str}')

        if version_info >= (3, 7):
            print('Python 3.7+ is installed [OK]')
        else:
            print(f'Python {version_str} found, but 3.7+ required [FAIL]')
            print('Please upgrade Python: https://python.org/downloads/')
            sys.exit(1)
    except Exception as e:
        print(f'Error checking Python version: {e}')
        sys.exit(1)

    print()

    # Check if required files exist
    print('2. Checking required files...')
    files = ['gallery.py', 'requirements.txt', 'static/index.html']
    missing_files = []

    for file in files:
        if os.path.isfile(file):
            print(f'{file} exists [OK]')
        else:
            print(f'{file} not found [FAIL]')
            missing_files.append(file)

    if missing_files:
        print(f'\nMissing files: {missing_files}')
        sys.exit(1)

    print()

    # Check if dependencies are installed
    print('3. Checking Python dependencies...')
    # Core dependencies from requirements.txt (excluding optional telegram bot)
    dependencies = ['flask', 'flask_cors', 'pygame', 'requests', 'geopy', 'psutil', 'PIL', 'piexif']
    missing_deps = []

    for dep in dependencies:
        try:
            __import__(dep)
            print(f'{dep} is installed [OK]')
        except ImportError:
            print(f'{dep} is not installed [FAIL]')
            missing_deps.append(dep)

    if missing_deps:
        print(f'\nMissing dependencies: {missing_deps}')
        print('Install with: pip install -r requirements.txt')

    print()

    # Check if static folder exists
    print('4. Checking static folder...')
    if os.path.isdir('static'):
        print('static folder exists [OK]')
        html_files = [f for f in os.listdir('static') if f.endswith('.html')]
        print(f'  Found {len(html_files)} HTML file(s)')
    else:
        print('static folder not found [FAIL]')

    print()

    # Check web.py for web server code
    print('5. Checking web.py for web integration...')
    try:
        with open('web.py', 'r', encoding='utf-8') as f:
            content = f.read()

        route_count = content.count('@app.route')
        if route_count > 0:
            print(f'Flask routes found in web.py [OK]')
            print(f'  Found {route_count} API endpoints')
        else:
            print('Flask routes not found in web.py [FAIL]')
    except Exception as e:
        print(f'Error checking web.py: {e}')

    print()

    # Check for config.ini
    print('6. Checking configuration...')
    if os.path.isfile('config.ini'):
        print('config.ini exists [OK]')
    else:
        print('config.ini not found (will be created on first run)')

    print()

    # Check port availability
    print('7. Checking port availability...')
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        if result == 0:
            print('Port 5000 is in use [WARNING]')
            print('  Make sure no other web server is running on port 5000')
        else:
            print('Port 5000 is available [OK]')
    except Exception as e:
        print(f'Could not check port 5000: {e}')

    print()

    # Check file permissions
    print('8. Checking file permissions...')
    try:
        # Check if we can write to current directory (needed for config.ini and uploads)
        test_file = '.permission_test'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print('Write permissions in current directory [OK]')
    except Exception as e:
        print(f'Cannot write to current directory [WARNING]')
        print('  This may cause issues with config saving and uploads')

    print()

    # Network check
    print('9. Network information...')
    try:
        hostname = socket.gethostname()
        print(f'  Hostname: {hostname}')

        try:
            ip = socket.gethostbyname(hostname)
            print(f'  IP Address: {ip}')
            print(f'  Hostname access: http://{hostname}:5000')
            print(f'  IP access: http://{ip}:5000')
        except:
            print('  Could not determine IP address')
            print(f'  Hostname access: http://{hostname}:5000')
    except Exception as e:
        print(f'Error getting network info: {e}')

    print()
    print('============================================')
    print('Setup verification complete!')
    print('============================================')
    print()
    print('Next steps:')
    print('1. If dependencies are missing, run: pip install -r requirements.txt')
    print('2. Edit config.ini to set your images directory')
    print('3. Run the gallery: python gallery.py')
    print('4. Access web interface at: http://[YOUR_IP]:5000 or http://[HOSTNAME]:5000')
    print()

if __name__ == '__main__':
    main()

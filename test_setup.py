#!/usr/bin/env python3
"""
Photo Frame Web Interface - Setup Verification
Cross-platform setup verification script
"""

# ============================================================================
# ULTRA-BASIC CHECKS (before most imports)
# ============================================================================

def check_ultra_basic_requirements():
    """Check absolute minimum requirements before importing most modules."""
    issues = []

    # Check if we can do basic string operations (Python core functionality)
    try:
        test = "test" + "string"
        if len(test) != 10:
            issues.append("[FAIL] Basic string operations failed")
    except:
        issues.append("[FAIL] Python string operations not working")

    # Check if we can do basic math (Python core functionality)
    try:
        if 2 + 2 != 4:
            issues.append("[FAIL] Basic math operations failed")
    except:
        issues.append("[FAIL] Python math operations not working")

    # Now we can safely import sys for more checks
    try:
        import sys
    except ImportError:
        issues.append("[FAIL] Cannot import sys module - critical Python issue")
        print("[FAIL] CRITICAL: Cannot import sys module")
        print("SOLUTION: This suggests a severely corrupted Python installation")
        print("   Try reinstalling Python from: https://python.org/downloads/")
        return False

    # Check if we're on a supported platform
    supported_platforms = ['win32', 'linux', 'darwin', 'cygwin', 'msys']
    if sys.platform not in supported_platforms:
        issues.append(f"[FAIL] Unsupported platform: {sys.platform}")
        issues.append("   Supported: Windows, Linux, macOS")

    # Check command line access
    try:
        if len(sys.argv) < 1:
            issues.append("[FAIL] Command line arguments not accessible")
    except:
        issues.append("[FAIL] sys.argv not available")

    if issues:
        print("[FAIL] CRITICAL: Ultra-basic requirements not met")
        for issue in issues:
            print(issue)
        print()
        print("SOLUTION: This suggests a severely corrupted Python installation")
        print("   Try reinstalling Python from: https://python.org/downloads/")
        return False

    return True

# ============================================================================
# STANDARD IMPORTS (after ultra-basic checks pass)
# ============================================================================

if not check_ultra_basic_requirements():
    # We need to import sys here in case it wasn't available above
    try:
        import sys
        sys.exit(1)
    except:
        exit(1)

# Now we can safely import all modules
import os
import sys
import subprocess
import socket

def check_python_environment():
    """Check if Python environment is properly set up before proceeding."""
    try:
        # Basic Python functionality test
        test_string = "Hello World"
        if len(test_string) != 11:
            raise RuntimeError("Basic Python functionality test failed")

        # Test basic imports that should always be available
        import os
        import sys

        return True
    except Exception as e:
        print("[FAIL] CRITICAL ERROR: Python environment is corrupted or incomplete")
        print(f"Error details: {e}")
        print()
        print("SOLUTION: TROUBLESHOOTING STEPS:")
        print("1. Reinstall Python from: https://python.org/downloads/")
        print("2. Make sure Python is in your PATH environment variable")
        print("3. Try running: python --version")
        print("4. If using virtual environment, activate it first")
        return False

def main():
    # sys should be available now from the ultra-basic checks
    try:
        # First, verify Python environment is working
        if not check_python_environment():
            sys.exit(1)
    except NameError:
        # If sys is not available, we have bigger problems
        print("CRITICAL ERROR: sys module not available in main()")
        print("This indicates the ultra-basic checks failed but didn't exit properly")
        try:
            exit(1)
        except:
            quit()
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
            print(f'[FAIL] Python {version_str} found, but 3.7+ required [FAIL]')
            print('SOLUTION: SOLUTION: Upgrade Python from https://python.org/downloads/')
            print('   Minimum required: Python 3.7.0 or higher')
            sys.exit(1)
    except AttributeError as e:
        print('[FAIL] CRITICAL: sys.version_info not available [FAIL]')
        print('This suggests a corrupted Python installation')
        print('SOLUTION: SOLUTION: Reinstall Python completely')
        sys.exit(1)
    except Exception as e:
        print(f'[FAIL] Error checking Python version: {e} [FAIL]')
        print('SOLUTION: TROUBLESHOOTING:')
        print('   - Try: python --version')
        print('   - Check if Python is properly installed')
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
        except ImportError as e:
            print(f'{dep} is not installed [FAIL]')
            missing_deps.append(dep)
        except Exception as e:
            print(f'{dep} failed to import [ERROR]')
            print(f'   Import error: {e}')
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
            print('[WARNING]  Port 5000 is in use [WARNING]')
            print('   Make sure no other web server is running on port 5000')
            print('   You can change the port in gallery.py if needed')
        else:
            print('Port 5000 is available [OK]')
    except socket.error as e:
        print(f'[WARNING]  Could not check port 5000 (socket error): {e}')
        print('   This might be due to firewall restrictions')
    except Exception as e:
        print(f'[WARNING]  Could not check port 5000: {e}')
        print('   Port check failed, but gallery might still work')

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
    except PermissionError as e:
        print('[FAIL] Cannot write to current directory [CRITICAL]')
        print('   This will prevent config saving and image uploads')
        print('SOLUTION: SOLUTIONS:')
        print('   - Run as administrator/sudo')
        print('   - Change directory permissions')
        print('   - Move project to a writable location')
        sys.exit(1)
    except OSError as e:
        print(f'[FAIL] File system error: {e} [CRITICAL]')
        print('   Check disk space and file system integrity')
        sys.exit(1)
    except Exception as e:
        print(f'[WARNING]  Cannot verify write permissions: {e} [WARNING]')
        print('   Config saving and uploads may not work properly')

    print()

    # Network check
    print('9. Network information...')
    try:
        hostname = socket.gethostname()
        print(f'  Hostname: {hostname}')

        try:
            ip = socket.gethostbyname(hostname)
            print(f'  IP Address: {ip}')
            print(f'  Access URLs:')
            print(f'    Via hostname: http://{hostname}:5000')
            print(f'    Via IP: http://{ip}:5000')
            print(f'    Local access: http://localhost:5000')
        except:
            print('  Could not determine IP address')
            print(f'  Hostname access: http://{hostname}:5000')
            print(f'  Local access: http://localhost:5000')
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
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED]  Setup verification cancelled by user")
        sys.exit(130)
    except Exception as e:
        print("\n[FAIL] UNEXPECTED ERROR during setup verification")
        print(f"Error: {e}")
        print()
        print("DEBUG: DEBUG INFORMATION:")
        print(f"- Python version: {sys.version}")
        print(f"- Platform: {sys.platform}")
        print(f"- Current directory: {os.getcwd()}")
        print()
        print("HELP: If this error persists, please:")
        print("1. Check the error message above")
        print("2. Verify all files are present")
        print("3. Try running: python --version")
        print("4. Report this issue with the debug information above")
        sys.exit(1)

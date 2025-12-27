#!/bin/bash
# Test script for verifying web interface setup

echo "================================================"
echo "Photo Frame Web Interface - Setup Verification"
echo "================================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
python3 --version
if [ $? -eq 0 ]; then
    echo "✓ Python 3 is installed"
else
    echo "✗ Python 3 not found"
    exit 1
fi
echo ""

# Check if required files exist
echo "2. Checking required files..."
files=("gallery.py" "requirements.txt" "static/index.html")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file not found"
        exit 1
    fi
done
echo ""

# Check if dependencies are installed
echo "3. Checking Python dependencies..."
dependencies=("flask" "flask_cors" "pygame" "requests" "geopy")
missing=()

for dep in "${dependencies[@]}"; do
    python3 -c "import $dep" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ $dep is installed"
    else
        echo "✗ $dep is not installed"
        missing+=("$dep")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    echo "Missing dependencies detected. Install with:"
    echo "  pip install -r requirements.txt"
    echo ""
fi
echo ""

# Check if static folder exists
echo "4. Checking static folder..."
if [ -d "static" ]; then
    echo "✓ static folder exists"
    file_count=$(find static -name "*.html" | wc -l)
    echo "  Found $file_count HTML file(s)"
else
    echo "✗ static folder not found"
fi
echo ""

# Check gallery.py for web server code
echo "5. Checking gallery.py for web integration..."
if grep -q "@app.route" gallery.py; then
    echo "✓ Flask routes found in gallery.py"
    route_count=$(grep -c "@app.route" gallery.py)
    echo "  Found $route_count API endpoints"
else
    echo "✗ Flask routes not found in gallery.py"
fi
echo ""

# Check for config.ini
echo "6. Checking configuration..."
if [ -f "config.ini" ]; then
    echo "✓ config.ini exists"
else
    echo "⚠ config.ini not found (will be created on first run)"
fi
echo ""

# Network check
echo "7. Network information..."
if command -v hostname &> /dev/null; then
    echo "  Hostname: $(hostname)"
    if command -v hostname &> /dev/null; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -n "$ip" ]; then
            echo "  IP Address: $ip"
            echo "  Web interface will be available at: http://$ip:5000"
        fi
    fi
fi
echo ""

echo "================================================"
echo "Setup verification complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. If dependencies are missing, run: pip install -r requirements.txt"
echo "2. Edit config.ini to set your images directory"
echo "3. Run the gallery: python gallery.py"
echo "4. Access web interface at: http://[YOUR_IP]:5000"
echo ""

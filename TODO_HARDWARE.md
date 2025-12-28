# piGallery - Hardware Features TODO List

## 🔧 Features Requiring Additional Hardware

These features need extra equipment beyond the base Raspberry Pi setup.

---

### 1. Doorbell/Front Door Camera Display
**Hardware Required:**
- Option A: Pi Camera Module ($5-25)
- Option B: USB Webcam ($15-50)
- Option C: IP Camera/Doorbell (Ring, Nest, etc.)

**Features:**
- [ ] Detect motion at front door
- [ ] Capture image/video when motion detected
- [ ] Display camera view on photo frame (interrupts slideshow)
- [ ] Show live feed for X seconds when doorbell pressed
- [ ] Picture-in-picture mode (camera + slideshow)
- [ ] Save snapshots to gallery
- [ ] Integration with existing doorbell systems (Ring, Nest API)
- [ ] Motion detection sensitivity settings
- [ ] Time-based enabling (only during certain hours)
- [ ] Return to slideshow after timeout

---

## 🎮 Other Hardware Feature Ideas

### 2. Touch Screen Support
**Hardware Required:** Touch screen display
- [ ] Touch gestures (swipe to change image, pinch to zoom)
- [ ] Tap for image info
- [ ] Long press for menu
- [ ] Multi-touch support

### 3. Physical Buttons/Remote
**Hardware Required:** GPIO buttons or IR receiver
- [ ] Next/Previous buttons
- [ ] Pause button
- [ ] Power on/off button
- [ ] IR remote support
- [ ] Custom button mapping

### 4. Motion Sensor
**Hardware Required:** PIR motion sensor
- [ ] Wake frame when motion detected
- [ ] Sleep/dim when no motion for X minutes
- [ ] Power saving mode
- [ ] Adjustable sensitivity

### 5. Ambient Light Sensor
**Hardware Required:** Light sensor (TSL2561, etc.)
- [ ] Auto-adjust screen brightness based on room light
- [ ] Day/night mode switching
- [ ] Color temperature adjustment

### 6. Temperature/Humidity Display
**Hardware Required:** DHT22 or similar sensor
- [ ] Display room temperature on frame
- [ ] Display humidity
- [ ] Historical graphs
- [ ] Alerts for extreme conditions

### 7. RGB LED Strip Integration
**Hardware Required:** WS2812B LED strip
- [ ] Ambient lighting that matches photo colors
- [ ] Backlight effects
- [ ] Mood lighting modes
- [ ] Sync with music (if audio playing)

### 8. Speaker/Audio Output
**Hardware Required:** USB speaker or audio HAT
- [ ] Background music during slideshow
- [ ] Audio for videos
- [ ] Voice notifications
- [ ] Text-to-speech announcements

### 9. Multiple Display Support
**Hardware Required:** Additional display(s)
- [ ] Extend to multiple screens
- [ ] Duplicate mode (same image on all)
- [ ] Different images on each display
- [ ] Video wall mode

### 10. E-Ink Display Option
**Hardware Required:** E-Ink display
- [ ] Ultra-low power consumption
- [ ] Perfect for battery operation
- [ ] Slower refresh but always-on
- [ ] Great for static images

### 11. GPS/Location Module
**Hardware Required:** GPS module
- [ ] Show photos taken near current location
- [ ] Travel mode (shows where photos were taken)
- [ ] Location-based sorting
- [ ] Map overlay with photo locations

### 12. Battery/UPS
**Hardware Required:** UPS HAT or battery pack
- [ ] Battery level display
- [ ] Low battery warnings
- [ ] Graceful shutdown on low battery
- [ ] Portable mode settings

---

## 📋 Notes

- All hardware features are optional enhancements
- Base piGallery works without any of these
- Hardware features can be added independently
- Test thoroughly before deployment
- Check GPIO pin compatibility
- Consider power requirements

---

## 🎯 Priority (When You Get Hardware)

**High Priority:**
1. Doorbell camera display (practical security feature)
2. Motion sensor (power saving)
3. Physical buttons (convenience)

**Medium Priority:**
4. Touch screen (better UX)
5. Light sensor (auto brightness)
6. RGB LED strip (aesthetic)

**Low Priority / Nice to Have:**
7. Temperature sensor
8. GPS module
9. Multiple displays
10. E-ink display
11. Battery/UPS
12. Speaker system

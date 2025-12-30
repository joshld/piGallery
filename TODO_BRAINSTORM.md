# piGallery - Feature TODO List

## 🎯 High Priority / Requested Features

### 1. Image Captions from Metadata ✅ COMPLETED (Major Enhancement)
- [x] Read EXIF/IPTC metadata from images
- [x] Support common caption fields (Title, Description, Caption)
- [x] Overlay captions on display (configurable position)
- [x] Add caption toggle in web UI settings
- [x] Support multi-line captions with word wrap
- [x] Font size/style configuration for captions
- [x] **NEW:** Set/edit captions via web UI (`/api/image/caption`)
- [x] **NEW:** Advanced metadata reading (EXIF, IPTC, XMP, PNG text chunks)
- [x] **NEW:** Multi-format support (JPG, JPEG, PNG)
- [x] **NEW:** Cross-platform metadata compatibility
- [x] **NEW:** Caption validation and error handling

### 2. Shutdown Button ✅ COMPLETED (Expanded)
- [x] Add shutdown button to web UI
- [x] Confirmation dialog before shutdown
- [x] Countdown timer display (e.g., "Shutting down in 10s...")
- [x] Graceful cleanup (save state, close connections)
- [x] Restart button option
- [x] Require sudo permissions handling
- [x] **NEW:** Automatic shutdown at display off time (power savings)
- [x] **NEW:** Configurable countdown duration
- [x] **NEW:** Telegram notifications before shutdown
- [x] **NEW:** Smart plug/timer setup guides
- [x] **NEW:** Manual shutdown via web UI (`/api/system/shutdown`)
- [x] **NEW:** System restart capability (`/api/system/restart`)
- [x] **NEW:** Cancel pending operations (`/api/system/cancel`)

### 2a. Error Detection & Reporting System ⭐ PARTIALLY COMPLETE
- [x] Structured error logging (timestamp, error type, stack trace)
- [x] Error log viewer in web UI (`/api/logs`)
- [x] Error categories (file system, network, display, etc.)
- [x] Automatic error capture (unhandled exceptions)
- [ ] Error notification alerts (email, web UI banner)
- [ ] Error statistics dashboard
- [ ] Export error logs (download as JSON/CSV)
- [ ] Error search and filtering
- [ ] Clear/archive old errors
- [ ] Debug mode with verbose logging
- [ ] Error rate limiting (prevent log spam)
- [ ] Context capture (system state at time of error)
- [x] **NEW:** Enhanced setup verification with comprehensive error checking
- [x] **NEW:** Ultra-basic environment validation (before imports)
- [x] **NEW:** Cross-platform error handling (Windows, Linux, macOS)
- [x] **NEW:** Port availability testing
- [x] **NEW:** File permission validation
- [x] **NEW:** Detailed troubleshooting guidance

### 2b. Delete Uploaded Images ⭐ NEW
- [ ] Identify uploaded vs original images
- [ ] Delete button in web UI (uploaded images only)
- [ ] Confirmation dialog before delete
- [ ] Bulk delete option (select multiple)
- [ ] Move to trash instead of permanent delete
- [ ] Trash/recycle bin viewer
- [ ] Restore from trash option
- [ ] Auto-cleanup trash after X days
- [ ] Delete protection for original images
- [ ] Warning if trying to delete non-uploaded images
- [ ] Disk space freed indicator
- [ ] Delete history/audit log

### 2c. Cross-Platform Support ⭐ COMPLETED
- [x] **Windows compatibility** - Full support for Windows PCs
- [x] **Cross-platform setup** - Works on Windows, Linux, macOS, Raspberry Pi
- [x] **Enhanced setup verification** - `test_setup.py` with comprehensive error checking
- [x] **Platform-specific instructions** - Updated documentation for each platform
- [x] **Unicode-safe error messages** - ASCII-only output for Windows terminal compatibility
- [x] **Network configuration** - IP and hostname access verification
- [x] **File permission validation** - Cross-platform permission checking
- [x] **Port availability testing** - Checks if port 5000 is free on all platforms

### 2d. System Control & Management ⭐ COMPLETED
- [x] **Remote shutdown** - Safe system shutdown via web UI
- [x] **Remote restart** - System restart capability
- [x] **Cancel operations** - Cancel pending shutdown/restart
- [x] **Countdown display** - Visual countdown timer before operations
- [x] **Safety measures** - Confirmation dialogs and notifications
- [x] **Security considerations** - Proper access control for system operations
- [x] **Telegram integration** - Notifications for system operations

### 3. Web UI Color Schemes
- [ ] Light mode (current)
- [ ] Dark mode
- [ ] Auto mode (follow system preference)
- [ ] Custom color scheme editor
- [ ] Save theme preference
- [ ] Smooth theme transition animation

### 4. Image Transitions
- [ ] Fade in/out transition
- [ ] Slide transition (left, right, up, down)
- [ ] Zoom transition
- [ ] Cross-fade transition
- [ ] Configurable transition duration
- [ ] Transition type selector in settings
- [ ] Disable transitions option (instant change)

### 5. Video Support
- [ ] Detect video files (.mp4, .avi, .mov, .mkv)
- [ ] Play videos inline (pygame or opencv)
- [ ] Video playback controls (pause, seek)
- [ ] Audio playback option
- [ ] Video length detection
- [ ] Auto-advance after video completes
- [ ] Video preview thumbnails in web UI
- [ ] Video format conversion helper

---

## 🎨 Web UI Enhancements

### Live Preview Before Save Settings
- [ ] Temporary settings system
- [ ] `/api/settings/preview` endpoint
- [ ] `/api/settings/revert` endpoint
- [ ] Show/hide Save/Revert buttons
- [ ] Unsaved changes warning
- [ ] Preview updates in real-time

### Image Management
- [ ] Delete images via web UI
- [ ] Rename images
- [ ] Move images to folders
- [ ] Bulk operations (delete multiple, move multiple)
- [ ] Image information panel (size, resolution, date)
- [ ] Sort options (date, name, size, random)

### Gallery Features
- [ ] Grid view of recent images
- [ ] Slideshow history viewer (last 50 images)
- [ ] Favorites/star system
- [ ] Rating system (1-5 stars)
- [ ] Filter by favorites/rating
- [ ] Jump to specific image from gallery

### Authentication & Security
- [ ] Basic authentication (username/password)
- [ ] HTTPS support
- [ ] Session management
- [ ] API key for external access
- [ ] IP whitelist option
- [ ] Login page design

---

## ⚡ Performance Optimizations

### Already Discussed (To Implement)
- [ ] Adaptive frame rate (1 FPS off, 5 FPS paused, 10 FPS playing)
- [ ] Time/date surface caching (only re-render when changed)
- [ ] Weather surface caching
- [ ] History size limiting (use existing config)
- [ ] Skip rendering when display off
- [ ] Skip redraw when no changes (paused)
- [ ] Weather throttling at night (1 hour vs 15 min)
- [ ] Image format validation (file size limits)
- [ ] Lazy image loading (progressive scanning)

### Additional Optimizations
- [ ] Image list caching (JSON cache file)
- [ ] Preview image caching on client side
- [ ] Compress weather API responses
- [ ] Batch similar operations
- [ ] Memory usage profiling
- [ ] CPU usage profiling

---

## 🖼️ Display Features

### Caption & Metadata
- [ ] EXIF date/time display
- [ ] Camera/lens information overlay
- [ ] GPS location overlay (if available)
- [ ] Custom text files for captions (imagename.txt)
- [ ] Caption editor in web UI

### Visual Enhancements
- [ ] Ken Burns effect (slow zoom/pan)
- [ ] Image filters (sepia, B&W, vintage)
- [ ] Border/frame options
- [ ] Vignette effect
- [ ] Ambient lighting mode (color cast from image)

### Multi-Display Support
- [ ] Detect multiple displays
- [ ] Choose which display to use
- [ ] Duplicate mode (same image on all)
- [ ] Extended mode (different images)

---

## 📱 Smart Features

### Scheduling & Automation
- [ ] Multiple time schedules (weekday vs weekend)
- [ ] Holiday schedule override
- [ ] Vacation mode
- [ ] Smart brightness (dim at night)
- [ ] Sunrise/sunset based schedule

### Content Management
- [ ] Playlists/collections
- [ ] Weighted random (show some images more often)
- [ ] Time-based playlists (morning, evening, night)
- [ ] Weather-based selection (rainy day photos on rainy days)
- [ ] Seasonal filtering (summer photos in summer)
- [ ] Smart shuffle (avoid repetition)

### AI/ML Features
- [ ] Face detection
- [ ] Face recognition (group by person)
- [ ] Scene detection (beach, mountain, city)
- [ ] Auto-tagging
- [ ] Similar image detection (avoid near-duplicates)
- [ ] Auto-rotation based on content

---

## 🔗 Integration & Connectivity

### Cloud Storage
- [ ] Google Photos integration
- [ ] Dropbox sync
- [ ] OneDrive sync
- [ ] iCloud Photos sync
- [ ] Amazon Photos
- [ ] Auto-download new photos

### Home Automation
- [ ] Home Assistant integration
- [ ] MQTT support
- [ ] Smart home triggers (play on door unlock)
- [ ] Voice control (Alexa/Google Home)
- [ ] Presence detection (pause when no one home)

### Social & Sharing
- [ ] QR code for current image info
- [ ] Share current image via email
- [ ] Generate shareable web link
- [ ] Print current image (network printer)
- [ ] Social media posting

---

## 🎮 Advanced Controls

### Gesture Support
- [ ] Touch screen support (swipe to change image)
- [ ] Pinch to zoom
- [ ] Double-tap for info
- [ ] Long press for menu

### Remote Controls
- [ ] IR remote support
- [ ] Bluetooth remote
- [ ] Mobile app (native iOS/Android)
- [ ] Keyboard shortcuts documentation
- [ ] Gamepad support

### Web UI Improvements
- [ ] Breadcrumb navigation in directory browser
- [ ] Keyboard navigation everywhere
- [ ] Drag-and-drop image reordering
- [ ] Image preview on hover
- [ ] Multi-file upload progress
- [ ] PWA support (install as app)

---

## 📊 Analytics & Monitoring

### Statistics
- [ ] View count per image
- [ ] Most viewed images
- [ ] Playback time statistics
- [ ] Uptime monitoring
- [ ] Error log viewer
- [ ] System resource graphs (CPU, RAM, temp)

### Logging
- [ ] Structured logging (JSON)
- [ ] Log rotation
- [ ] Remote logging (syslog)
- [ ] Email alerts on errors
- [ ] Slack/Discord notifications

---

## 🎬 Media Features

### Video Support (Detailed)
- [ ] Hardware-accelerated decoding
- [ ] Subtitles support
- [ ] Audio level normalization
- [ ] Video aspect ratio handling
- [ ] Thumbnail generation for videos
- [ ] Playback speed control
- [ ] Loop video option

### Audio
- [ ] Background music support
- [ ] Audio fade between images
- [ ] Sync music to slideshow tempo
- [ ] Audio visualization
- [ ] Podcast/radio support

### Live Content
- [ ] Webcam feed display
- [ ] IP camera support
- [ ] RSS feed images
- [ ] News ticker
- [ ] Calendar events display
- [ ] Clock screensaver mode

---

## 🛠️ System & Maintenance

### Configuration
- [ ] Configuration backup/restore
- [ ] Import/export settings
- [ ] Multiple config profiles
- [ ] Config validation and migration
- [ ] Setup wizard for first run

### Updates & Maintenance
- [ ] Auto-update check
- [ ] One-click update via web
- [ ] Database optimization
- [ ] Cache cleanup tool
- [ ] Diagnostic mode
- [ ] Health check endpoint

### Documentation
- [ ] User manual (web-based)
- [ ] Video tutorials
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Troubleshooting guide
- [ ] FAQ page
- [ ] Keyboard shortcuts reference

---

## 🚀 Alternative Technologies

### Display Alternatives
- [ ] PIL + Framebuffer (lower resources)
- [ ] fbi + PIL overlays (hybrid approach)
- [ ] Hardware-accelerated rendering (OpenGL)
- [ ] Web-based display (Chromium kiosk)

### Architecture
- [ ] Microservices split (display + web server separate)
- [ ] Database backend (SQLite)
- [ ] Message queue (Redis/RabbitMQ)
- [ ] Caching layer (Redis)

---

## 📝 Code Quality

### Testing
- [ ] Unit tests for core functions
- [ ] Integration tests for API
- [ ] UI/E2E tests (Selenium)
- [ ] Performance tests
- [ ] Load testing (multiple users)
- [ ] CI/CD pipeline

### Code Improvements
- [ ] Type hints everywhere
- [ ] Docstrings for all functions
- [ ] Code coverage reports
- [ ] Linting (flake8, pylint)
- [ ] Code formatting (black)
- [ ] Security scanning

---

## ✅ Completed Quick Wins

1. **Shutdown button** ✅ (expanded with auto-shutdown)
2. **Basic error logging** ✅ (comprehensive error detection)
3. **Error log viewer** ✅ (`/api/logs` endpoint)
4. **Image captions** ✅ (full EXIF/IPTC/XMP support + editing)
5. **Cross-platform setup** ✅ (Windows, Linux, macOS support)
6. **Enhanced setup verification** ✅ (ultra-basic checks + comprehensive validation)

## 🎯 Remaining Quick Wins (Still Available)

1. **Adaptive frame rate** (30 min, huge CPU savings)
2. **Time/date caching** (30 min, smoother display)
3. **History limiting** (10 min, memory safety)
4. **Dark mode for web UI** (2 hours, better UX)
5. **Simple fade transition** (2 hours, looks professional)
6. **Delete uploaded images button** (2 hours, safety + useful)

---

## 💭 Nice-to-Have / Future Ideas

- [ ] E-ink display support
- [ ] Multi-room sync (same image on all frames)
- [ ] NFT/crypto art display
- [ ] DALL-E/Midjourney integration
- [ ] Live photo effects (motion photos)
- [ ] Augmented reality features
- [ ] 3D photo support (stereoscopic)
- [ ] Portrait mode effects
- [ ] Time-lapse creation from photos
- [ ] Photo booth mode (take photos via camera)
- [ ] Whiteboard mode (annotations)
- [ ] Guest mode (limited controls)

---

## 🔥 Community Requested

- [ ] Docker container
- [ ] Snap package
- [ ] Windows executable
- [ ] MacOS app
- [ ] Raspberry Pi image download
- [ ] Template library
- [ ] Plugin system
- [ ] Theme marketplace

---

## Priority Ranking

### ✅ COMPLETED (v1.0 Core)
- Image captions (enhanced with editing)
- Shutdown button (expanded with auto-shutdown)
- Error detection & logging (core features)
- Cross-platform support (Windows, Linux, macOS)
- System control features (shutdown/restart/cancel)
- Enhanced setup verification
- Performance monitoring (real-time metrics)

### 🔄 IN PROGRESS (v1.1)
- Dark mode for web UI
- Basic transitions (fade effects)
- Delete uploaded images
- Live settings preview

### 📋 NEXT (v1.5)
- Video support
- Image sorting/display order
- Favorites system
- Authentication/security
- Performance optimizations

### 🚀 FUTURE (v2.0+)
- Cloud integration (Google Photos, Dropbox)
- Face detection & recognition
- Smart features (AI/ML)
- Mobile app companion
- Advanced playlists

### 🌟 LONG TERM (v3.0++)
- AI/ML features (scene detection, auto-tagging)
- Multi-display support
- Advanced analytics & monitoring
- Plugin system & marketplace
- Alternative display technologies (E-ink, etc.)

---

## 📊 Current Project Status

**Major Milestones Achieved:**
- ✅ **Cross-platform compatibility** (Windows, Linux, macOS, Raspberry Pi)
- ✅ **System management capabilities** (shutdown, restart, monitoring)
- ✅ **Enhanced error handling** (comprehensive setup verification)
- ✅ **Advanced image captioning** (metadata reading + editing)
- ✅ **API expansion** (18 endpoints vs original ~11)
- ✅ **Production readiness** (robust error handling, documentation)

**Current Version:** v1.0 (feature complete for core functionality)

## Next Steps

1. **Polish existing features** (dark mode, transitions, delete functionality)
2. **Performance optimization** (adaptive framerate, caching)
3. **User experience improvements** (sorting, favorites, search)
4. **Advanced features** (video support, authentication, cloud integration)
5. **Community feedback** and testing on different platforms
6. **Documentation updates** for new features

**Priority Focus:** User experience and stability before adding more features.


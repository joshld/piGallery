# piGallery - TODO List (User Requested Features Only)

## ✅ Features You Requested (Priority Order)

### 1. Telegram Integration (Full Featured) ⭐ PRIORITY
**Phase 1 - Status Updates TO Telegram:** (~2 hours - Start Here!)
- [x] Setup Telegram bot via BotFather
- [x] Send status updates to group/channel
- [x] Startup/shutdown notifications
- [x] Error notifications (immediate alerts)
- [x] Image change notifications (configurable frequency)
- [x] Upload notifications
- [x] Settings change notifications
- [x] System alerts (low memory, high CPU, high temp)
- [ ] Daily summary reports
- [x] Configure notification types in settings

**Phase 2 - Commands FROM Telegram:** (~4 hours)
- [ ] Receive and process Telegram commands
- [ ] `/next` - Skip to next image
- [ ] `/prev` - Go to previous image
- [ ] `/pause` - Toggle pause/play
- [ ] `/status` - Get current status
- [ ] `/weather` - Force weather update
- [ ] `/shutdown` - Safe shutdown with confirmation
- [ ] `/restart` - Restart gallery
- [ ] `/photo` - Send current image to Telegram
- [ ] `/help` - List all available commands

**Phase 3 - Advanced Features:** (~2 hours)
- [ ] `/upload` - Upload photo from Telegram to gallery
- [ ] `/settings <key> <value>` - Change settings
- [ ] `/sort <type>` - Change image sorting
- [ ] `/delay <seconds>` - Change display delay
- [ ] User authentication (whitelist user IDs)
- [ ] Rate limiting for commands
- [ ] Command history/audit log
- [ ] Scheduled status updates (hourly/daily)

**Configuration:**
- [ ] Store bot token and chat ID in config.ini
- [ ] Configure notification preferences
- [ ] Security settings (allowed users, rate limits)
- [ ] Add python-telegram-bot to requirements.txt

### 2. Image Captions from Metadata ✅ COMPLETED (Enhanced)
- [x] Read EXIF/IPTC metadata from images
- [x] Display captions overlaid on images
- [x] Toggle caption display on/off
- [x] Configure caption position and styling
- [x] **NEW:** Set/edit captions via web UI (`/api/image/caption`)
- [x] **NEW:** Advanced metadata reading (EXIF, IPTC, XMP)
- [x] **NEW:** Multi-format support (JPG, PNG, other formats)
- [x] **NEW:** Caption validation and error handling
- [x] **NEW:** Cross-platform metadata compatibility

### 3. Automatic Shutdown & Power Management ✅ COMPLETED
- [x] Configurable automatic shutdown at display off time
- [x] Countdown timer display before shutdown
- [x] Telegram notification before shutdown
- [x] Default enabled for power savings
- [x] Documented power-saving options (smart plugs, timers, etc.)
- [x] Add shutdown button to web UI (manual shutdown)
- [x] Confirmation dialog for manual shutdown

### 4. Color Schemes for Web UI ✅ PARTIALLY COMPLETE
- [x] Light mode (current)
- [x] Dark mode
- [x] **NEW:** Tokyo Night theme (dark blue/cyan/purple)
- [x] Other color scheme options (Nord, Dracula, Gruvbox, etc.)
- [x] Save theme preference

### 5. Image Transitions
- [ ] Fade transition
- [ ] Slide transition
- [ ] Other transition types
- [ ] Configurable transition speed
- [ ] Option to disable transitions

### 6. Video Support
- [ ] Play video files (.mp4, .avi, .mov, etc.)
- [ ] Video playback controls
- [ ] Auto-advance after video completes
- [ ] Audio playback option

### 7. Error Detection & Reporting (Partially Complete)
- [x] Capture and log all errors
- [x] Error log viewer in web UI
- [x] Error details (timestamp, type, context)
- [ ] Export error logs
- [ ] Clear error log option

### 8. Delete Uploaded Images (via Modal Manager) ✅ COMPLETED
- [x] "Manage Uploaded Images" button near upload area
- [x] Modal popup showing grid of uploaded image thumbnails
- [x] Checkboxes for selecting images to delete
- [x] "Delete Selected" button (bulk delete)
- [x] Individual delete button per image
- [x] Protection for original gallery images (only uploaded folder)
- [x] Confirmation dialog before delete
- [x] Pagination if >20 images (scrolling instead)
- [x] Refresh image list after deletion
- [x] **NEW:** Upload count badge on button
- [x] **NEW:** Image preview on thumbnail click
- [x] **NEW:** Select all/deselect all functionality
- [x] **NEW:** File size and upload date display
- [x] **NEW:** Responsive design for mobile
- [x] **NEW:** Loading states and error handling
- [x] **NEW:** Edit Mode for filename/caption editing
- [x] **NEW:** Inline filename editing
- [x] **NEW:** Caption editing with textarea
- [x] **NEW:** Auto-save captions on change
- [x] **NEW:** Improved UX - "Close" button instead of "Cancel"
- [x] **NEW:** Better modal close behavior (cleanup temp files)
- [x] **NEW:** Enhanced feedback - Save button appears immediately
- [x] **NEW:** Space input fixes in textareas

### 9. Image Display Order/Sorting ✅ COMPLETED
- [x] Sort options in settings (dropdown/selector)
- [x] Random (current default)
- [x] Date taken (from EXIF metadata)
- [x] Date created (file creation date)
- [x] Date modified (file modified date)
- [x] Filename (alphabetical)
- [x] File size (smallest/largest first)
- [x] Reverse order option
- [x] Save sort preference to config
- [x] Apply sorting when refreshing images
- [x] **NEW:** Immediate sorting when settings change (re-sorts existing queue)
- [x] **NEW:** EXIF DateTimeOriginal reading with fallback to file dates
- [x] **NEW:** Support for uploaded images in separate directories
- [x] **NEW:** Robust error handling for missing/corrupted EXIF data
- [x] **NEW:** Intelligent default sort behavior (largest images first for size sorting)

### 10. Feedback/Suggestions System
- [ ] "Send Feedback" button in web UI
- [ ] Feedback form modal (type, title, description)
- [ ] Feedback types: Bug Report, Feature Request, Question, General
- [ ] GitHub Issues API integration (create issue automatically)
- [ ] Rate limiting (prevent spam)
- [ ] Confirmation message with link to created issue
- [ ] Store GitHub token in config.ini
- [ ] Optional: Email fallback if GitHub API unavailable
- [ ] User feedback history view
- [ ] Anonymous submission option

### 11. Performance Monitoring & System Health (Partially Complete)
**Real-time Metrics:**
- [x] CPU usage (current, average, per-core if multi-core)
- [x] Memory usage (total, used, free, available, swap)
- [ ] Memory leak detection (track growth over time)
- [x] Temperature monitoring (CPU temp, GPU temp if available)
- [x] Disk/filesystem usage (used, free, percentage)
- [ ] Network usage (bandwidth, requests per minute)
- [ ] Process uptime and restart count

**Historical Tracking:**
- [ ] Store metrics history (last 24 hours, 7 days)
- [ ] Generate performance graphs/charts
- [ ] Peak usage tracking
- [ ] Identify performance trends
- [ ] Export metrics data (CSV/JSON)

**Web UI Dashboard:**
- [x] System status card with live metrics
- [x] Visual indicators (gauges, progress bars)
- [ ] Color-coded warnings (green/yellow/red)
- [ ] Performance graphs (CPU, memory over time)
- [ ] Disk space breakdown by directory
- [ ] Alert thresholds configuration

**Alerts & Warnings:**
- [x] High CPU usage alert (>80% sustained)
- [x] Low memory warning (<100 MB free)
- [x] Disk space warning (<1 GB free)
- [x] High temperature alert (>80°C)
- [ ] Memory leak detection (continuous growth)
- [ ] Swap usage warning
- [x] Send alerts via Telegram (if enabled)
- [ ] Log performance issues to error log

**Optimization Tools:**
- [ ] Cache cleanup button
- [ ] Memory optimization suggestions
- [ ] Identify resource-heavy operations
- [ ] Restart services if memory leaked
- [ ] Auto-restart on critical thresholds

**Raspberry Pi Specific:**
- [ ] GPU memory split monitoring
- [ ] Throttling detection (under-voltage, thermal)
- [ ] SD card health monitoring
- [x] vcgencmd integration for Pi metrics

---

### 12. Cross-Platform Support ✅ COMPLETED
- [x] **Windows compatibility** - Full support for Windows PCs
- [x] **Cross-platform setup** - Works on Windows, Linux, macOS, Raspberry Pi
- [x] **Enhanced setup verification** - `test_setup.py` with comprehensive error checking
- [x] **Platform-specific instructions** - Updated README with platform-specific setup guides
- [x] **Unicode-safe error messages** - ASCII-only output for Windows terminal compatibility

---

### 13. Enhanced Setup Verification & Error Handling ✅ COMPLETED
- [x] **Ultra-basic environment checks** - Validates Python functionality before imports
- [x] **Comprehensive dependency checking** - All 8 required packages verified
- [x] **Port availability testing** - Checks if port 5000 is free
- [x] **File permission validation** - Ensures write access for config/uploads
- [x] **Network configuration** - IP and hostname access verification
- [x] **Detailed error messages** - Actionable troubleshooting for each failure type
- [x] **Cross-platform compatibility** - Works on Windows, Linux, macOS

---

### 14. System Control Features ✅ COMPLETED
- [x] **Remote shutdown** - Safe system shutdown via web UI (`/api/system/shutdown`)
- [x] **Remote restart** - System restart capability (`/api/system/restart`)
- [x] **Cancel operations** - Cancel pending shutdown/restart (`/api/system/cancel`)
- [x] **Countdown display** - Visual countdown timer before system operations
- [x] **Safety measures** - Confirmation dialogs and Telegram notifications
- [x] **Security considerations** - Proper access control for system operations

---

### 15. Additional API Endpoints & Features ✅ COMPLETED
**Image Management:**
- [x] `/api/image/preview` - Thumbnail with caption overlay
- [x] `/api/image/full` - Full resolution image viewing
- [x] `/api/image/caption` (GET/POST) - Caption editing via web UI

**System & Utilities:**
- [x] `/api/logs` - Error log access and viewing
- [x] `/api/directories` - Folder browsing for image selection

**Total API Endpoints:** 18 (up from ~11 originally)

---

## 📊 Updated Project Statistics

**Completed Features:** 8/15 (53%)
- ✅ Telegram Integration (Phase 1)
- ✅ Image Captions (Enhanced)
- ✅ Automatic Shutdown & Power Management
- ✅ Color Schemes (Partially - Tokyo Night added)
- ✅ Cross-Platform Support
- ✅ Enhanced Setup Verification
- ✅ System Control Features
- ✅ **Delete Uploaded Images (Enhanced!)**

**Partially Complete:** 2/15 (13%)
- 🔄 Error Detection & Reporting (~60% complete)
- 🔄 Performance Monitoring (~50% complete)

**Not Yet Started:** 6/15 (40%)
- ❌ Color Schemes for Web UI
- ❌ Image Transitions
- ❌ Video Support
- ❌ Image Display Order/Sorting
- ❌ Feedback/Suggestions System

**Total API Endpoints:** 18 (up from ~11)
**Platforms Supported:** Windows, Linux, macOS, Raspberry Pi
**Setup Verification:** Comprehensive (ultra-basic → application level)

## 📝 Notes

- Keep the comprehensive feature ideas list separately
- Review and approve any additional features before adding
- Focus on implementing these core features first
- **Major milestone:** Cross-platform compatibility achieved
- **Major milestone:** System management capabilities added

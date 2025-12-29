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

### 2. Image Captions from Metadata ✅ COMPLETED
- [x] Read EXIF/IPTC metadata from images
- [x] Display captions overlaid on images
- [x] Toggle caption display on/off
- [x] Configure caption position and styling

### 3. Automatic Shutdown & Power Management ✅ COMPLETED
- [x] Configurable automatic shutdown at display off time
- [x] Countdown timer display before shutdown
- [x] Telegram notification before shutdown
- [x] Default enabled for power savings
- [x] Documented power-saving options (smart plugs, timers, etc.)
- [ ] Add shutdown button to web UI (manual shutdown)
- [ ] Confirmation dialog for manual shutdown

### 4. Color Schemes for Web UI
- [ ] Light mode (current)
- [ ] Dark mode
- [ ] Other color scheme options
- [ ] Save theme preference

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

### 8. Delete Uploaded Images (via Modal Manager)
- [ ] "Manage Uploaded Images" button near upload area
- [ ] Modal popup showing grid of uploaded image thumbnails
- [ ] Checkboxes for selecting images to delete
- [ ] "Delete Selected" button (bulk delete)
- [ ] Individual delete button per image
- [ ] Protection for original gallery images (only uploaded folder)
- [ ] Confirmation dialog before delete
- [ ] Pagination if >20 images
- [ ] Refresh image list after deletion

### 9. Image Display Order/Sorting
- [ ] Sort options in settings (dropdown/selector)
- [ ] Random (current default)
- [ ] Date taken (from EXIF metadata)
- [ ] Date created (file creation date)
- [ ] Date modified (file modified date)
- [ ] Filename (alphabetical)
- [ ] File size (smallest/largest first)
- [ ] Reverse order option
- [ ] Save sort preference to config
- [ ] Apply sorting when refreshing images

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
- [ ] Disk space warning (<1 GB free)
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

## 📝 Notes

- Keep the comprehensive feature ideas list separately
- Review and approve any additional features before adding
- Focus on implementing these core features first

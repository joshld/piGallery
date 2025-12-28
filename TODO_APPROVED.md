# piGallery - TODO List (User Requested Features Only)

## ✅ Features You Requested (Priority Order)

### 1. Telegram Integration (Full Featured) ⭐ PRIORITY
**Phase 1 - Status Updates TO Telegram:** (~2 hours - Start Here!)
- [ ] Setup Telegram bot via BotFather
- [ ] Send status updates to group/channel
- [ ] Startup/shutdown notifications
- [ ] Error notifications (immediate alerts)
- [ ] Image change notifications (configurable frequency)
- [ ] Upload notifications
- [ ] Settings change notifications
- [ ] System alerts (low memory, high CPU, high temp)
- [ ] Daily summary reports
- [ ] Configure notification types in settings

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

### 2. Image Captions from Metadata
- [ ] Read EXIF/IPTC metadata from images
- [ ] Display captions overlaid on images
- [ ] Toggle caption display on/off
- [ ] Configure caption position and styling

### 3. Shutdown Button
- [ ] Add shutdown button to web UI
- [ ] Confirmation dialog before shutdown
- [ ] Countdown timer display
- [ ] Graceful cleanup

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

### 7. Error Detection & Reporting
- [ ] Capture and log all errors
- [ ] Error log viewer in web UI
- [ ] Error details (timestamp, type, context)
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

### 10. Telegram Integration (Full Featured)
**Phase 1 - Status Updates TO Telegram:**
- [ ] Setup Telegram bot via BotFather
- [ ] Send status updates to group/channel
- [ ] Startup/shutdown notifications
- [ ] Error notifications (immediate alerts)
- [ ] Image change notifications (configurable frequency)
- [ ] Upload notifications
- [ ] Settings change notifications
- [ ] System alerts (low memory, high CPU, high temp)
- [ ] Daily summary reports
- [ ] Configure notification types in settings

**Phase 2 - Commands FROM Telegram:**
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

**Phase 3 - Advanced Features:**
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

---

## 📝 Notes

- Keep the comprehensive feature ideas list separately
- Review and approve any additional features before adding
- Focus on implementing these core features first

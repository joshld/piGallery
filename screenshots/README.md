# Screenshots Guide

## What Screenshots to Take

To complete the PR, please capture these screenshots:

### 1. `web-interface-main.png`
**What to show:**
- Full web interface loaded at http://raspberrypi.local:5000
- Status bar showing current image info
- Live image preview (showing an actual photo)
- Playback controls visible
- Display control buttons

**How to capture:**
1. Start gallery.py with some images loaded
2. Open http://raspberrypi.local:5000 in browser
3. Let it display an image for a few seconds (so preview loads)
4. Take full browser screenshot (F12 → Screenshot in dev tools, or browser extension)

**Recommended size:** ~1200px wide

---

### 2. `settings-panel.png`
**What to show:**
- Settings card with all toggle switches
- Advanced settings inputs (delay, times, location)
- Directory settings
- Save Settings button

**How to capture:**
1. Scroll down to settings section
2. Expand/show all settings
3. Screenshot just the settings card(s)

**Recommended size:** ~800px wide

---

### 3. `upload-management.png`
**What to show:**
- Upload area with "Click or Drop Files Here"
- Directory settings with browse buttons
- Directory browser modal (if possible)

**How to capture:**
Option A: Just the upload area
Option B: Click browse button and screenshot the modal dialog

**Recommended size:** ~800px wide

---

### 4. `mobile-view.png`
**What to show:**
- Web interface on phone or narrow browser window
- Single column layout
- Touch-friendly buttons
- Settings adapted to mobile

**How to capture:**
1. Open web UI on phone OR resize browser to ~375px width
2. Show how layout adapts
3. Capture full page (may need scrolling screenshot)

**Recommended size:** ~375px wide (phone width)

---

## Tools for Taking Screenshots

**On Raspberry Pi Desktop:**
- `scrot` (if installed)
- Built-in screenshot tool (Print Screen key)

**In Browser:**
- Firefox: Right-click → "Take Screenshot"
- Chrome: F12 → Ctrl+Shift+P → "Capture screenshot"
- Extension: Nimbus Screenshot, FireShot, etc.

**On Phone:**
- iOS: Power + Volume Up
- Android: Power + Volume Down

**Scrolling Screenshots:**
- Use browser extension (FireShot, GoFullPage)
- Or take multiple screenshots and stitch

---

## Optional Screenshots

If you want to make the PR even better:

### 5. `directory-browser-modal.png`
- Shows the directory browsing dialog
- Parent directory navigation
- List of folders
- "Select This Directory" button

### 6. `full-image-modal.png`
- Shows clicked image in full-size modal
- Demonstrates zoom feature

### 7. `error-display.png` (future)
- If implementing error log viewer
- Shows errors in UI

---

## After Taking Screenshots

1. Save them in this `screenshots/` folder
2. Name them exactly as listed above
3. Optimize/compress if very large (>500 KB)
4. Commit and push:
   ```bash
   git add screenshots/
   git commit -m "Add web interface screenshots for PR"
   git push
   ```

The PR_DESCRIPTION.md already references these filenames, so they'll show up automatically in the PR!

---

## Alternative: Placeholders

If you can't take screenshots right now, you can:
1. Leave placeholders in PR
2. Add screenshots in a follow-up commit
3. Or remove screenshot section from PR description

The PR is still valuable without screenshots, but they help reviewers understand the UI!

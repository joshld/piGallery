let settings = {};

// Theme management
function changeTheme(theme) {
    if (theme === 'default' || !theme) {
        // Remove data-theme attribute to use :root styles
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('piGallery-theme', 'default');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('piGallery-theme', theme);
    }
    // Update selector if it exists
    const selector = document.getElementById('theme-selector');
    if (selector) {
        selector.value = theme || 'default';
    }
    // Update debug display
    updateThemeDebug();
}

function updateThemeDebug() {
    const debugDisplay = document.getElementById('current-theme-display');
    if (debugDisplay) {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'default (:root)';
        const cssLoaded = document.querySelector('link[href="/static/themes.css"]') ? 'Yes' : 'No';
        debugDisplay.textContent = currentTheme + ' | CSS loaded: ' + cssLoaded;
    }
}

function loadTheme() {
    const savedTheme = localStorage.getItem('piGallery-theme');
    if (savedTheme) {
        changeTheme(savedTheme);
    } else {
        // No saved theme, use default (no data-theme attribute = uses :root styles)
        document.documentElement.removeAttribute('data-theme');
        updateThemeDebug();
    }
}
let isPaused = false;

// Initialize
let countdownInterval = null;
let lastKnownTimeRemaining = 0;
let lastUpdateTime = Date.now();

// Power action countdown
let powerActionCountdownInterval = null;
let powerActionEndTime = null;
let powerActionCompleteTimeout = null;

document.addEventListener('DOMContentLoaded', function() {
    // Load theme first
    loadTheme();
    // Update debug after a short delay to ensure CSS is loaded
    setTimeout(updateThemeDebug, 100);
    updateStatus();
    loadSettings();
    setInterval(updateStatus, 3000); // Update every 3 seconds
    
    // Update countdown every second
    countdownInterval = setInterval(updateCountdown, 1000);

    // Drag and drop
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFileSelect(e.dataTransfer.files);
    });

    // Sticky save button visibility based on scroll
    setupStickySaveButton();
});

function setupStickySaveButton() {
    const stickyBtn = document.getElementById('sticky-save-btn');
    const controlsSection = document.querySelector('.controls');
    
    if (!stickyBtn || !controlsSection) return;
    
    // Use Intersection Observer for better performance
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Controls section is visible
                stickyBtn.classList.add('visible');
            } else {
                // Controls section is not visible
                stickyBtn.classList.remove('visible');
            }
        });
    }, {
        threshold: 0.1, // Trigger when 10% of the section is visible
        rootMargin: '-100px 0px' // Account for header offset
    });
    
    observer.observe(controlsSection);
}

let lastImageName = '';
let currentBrowsingField = null;
let currentBrowsePath = '';

async function browseDirectory(fieldId) {
    currentBrowsingField = fieldId;
    currentBrowsePath = '';
    document.getElementById('directoryModal').style.display = 'block';
    await loadDirectories('');
}

function closeDirectoryBrowser() {
    document.getElementById('directoryModal').style.display = 'none';
    currentBrowsingField = null;
    currentBrowsePath = '';
}

async function loadDirectories(path) {
    try {
        const url = path ? `/api/directories?path=${encodeURIComponent(path)}` : '/api/directories';
        const response = await fetch(url);
        const data = await response.json();
        
        if (response.ok) {
            currentBrowsePath = data.current_path || '';
            const browserDiv = document.getElementById('directoryBrowser');
            
            let html = '';
            
            // Show current path
            if (currentBrowsePath) {
                html += `<div style="margin-bottom: 15px; padding: 10px; background: var(--bg-secondary); border-radius: 5px; color: var(--text-primary);">`;
                html += `<strong>Current Path:</strong> ${currentBrowsePath}`;
                html += `</div>`;
            }
            
            // Parent directory button
            if (data.parent_path !== null && data.parent_path !== undefined) {
                const escapedParent = data.parent_path.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
                html += `<div class="directory-item" onclick="loadDirectories('${escapedParent}')">`;
                html += `<strong>.. (Parent Directory)</strong>`;
                html += `</div>`;
            }
            
            // List directories
            if (data.directories && data.directories.length > 0) {
                data.directories.forEach(dir => {
                    // Check if this is a Windows drive letter (e.g., "C:\")
                    const isDriveLetter = /^[A-Z]:\\?$/.test(dir);
                    
                    if (isDriveLetter) {
                        // It's a drive letter - navigate into it
                        const escapedPath = dir.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
                        html += `<div class="directory-item" onclick="loadDirectories('${escapedPath}')">${dir}</div>`;
                    } else if (currentBrowsePath) {
                        // Regular directory - construct full path
                        // Determine separator based on current path format
                        let separator = '/';
                        if (currentBrowsePath.includes('\\') && !currentBrowsePath.includes('/')) {
                            // Windows path
                            separator = '\\';
                        }
                        
                        // Only add separator if path doesn't already end with one
                        const needsSeparator = !currentBrowsePath.endsWith('/') && !currentBrowsePath.endsWith('\\');
                        const fullPath = `${currentBrowsePath}${separator}${dir}`;
                        const escapedPath = fullPath.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
                        html += `<div class="directory-item" onclick="loadDirectories('${escapedPath}')">${dir}</div>`;
                    } else {
                        // No current path - treat as full path (shouldn't happen, but handle it)
                        const escapedPath = dir.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
                        html += `<div class="directory-item" onclick="loadDirectories('${escapedPath}')">${dir}</div>`;
                    }
                });
            } else {
                html += `<p>No subdirectories found.</p>`;
            }
            
            // Select current directory button
            if (currentBrowsePath) {
                const escapedPath = currentBrowsePath.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
                html += `<div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid var(--accent-border);">`;
                html += `<button class="btn-success btn-full" onclick="selectDirectory('${escapedPath}')">`;
                html += `✓ Select This Directory`;
                html += `</button>`;
                html += `</div>`;
            }
            
            browserDiv.innerHTML = html;
        } else {
            document.getElementById('directoryBrowser').innerHTML = 
                `<p style="color: var(--alert-error-text);">Error: ${data.error}</p>`;
        }
    } catch (error) {
        document.getElementById('directoryBrowser').innerHTML = 
            `<p style="color: var(--alert-error-text);">Error loading directories: ${error.message}</p>`;
    }
}

function selectDirectory(path) {
    if (currentBrowsingField) {
        document.getElementById(currentBrowsingField).value = path;
        updateSetting(currentBrowsingField.replace('-', '_'), path);
        closeDirectoryBrowser();
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('directoryModal');
    if (event.target == modal) {
        closeDirectoryBrowser();
    }
}

function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // Activate selected button
    event.target.classList.add('active');
    
    // Load logs when System tab is opened
    if (tabName === 'system') {
        loadLogs();
    }
}

async function loadLogs() {
    const logViewer = document.getElementById('log-viewer');
    const linesSelect = document.getElementById('log-lines');
    const lines = linesSelect ? parseInt(linesSelect.value) : 100;
    
    try {
        if (logViewer) {
            logViewer.textContent = 'Loading logs...';
            const response = await fetch(`/api/logs?lines=${lines}`);
            const data = await response.json();
            
            if (data.status === 'ok' && data.lines) {
                // Join log lines and display
                logViewer.textContent = data.lines.join('\n');
                // Auto-scroll to bottom
                logViewer.scrollTop = logViewer.scrollHeight;
            } else {
                logViewer.textContent = 'No logs available';
            }
        }
    } catch (error) {
        if (logViewer) {
            logViewer.textContent = `Error loading logs: ${error.message}`;
        }
        console.error('Failed to load logs:', error);
    }
}

function updateCountdown() {
    // Don't update countdown if we don't have valid data yet
    if (lastKnownTimeRemaining === 0 && lastUpdateTime === 0) {
        return;
    }
    
    // Calculate time elapsed since last API update
    const now = Date.now();
    const elapsed = Math.floor((now - lastUpdateTime) / 1000);
    const remaining = Math.max(0, lastKnownTimeRemaining - elapsed);
    
    const countdownEl = document.getElementById('status-countdown');
    if (countdownEl && countdownEl.textContent !== 'Paused') {
        if (remaining > 0) {
            countdownEl.textContent = `${remaining}s`;
            countdownEl.style.color = remaining <= 5 ? '#e74c3c' : '#2ecc71'; // Red when < 5s
        } else {
            countdownEl.textContent = '0s';
            countdownEl.style.color = '#e74c3c';
        }
    }
}

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        document.getElementById('status-time').textContent = data.time || '--:--';
        document.getElementById('status-date').textContent = data.date || '---';
        document.getElementById('status-temp').textContent = data.temperature || '--°C';
        document.getElementById('status-weather').textContent = data.weather || '---';
        document.getElementById('status-index').textContent = `${data.current_index} / ${data.total_images}`;
        document.getElementById('status-paused').textContent = data.paused ? 'Paused' : 'Playing';
        document.getElementById('current-image').textContent = data.current_image || 'No image loaded';
        
        // Update countdown tracking
        if (data.time_remaining !== undefined) {
            lastKnownTimeRemaining = data.time_remaining;
            lastUpdateTime = Date.now();
            
            // Show "Paused" instead of countdown when paused
            const countdownEl = document.getElementById('status-countdown');
            if (data.paused && countdownEl) {
                countdownEl.textContent = 'Paused';
                countdownEl.style.color = '#f39c12';
            } else {
                updateCountdown(); // Immediately update display
            }
        }
        
        // Update system stats if available
        if (data.system) {
            const sys = data.system;
            const memoryEl = document.getElementById('status-memory');
            const cpuEl = document.getElementById('status-cpu');
            const tempEl = document.getElementById('status-cpu-temp');
            const diskFreeEl = document.getElementById('status-disk-free');
            const diskUsedEl = document.getElementById('status-disk-used');
            
            if (memoryEl && sys.memory_free_mb !== undefined) {
                memoryEl.textContent = `${sys.memory_free_mb} MB`;
            }
            if (cpuEl && sys.cpu_percent !== undefined) {
                cpuEl.textContent = `${sys.cpu_percent}%`;
            }
            if (tempEl && sys.cpu_temp !== undefined) {
                tempEl.textContent = `${sys.cpu_temp}°C`;
            }
            if (diskFreeEl && sys.disk_free_gb !== undefined) {
                diskFreeEl.textContent = `${sys.disk_free_gb} GB`;
            }
            if (diskUsedEl && sys.disk_used_percent !== undefined) {
                diskUsedEl.textContent = `${sys.disk_used_percent}%`;
            }
        }
        
        // Update image preview only when image changes
        const previewImg = document.getElementById('image-preview');
        if (data.current_image && data.current_image !== lastImageName) {
            previewImg.src = `/api/image/preview?t=${Date.now()}`;
            previewImg.style.display = 'block';
            lastImageName = data.current_image;
            // Load caption when image changes
            loadCaption();
        } else if (!data.current_image) {
            previewImg.style.display = 'none';
            lastImageName = '';
            // Clear caption when no image
            document.getElementById('caption-text').value = '';
            document.getElementById('caption-status').textContent = '';
        }
        
        isPaused = data.paused;
        document.getElementById('pauseBtn').textContent = isPaused ? '▶️ Resume' : '⏸️ Pause';
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

async function loadSettings() {
    // Load theme selector value
    const themeSelector = document.getElementById('theme-selector');
    if (themeSelector) {
        const savedTheme = localStorage.getItem('piGallery-theme') || 'default';
        themeSelector.value = savedTheme || 'default';
    }
    try {
        const response = await fetch('/api/settings');
        settings = await response.json();
        
        // Update toggle switches
        updateToggle('toggle-time', settings.show_time === 'true');
        updateToggle('toggle-date', settings.show_date === 'true');
        updateToggle('toggle-temp', settings.show_temperature === 'true');
        updateToggle('toggle-weather', settings.show_weather_code === 'true');
        updateToggle('toggle-filename', settings.show_filename === 'true');
        updateToggle('toggle-caption', settings.show_caption === 'true');

        // Update input fields
        if (document.getElementById('delay-seconds')) {
            document.getElementById('delay-seconds').value = settings.delay_seconds || 30;
        }
        if (document.getElementById('display-on-time')) {
            document.getElementById('display-on-time').value = settings.display_on_time || '05:00';
        }
        if (document.getElementById('display-off-time')) {
            document.getElementById('display-off-time').value = settings.display_off_time || '23:00';
        }
        if (document.getElementById('location-city')) {
            document.getElementById('location-city').value = settings.location_city_suburb || '';
        }
        if (document.getElementById('ui-text-alpha')) {
            document.getElementById('ui-text-alpha').value = settings.ui_text_alpha || 192;
        }
        if (document.getElementById('display-correction-horizontal')) {
            document.getElementById('display-correction-horizontal').value = settings.display_correction_horizontal || 1.0;
        }
        if (document.getElementById('display-correction-vertical')) {
            document.getElementById('display-correction-vertical').value = settings.display_correction_vertical || 1.0;
        }
        if (document.getElementById('weather-update')) {
            document.getElementById('weather-update').value = settings.weather_update_seconds || 900;
        }
        if (document.getElementById('images-directory')) {
            document.getElementById('images-directory').value = settings.images_directory || '';
        }
        if (document.getElementById('upload-directory')) {
            document.getElementById('upload-directory').value = settings.upload_directory || '';
        }
        
        // Load shutdown settings
        updateToggle('toggle-shutdown', settings.shutdown_on_display_off === 'true');
        if (document.getElementById('shutdown-countdown')) {
            document.getElementById('shutdown-countdown').value = settings.shutdown_countdown_seconds || 10;
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

function updateSetting(key, value) {
    settings[key] = value;
    // Optionally auto-save, or wait for "Save Settings" button
}

function updateToggle(id, active) {
    const element = document.getElementById(id);
    if (active) {
        element.classList.add('active');
    } else {
        element.classList.remove('active');
    }
}

function toggleSetting(key, element) {
    element.classList.toggle('active');
    const isActive = element.classList.contains('active');
    settings[key] = isActive ? 'true' : 'false';
}

async function saveSettings() {
    try {
        // Collect all settings from form
        const allSettings = {
            ...settings,
            delay_seconds: parseInt(document.getElementById('delay-seconds')?.value || settings.delay_seconds),
            display_on_time: document.getElementById('display-on-time')?.value || settings.display_on_time,
            display_off_time: document.getElementById('display-off-time')?.value || settings.display_off_time,
            location_city_suburb: document.getElementById('location-city')?.value || settings.location_city_suburb,
            weather_update_seconds: parseInt(document.getElementById('weather-update')?.value || settings.weather_update_seconds),
            ui_text_alpha: parseInt(document.getElementById('ui-text-alpha')?.value || settings.ui_text_alpha),
            display_correction_horizontal: parseFloat(document.getElementById('display-correction-horizontal')?.value || settings.display_correction_horizontal || 1.0),
            display_correction_vertical: parseFloat(document.getElementById('display-correction-vertical')?.value || settings.display_correction_vertical || 1.0),
            images_directory: document.getElementById('images-directory')?.value || settings.images_directory,
            upload_directory: document.getElementById('upload-directory')?.value || settings.upload_directory,
            shutdown_countdown_seconds: parseInt(document.getElementById('shutdown-countdown')?.value || settings.shutdown_countdown_seconds || 10),
            save_to_config: true
        };
        
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(allSettings)
        });
        
        if (response.ok) {
            showAlert('Settings saved successfully!', 'success');
        } else {
            showAlert('Failed to save settings', 'error');
        }
    } catch (error) {
        showAlert('Error saving settings: ' + error.message, 'error');
    }
}

async function saveSettingsSticky() {
    const btn = document.getElementById('sticky-save-btn');
    const originalText = btn.innerHTML;
    
    try {
        // Update button to show saving state
        btn.disabled = true;
        btn.innerHTML = '⏳ Saving...';
        
        // Call the main save function
        await saveSettings();
        
        // Show success state
        btn.classList.add('saved');
        btn.innerHTML = '✓ Saved!';
        
        // Reset after 2 seconds
        setTimeout(() => {
            btn.classList.remove('saved');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        // Reset on error
        btn.innerHTML = '❌ Error';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

async function nextImage() {
    try {
        const response = await fetch('/api/next', { method: 'POST' });
        if (response.ok) {
            updateStatus();
            showAlert('Moved to next image', 'success');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

async function previousImage() {
    try {
        const response = await fetch('/api/prev', { method: 'POST' });
        if (response.ok) {
            updateStatus();
            showAlert('Moved to previous image', 'success');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

async function loadCaption() {
    try {
        const response = await fetch('/api/image/caption');
        if (response.ok) {
            const data = await response.json();
            const captionText = document.getElementById('caption-text');
            const statusEl = document.getElementById('caption-status');
            
            if (data.caption) {
                captionText.value = data.caption;
                statusEl.textContent = 'Caption loaded from image metadata';
                statusEl.style.color = '#28a745';
            } else {
                captionText.value = '';
                statusEl.textContent = 'No caption found in image metadata';
                statusEl.style.color = '#666';
            }
        } else {
            const error = await response.json();
            document.getElementById('caption-status').textContent = 'Error: ' + (error.error || 'Failed to load caption');
            document.getElementById('caption-status').style.color = '#dc3545';
        }
    } catch (error) {
        document.getElementById('caption-status').textContent = 'Error: ' + error.message;
        document.getElementById('caption-status').style.color = '#dc3545';
    }
}

async function saveCaption() {
    try {
        const captionText = document.getElementById('caption-text');
        const statusEl = document.getElementById('caption-status');
        const saveBtn = document.getElementById('save-caption-btn');
        
        const caption = captionText.value.trim();
        
        // Disable button during save
        saveBtn.disabled = true;
        saveBtn.textContent = '💾 Saving...';
        statusEl.textContent = 'Saving caption...';
        statusEl.style.color = '#666';
        
        const response = await fetch('/api/image/caption', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ caption: caption })
        });
        
        if (response.ok) {
            const data = await response.json();
            statusEl.textContent = data.message || 'Caption saved successfully!';
            statusEl.style.color = '#28a745';
            showAlert('Caption saved to image metadata', 'success');
        } else {
            const error = await response.json();
            statusEl.textContent = 'Error: ' + (error.error || 'Failed to save caption');
            statusEl.style.color = '#dc3545';
            showAlert('Failed to save caption: ' + (error.error || 'Unknown error'), 'error');
        }
        
        // Re-enable button
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Caption';
    } catch (error) {
        document.getElementById('caption-status').textContent = 'Error: ' + error.message;
        document.getElementById('caption-status').style.color = '#dc3545';
        document.getElementById('save-caption-btn').disabled = false;
        document.getElementById('save-caption-btn').textContent = '💾 Save Caption';
        showAlert('Error saving caption: ' + error.message, 'error');
    }
}

async function togglePause() {
    try {
        const response = await fetch('/api/pause', { method: 'POST' });
        if (response.ok) {
            updateStatus();
            const data = await response.json();
            showAlert(data.paused ? 'Slideshow paused' : 'Slideshow resumed', 'success');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

async function setDisplay(action) {
    try {
        const response = await fetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        
        if (response.ok) {
            const messages = {
                'on': 'Display turned on',
                'off': 'Display turned off',
                'auto': 'Display set to auto mode'
            };
            showAlert(messages[action], 'success');
            updateStatus();
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Store selected files for preview
let selectedFiles = [];

function handleFileSelect(files) {
    // Add new files to the selection
    for (let file of files) {
        // Check if file is already in the list
        if (!selectedFiles.find(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
            selectedFiles.push(file);
        }
    }
    updateFilePreview();
}

function updateFilePreview() {
    const previewDiv = document.getElementById('uploadPreview');
    const fileListDiv = document.getElementById('fileList');
    
    if (selectedFiles.length === 0) {
        previewDiv.style.display = 'none';
        return;
    }
    
    previewDiv.style.display = 'block';
    fileListDiv.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.style.cssText = 'display: flex; align-items: center; gap: 6px; padding: 6px 8px; margin-bottom: 4px; background: var(--bg-card); border-radius: 5px; border: 1px solid var(--border-divider); min-width: 0; width: 100%; box-sizing: border-box;';
        
        // Store original filename and extension
        const originalName = file.name;
        const lastDot = originalName.lastIndexOf('.');
        const baseName = lastDot > 0 ? originalName.substring(0, lastDot) : originalName;
        const extension = lastDot > 0 ? originalName.substring(lastDot) : '';
        const displayName = file.customName || originalName;
        
        const fileInfoContainer = document.createElement('div');
        fileInfoContainer.style.cssText = 'flex: 1; min-width: 0; display: flex; align-items: center; gap: 6px;';
        
        const fileInfo = document.createElement('span');
        fileInfo.style.cssText = 'flex: 1; color: var(--text-primary); font-size: 0.9em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; cursor: pointer;';
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        fileInfo.textContent = `${displayName} (${fileSize} MB)`;
        fileInfo.title = `Click to rename: ${displayName} (${fileSize} MB)`;
        
        // Make filename editable on click
        const startEdit = () => {
            const input = document.createElement('input');
            input.type = 'text';
            // Use current custom name or original base name
            const currentBaseName = file.customName ? file.customName.substring(0, file.customName.lastIndexOf('.')) : baseName;
            input.value = currentBaseName;
            input.style.cssText = 'flex: 1; padding: 2px 4px; border: 1px solid var(--accent-border); border-radius: 3px; font-size: 0.9em; min-width: 0; color: var(--input-text); background: var(--bg-input);';
            input.style.width = '100%';
            
            const saveRename = () => {
                const newName = input.value.trim();
                if (newName && newName.length > 0) {
                    // Only update if name actually changed
                    const newFullName = newName + extension;
                    if (newFullName !== originalName) {
                        file.customName = newFullName;
                        fileInfo.textContent = `${file.customName} (${fileSize} MB)`;
                        fileInfo.title = `Click to rename: ${file.customName} (${fileSize} MB)`;
                    } else {
                        // Reverted to original, clear custom name
                        file.customName = null;
                        fileInfo.textContent = `${originalName} (${fileSize} MB)`;
                        fileInfo.title = `Click to rename: ${originalName} (${fileSize} MB)`;
                    }
                } else {
                    // Empty name, revert to original
                    file.customName = null;
                    fileInfo.textContent = `${originalName} (${fileSize} MB)`;
                    fileInfo.title = `Click to rename: ${originalName} (${fileSize} MB)`;
                }
                fileInfoContainer.replaceChild(fileInfo, input);
                // Re-attach click handler
                fileInfo.onclick = startEdit;
            };
            
            const cancelRename = () => {
                fileInfoContainer.replaceChild(fileInfo, input);
                // Re-attach click handler
                fileInfo.onclick = startEdit;
            };
            
            input.onblur = saveRename;
            input.onkeydown = (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    saveRename();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    cancelRename();
                }
            };
            
            fileInfoContainer.replaceChild(input, fileInfo);
            input.focus();
            input.select();
        };
        
        fileInfo.onclick = startEdit;
        
        const removeBtn = document.createElement('button');
        removeBtn.textContent = '×';
        removeBtn.style.cssText = 'background: var(--alert-error-border); color: var(--btn-text); border: none; border-radius: 2px; padding: 0; margin: 0; cursor: pointer; font-size: 12px; font-weight: bold; flex-shrink: 0; width: 16px !important; height: 16px !important; min-width: 16px !important; max-width: 16px !important; line-height: 1; display: inline-flex; align-items: center; justify-content: center; box-sizing: border-box;';
        removeBtn.title = 'Remove file';
        removeBtn.onclick = () => {
            selectedFiles.splice(index, 1);
            updateFilePreview();
        };
        
        fileInfoContainer.appendChild(fileInfo);
        fileItem.appendChild(fileInfoContainer);
        fileItem.appendChild(removeBtn);
        fileListDiv.appendChild(fileItem);
    });
}

function clearFileSelection() {
    selectedFiles = [];
    document.getElementById('fileInput').value = '';
    const captionInput = document.getElementById('upload-caption');
    if (captionInput) {
        captionInput.value = '';
    }
    updateFilePreview();
    document.getElementById('uploadStatus').innerHTML = '';
}

async function uploadSelectedFiles() {
    if (selectedFiles.length === 0) {
        showAlert('No files selected', 'error');
        return;
    }

    const uploadStatus = document.getElementById('uploadStatus');
    const uploadBtn = document.getElementById('uploadBtn');
    uploadStatus.innerHTML = '';

    // Disable upload button during upload
    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ Uploading...';

    // Get caption from input field (applies to all files)
    const captionInput = document.getElementById('upload-caption');
    const caption = captionInput ? captionInput.value.trim() : '';

    let successCount = 0;
    let failCount = 0;

    for (let file of selectedFiles) {
        const formData = new FormData();
        // Use custom name if set, otherwise use original filename
        const fileName = file.customName || file.name;
        // Create a new File object with the custom name if renamed
        const fileToUpload = file.customName ? new File([file], fileName, { type: file.type, lastModified: file.lastModified }) : file;
        formData.append('file', fileToUpload);
        if (caption) {
            formData.append('caption', caption);
        }

        try {
            uploadStatus.innerHTML += `<p>Uploading ${file.name}...</p>`;
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                const captionMsg = caption ? ' with caption' : '';
                uploadStatus.innerHTML += `<p style="color: var(--alert-success-text);">✅ ${file.name} uploaded successfully${captionMsg}!</p>`;
                successCount++;
            } else {
                const data = await response.json();
                uploadStatus.innerHTML += `<p style="color: var(--alert-error-text);">❌ ${file.name}: ${data.error}</p>`;
                failCount++;
            }
        } catch (error) {
            uploadStatus.innerHTML += `<p style="color: var(--alert-error-text);">❌ ${file.name}: ${error.message}</p>`;
            failCount++;
        }
    }

    // Re-enable upload button
    uploadBtn.disabled = false;
    uploadBtn.textContent = '📤 Upload All';

    // Show summary
    if (successCount > 0) {
        showAlert(`Successfully uploaded ${successCount} file(s)${failCount > 0 ? `, ${failCount} failed` : ''}`, failCount > 0 ? 'error' : 'success');
    } else {
        showAlert('Upload failed for all files', 'error');
    }

    // Clear selection after successful upload
    if (failCount === 0) {
        clearFileSelection();
    }
    
    // Refresh status after upload
    setTimeout(updateStatus, 1000);
}

function showAlert(message, type) {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert ${type}`;
    alert.style.display = 'block';
    
    setTimeout(() => {
        alert.style.display = 'none';
    }, 3000);
}

function showFullImage() {
    const modal = document.getElementById('imageModal');
    const fullImg = document.getElementById('full-image');
    const previewImg = document.getElementById('image-preview');
    
    if (previewImg.src) {
        // Use the full image endpoint
        fullImg.src = `/api/image/full?t=${Date.now()}`;
        modal.style.display = 'block';
    }
}

function closeFullImage(event) {
    const modal = document.getElementById('imageModal');
    // Close if clicking on the background or the close button
    if (event.target === modal || event.target.classList.contains('image-modal-close')) {
        modal.style.display = 'none';
    }
}

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('imageModal');
        if (modal.style.display === 'block') {
            modal.style.display = 'none';
        }
        // Close power management modals too
        const shutdownModal = document.getElementById('shutdownModal');
        const restartModal = document.getElementById('restartModal');
        if (shutdownModal && shutdownModal.style.display === 'block') {
            closeShutdownModal();
        }
        if (restartModal && restartModal.style.display === 'block') {
            closeRestartModal();
        }
    }
});

// Shutdown modal functions
function confirmShutdown() {
    document.getElementById('shutdownModal').style.display = 'block';
}

function closeShutdownModal() {
    document.getElementById('shutdownModal').style.display = 'none';
}

async function executeShutdown() {
    const countdown = parseInt(document.getElementById('shutdown-countdown-input').value) || 10;
    
    try {
        const response = await fetch('/api/system/shutdown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ countdown: countdown })
        });
        
        if (response.ok) {
            const data = await response.json();
            closeShutdownModal();
            showAlert(`System shutting down in ${countdown} seconds...`, 'success');
            
            // Start countdown timer
            startPowerActionCountdown(countdown, 'Shutting down');
            
            // Hide cancel button after countdown
            powerActionCompleteTimeout = setTimeout(() => {
                stopPowerActionCountdown();
                hidePowerActionStatus();
                showAlert('System shutdown initiated. Connection will be lost.', 'error');
                powerActionCompleteTimeout = null;
            }, countdown * 1000);
        } else if (response.status === 409) {
            // Power action already in progress
            const error = await response.json();
            closeShutdownModal();
            showAlert(error.error || 'A power action is already in progress', 'error');
        } else {
            const error = await response.json();
            showAlert('Shutdown failed: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error initiating shutdown: ' + error.message, 'error');
    }
}

// Restart modal functions
function confirmRestart() {
    document.getElementById('restartModal').style.display = 'block';
}

function closeRestartModal() {
    document.getElementById('restartModal').style.display = 'none';
}

async function executeRestart() {
    const countdown = parseInt(document.getElementById('restart-countdown-input').value) || 10;
    
    try {
        const response = await fetch('/api/system/restart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ countdown: countdown })
        });
        
        if (response.ok) {
            const data = await response.json();
            closeRestartModal();
            showAlert(`System restarting in ${countdown} seconds...`, 'success');
            
            // Start countdown timer
            startPowerActionCountdown(countdown, 'Restarting');
            
            // Hide cancel button and show reconnection message
            powerActionCompleteTimeout = setTimeout(() => {
                stopPowerActionCountdown();
                hidePowerActionStatus();
                showAlert('System restarting. Page will reload when system comes back online.', 'error');
                
                // Try to reconnect after estimated restart time (30 seconds boot time)
                const reconnectTime = 30 * 1000;
                setTimeout(() => {
                    location.reload();
                }, reconnectTime);
                powerActionCompleteTimeout = null;
            }, countdown * 1000);
        } else if (response.status === 409) {
            // Power action already in progress
            const error = await response.json();
            closeRestartModal();
            showAlert(error.error || 'A power action is already in progress', 'error');
        } else {
            const error = await response.json();
            showAlert('Restart failed: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error initiating restart: ' + error.message, 'error');
    }
}

// Close modals when clicking outside
window.addEventListener('click', function(event) {
    const shutdownModal = document.getElementById('shutdownModal');
    const restartModal = document.getElementById('restartModal');
    if (event.target === shutdownModal) {
        closeShutdownModal();
    }
    if (event.target === restartModal) {
        closeRestartModal();
    }
});

// Power action status functions
function showPowerActionStatus(message) {
    const statusDiv = document.getElementById('power-action-status');
    const messageSpan = document.getElementById('power-action-message');
    messageSpan.textContent = message;
    statusDiv.style.display = 'block';
}

function hidePowerActionStatus() {
    const statusDiv = document.getElementById('power-action-status');
    statusDiv.style.display = 'none';
}

function startPowerActionCountdown(seconds, actionName) {
    // Set end time
    powerActionEndTime = Date.now() + (seconds * 1000);
    
    // Initial display
    updatePowerActionCountdown(actionName);
    
    // Update every second
    powerActionCountdownInterval = setInterval(() => {
        updatePowerActionCountdown(actionName);
    }, 1000);
}

function updatePowerActionCountdown(actionName) {
    if (!powerActionEndTime) return;
    
    const remaining = Math.max(0, Math.ceil((powerActionEndTime - Date.now()) / 1000));
    
    if (remaining > 0) {
        showPowerActionStatus(`⏳ ${actionName} in ${remaining} second${remaining !== 1 ? 's' : ''}...`);
    } else {
        showPowerActionStatus(`⏳ ${actionName} now...`);
    }
}

function stopPowerActionCountdown() {
    if (powerActionCountdownInterval) {
        clearInterval(powerActionCountdownInterval);
        powerActionCountdownInterval = null;
    }
    if (powerActionCompleteTimeout) {
        clearTimeout(powerActionCompleteTimeout);
        powerActionCompleteTimeout = null;
    }
    powerActionEndTime = null;
}

async function cancelPowerAction() {
    try {
        const response = await fetch('/api/system/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            stopPowerActionCountdown();
            hidePowerActionStatus();
            showAlert('Power action cancelled successfully', 'success');
        } else {
            const error = await response.json();
            showAlert('Cancel failed: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error cancelling power action: ' + error.message, 'error');
    }
}

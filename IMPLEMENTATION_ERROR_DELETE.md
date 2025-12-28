# Error Detection & Reporting System - Implementation Spec

## Overview
Comprehensive error tracking system that captures, logs, and displays all errors for debugging and monitoring.

## Architecture

### 1. Error Logger Class
```python
import logging
import json
import traceback
from datetime import datetime
from collections import deque

class GalleryErrorLogger:
    def __init__(self, log_dir='/var/log/pigallery', max_errors=1000):
        self.log_dir = log_dir
        self.max_errors = max_errors
        self.error_buffer = deque(maxlen=max_errors)  # In-memory circular buffer
        self.error_counts = {}  # Track error frequency
        
        # Setup file logging
        os.makedirs(log_dir, exist_ok=True)
        self.setup_logging()
    
    def log_error(self, error_type, message, exception=None, context=None):
        """Log an error with full context"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': message,
            'exception': str(exception) if exception else None,
            'traceback': traceback.format_exc() if exception else None,
            'context': context or {},
            'system_state': self.capture_system_state()
        }
        
        # Add to buffer
        self.error_buffer.append(error_entry)
        
        # Update counts
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log to file
        self.log_to_file(error_entry)
        
        return error_entry
    
    def capture_system_state(self):
        """Capture current system state for debugging"""
        return {
            'memory_mb': self.get_memory_usage(),
            'cpu_percent': self.get_cpu_usage(),
            'disk_free_gb': self.get_disk_free(),
            'uptime_seconds': time.time() - self.start_time,
            'current_image': slideshow_instance.current_img if slideshow_instance else None,
            'paused': slideshow_instance.paused if slideshow_instance else None,
            'display_on': slideshow_instance.is_display_on() if slideshow_instance else None
        }
```

### 2. Error Types
```python
ERROR_TYPES = {
    'IMAGE_LOAD': 'Failed to load image',
    'FILE_NOT_FOUND': 'File or directory not found',
    'PERMISSION_DENIED': 'Permission error',
    'NETWORK_ERROR': 'Network/API failure',
    'DISPLAY_ERROR': 'Display/rendering error',
    'CONFIG_ERROR': 'Configuration error',
    'WEATHER_API': 'Weather service error',
    'UPLOAD_ERROR': 'File upload error',
    'SYSTEM_ERROR': 'System/OS error',
    'UNKNOWN': 'Unknown error'
}
```

### 3. Error Catching Wrapper
```python
def safe_execute(func, error_type='UNKNOWN', context=None):
    """Decorator to catch and log errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_logger.log_error(
                error_type=error_type,
                message=f"Error in {func.__name__}",
                exception=e,
                context=context or {'function': func.__name__}
            )
            return None
    return wrapper
```

## API Endpoints

### GET /api/errors
```python
@app.route('/api/errors')
def api_get_errors():
    """Get recent errors"""
    limit = request.args.get('limit', 50, type=int)
    error_type = request.args.get('type', None)
    
    errors = list(error_logger.error_buffer)
    
    # Filter by type if specified
    if error_type:
        errors = [e for e in errors if e['type'] == error_type]
    
    # Limit results
    errors = errors[-limit:]
    
    return jsonify({
        'errors': errors,
        'total_count': len(error_logger.error_buffer),
        'error_counts': error_logger.error_counts
    })
```

### GET /api/errors/stats
```python
@app.route('/api/errors/stats')
def api_error_stats():
    """Get error statistics"""
    return jsonify({
        'total_errors': len(error_logger.error_buffer),
        'by_type': error_logger.error_counts,
        'recent_24h': count_errors_last_24h(),
        'most_common': get_most_common_errors(5),
        'error_rate': calculate_error_rate()
    })
```

### DELETE /api/errors/clear
```python
@app.route('/api/errors/clear', methods=['DELETE'])
def api_clear_errors():
    """Clear error log"""
    error_logger.error_buffer.clear()
    error_logger.error_counts.clear()
    return jsonify({'status': 'ok', 'message': 'Error log cleared'})
```

### GET /api/errors/export
```python
@app.route('/api/errors/export')
def api_export_errors():
    """Export errors as JSON/CSV"""
    format = request.args.get('format', 'json')
    
    if format == 'json':
        return jsonify(list(error_logger.error_buffer))
    elif format == 'csv':
        # Convert to CSV and return
        return send_csv(error_logger.error_buffer)
```

## Web UI Components

### Error Log Viewer Page
```html
<div class="control-card">
    <h2>🐛 Error Log</h2>
    
    <!-- Stats Summary -->
    <div class="error-stats">
        <div class="stat-box">
            <span class="stat-value" id="total-errors">0</span>
            <span class="stat-label">Total Errors</span>
        </div>
        <div class="stat-box">
            <span class="stat-value" id="errors-24h">0</span>
            <span class="stat-label">Last 24 Hours</span>
        </div>
    </div>
    
    <!-- Filter Controls -->
    <div class="error-filters">
        <select id="error-type-filter">
            <option value="">All Types</option>
            <option value="IMAGE_LOAD">Image Load</option>
            <option value="NETWORK_ERROR">Network</option>
            <!-- etc -->
        </select>
        <button onclick="refreshErrors()">🔄 Refresh</button>
        <button onclick="clearErrors()">🗑️ Clear All</button>
        <button onclick="exportErrors('json')">📥 Export JSON</button>
    </div>
    
    <!-- Error List -->
    <div id="error-list" class="error-list">
        <!-- Dynamically populated -->
    </div>
</div>
```

### JavaScript Error Handling
```javascript
// Display errors in UI
function displayErrors(errors) {
    const errorList = document.getElementById('error-list');
    errorList.innerHTML = '';
    
    errors.forEach(error => {
        const errorCard = document.createElement('div');
        errorCard.className = `error-card ${error.type.toLowerCase()}`;
        errorCard.innerHTML = `
            <div class="error-header">
                <span class="error-type">${error.type}</span>
                <span class="error-time">${formatTime(error.timestamp)}</span>
            </div>
            <div class="error-message">${error.message}</div>
            ${error.exception ? `<div class="error-exception">${error.exception}</div>` : ''}
            <button onclick="showErrorDetails('${error.timestamp}')">Details</button>
        `;
        errorList.appendChild(errorCard);
    });
}

// Auto-refresh errors
setInterval(() => {
    fetch('/api/errors?limit=20')
        .then(r => r.json())
        .then(data => {
            displayErrors(data.errors);
            updateErrorStats(data);
        });
}, 10000);  // Every 10 seconds
```

## Integration Points

### 1. Wrap Critical Operations
```python
# Image loading
def load_image(path):
    try:
        return pygame.image.load(path)
    except pygame.error as e:
        error_logger.log_error('IMAGE_LOAD', f'Failed to load {path}', e)
        return None

# Weather API
def get_weather(lat, lon):
    try:
        # ... existing code ...
    except requests.exceptions.RequestException as e:
        error_logger.log_error('NETWORK_ERROR', 'Weather API failed', e)
        return None, None, None
```

### 2. Global Exception Handler
```python
def exception_handler(exctype, value, tb):
    """Catch unhandled exceptions"""
    error_logger.log_error(
        'SYSTEM_ERROR',
        'Unhandled exception',
        value,
        {'traceback': ''.join(traceback.format_tb(tb))}
    )
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_handler
```

## Notifications

### Error Alert Banner
```javascript
// Show banner if new errors
if (data.recent_errors > last_known_errors) {
    showErrorBanner(`${new_errors} new errors detected`);
}
```

### Email Alerts (Optional)
```python
def send_error_alert(error):
    """Send email for critical errors"""
    if error['type'] in ['SYSTEM_ERROR', 'DISPLAY_ERROR']:
        send_email(
            subject=f"piGallery Error: {error['type']}",
            body=format_error_email(error)
        )
```

## Performance Considerations

1. **Circular buffer** - Limit in-memory errors to 1000
2. **Rate limiting** - Don't log same error repeatedly
3. **Async logging** - Don't block main thread
4. **Log rotation** - Archive old log files
5. **Compression** - Gzip old logs

## Implementation Priority

### Phase 1 (Essential - 2 hours)
- [ ] Basic error logger class
- [ ] Wrap critical operations
- [ ] Simple error list in web UI
- [ ] `/api/errors` endpoint

### Phase 2 (Important - 3 hours)
- [ ] Error statistics
- [ ] Error filtering/search
- [ ] Export functionality
- [ ] Error details modal

### Phase 3 (Nice to have - 4 hours)
- [ ] Email notifications
- [ ] Auto-cleanup old errors
- [ ] Error trends/charts
- [ ] Debug mode toggle

---

# Delete Uploaded Images - Implementation Spec

## Overview
Safe deletion of uploaded images (only), protecting original gallery images.

## Architecture

### 1. Image Tracking System
```python
class ImageTracker:
    def __init__(self):
        self.uploaded_images = set()  # Track uploaded files
        self.load_uploaded_list()
    
    def load_uploaded_list(self):
        """Load list of uploaded images from file"""
        tracker_file = '/var/lib/pigallery/uploaded_images.json'
        if os.path.exists(tracker_file):
            with open(tracker_file, 'r') as f:
                self.uploaded_images = set(json.load(f))
    
    def mark_as_uploaded(self, filename):
        """Mark image as uploaded"""
        self.uploaded_images.add(filename)
        self.save_uploaded_list()
    
    def is_uploaded(self, filename):
        """Check if image was uploaded via web UI"""
        return filename in self.uploaded_images
    
    def remove_from_uploaded(self, filename):
        """Remove from uploaded list (after deletion)"""
        self.uploaded_images.discard(filename)
        self.save_uploaded_list()
```

### 2. Safe Delete Function
```python
def safe_delete_image(filename):
    """Safely delete image (only if uploaded)"""
    # Safety check #1: Is it uploaded?
    if not image_tracker.is_uploaded(filename):
        raise PermissionError("Cannot delete original images")
    
    # Safety check #2: Does file exist?
    file_path = get_full_path(filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {filename}")
    
    # Safety check #3: Is it in upload directory?
    upload_dir = get_upload_directory()
    if not file_path.startswith(upload_dir):
        raise PermissionError("File outside upload directory")
    
    # Move to trash instead of permanent delete
    move_to_trash(file_path)
    
    # Update tracking
    image_tracker.remove_from_uploaded(filename)
    
    return True
```

### 3. Trash/Recycle Bin
```python
class TrashBin:
    def __init__(self, trash_dir='/var/lib/pigallery/trash'):
        self.trash_dir = trash_dir
        os.makedirs(trash_dir, exist_ok=True)
    
    def move_to_trash(self, file_path):
        """Move file to trash with timestamp"""
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        trash_name = f"{timestamp}_{filename}"
        trash_path = os.path.join(self.trash_dir, trash_name)
        
        shutil.move(file_path, trash_path)
        
        # Create metadata
        metadata = {
            'original_path': file_path,
            'deleted_at': datetime.now().isoformat(),
            'file_size': os.path.getsize(trash_path)
        }
        
        with open(f"{trash_path}.meta.json", 'w') as f:
            json.dump(metadata, f)
        
        return trash_name
    
    def restore_from_trash(self, trash_name):
        """Restore file from trash"""
        trash_path = os.path.join(self.trash_dir, trash_name)
        meta_path = f"{trash_path}.meta.json"
        
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
        
        original_path = metadata['original_path']
        shutil.move(trash_path, original_path)
        os.remove(meta_path)
        
        return original_path
    
    def list_trash(self):
        """List files in trash"""
        trash_items = []
        for filename in os.listdir(self.trash_dir):
            if filename.endswith('.meta.json'):
                continue
            
            meta_file = f"{filename}.meta.json"
            if os.path.exists(os.path.join(self.trash_dir, meta_file)):
                with open(os.path.join(self.trash_dir, meta_file), 'r') as f:
                    metadata = json.load(f)
                    metadata['trash_name'] = filename
                    trash_items.append(metadata)
        
        return sorted(trash_items, key=lambda x: x['deleted_at'], reverse=True)
```

## API Endpoints

### DELETE /api/image/delete
```python
@app.route('/api/image/delete', methods=['DELETE'])
def api_delete_image():
    """Delete an uploaded image"""
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    
    try:
        # Check if uploaded
        if not image_tracker.is_uploaded(filename):
            return jsonify({
                'error': 'Cannot delete original images',
                'reason': 'safety_protection'
            }), 403
        
        # Move to trash
        trash_name = trash_bin.move_to_trash(get_full_path(filename))
        
        # Remove from tracking
        image_tracker.remove_from_uploaded(filename)
        
        # Refresh image list
        if slideshow_instance:
            slideshow_instance.refresh_images()
        
        return jsonify({
            'status': 'ok',
            'message': 'Image moved to trash',
            'trash_name': trash_name
        })
    
    except Exception as e:
        error_logger.log_error('DELETE_ERROR', f'Failed to delete {filename}', e)
        return jsonify({'error': str(e)}), 500
```

### GET /api/trash
```python
@app.route('/api/trash')
def api_list_trash():
    """List items in trash"""
    return jsonify({
        'items': trash_bin.list_trash(),
        'total_size_mb': trash_bin.get_total_size() / 1024 / 1024
    })
```

### POST /api/trash/restore
```python
@app.route('/api/trash/restore', methods=['POST'])
def api_restore_from_trash():
    """Restore image from trash"""
    data = request.json
    trash_name = data.get('trash_name')
    
    try:
        restored_path = trash_bin.restore_from_trash(trash_name)
        
        # Re-add to uploaded list
        filename = os.path.basename(restored_path)
        image_tracker.mark_as_uploaded(filename)
        
        # Refresh images
        if slideshow_instance:
            slideshow_instance.refresh_images()
        
        return jsonify({
            'status': 'ok',
            'message': 'Image restored',
            'path': restored_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### DELETE /api/trash/empty
```python
@app.route('/api/trash/empty', methods=['DELETE'])
def api_empty_trash():
    """Permanently delete all items in trash"""
    try:
        count = trash_bin.empty_trash()
        return jsonify({
            'status': 'ok',
            'message': f'Deleted {count} items permanently'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Web UI Components

### Delete Button in Preview
```html
<div class="image-preview-controls">
    <button class="btn-danger" onclick="deleteCurrentImage()" 
            id="delete-btn" style="display: none;">
        🗑️ Delete
    </button>
    <span id="delete-status"></span>
</div>

<script>
// Show delete button only for uploaded images
async function updateDeleteButton() {
    const response = await fetch('/api/image/info');
    const data = await response.json();
    
    if (data.is_uploaded) {
        document.getElementById('delete-btn').style.display = 'block';
    } else {
        document.getElementById('delete-btn').style.display = 'none';
    }
}

async function deleteCurrentImage() {
    const confirmed = confirm('Move this image to trash?');
    if (!confirmed) return;
    
    const filename = getCurrentImageFilename();
    
    try {
        const response = await fetch('/api/image/delete', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert('Image moved to trash', 'success');
            // Skip to next image
            nextImage();
        } else {
            showAlert(data.error, 'error');
        }
    } catch (error) {
        showAlert('Delete failed: ' + error.message, 'error');
    }
}
</script>
```

### Trash Viewer
```html
<div class="control-card">
    <h2>🗑️ Trash Bin</h2>
    
    <div class="trash-stats">
        <span id="trash-count">0 items</span>
        <span id="trash-size">0 MB</span>
        <button class="btn-danger" onclick="emptyTrash()">
            Empty Trash
        </button>
    </div>
    
    <div id="trash-list" class="trash-list">
        <!-- Dynamically populated -->
    </div>
</div>

<script>
async function loadTrash() {
    const response = await fetch('/api/trash');
    const data = await response.json();
    
    document.getElementById('trash-count').textContent = 
        `${data.items.length} items`;
    document.getElementById('trash-size').textContent = 
        `${data.total_size_mb.toFixed(2)} MB`;
    
    const trashList = document.getElementById('trash-list');
    trashList.innerHTML = '';
    
    data.items.forEach(item => {
        const itemCard = document.createElement('div');
        itemCard.className = 'trash-item';
        itemCard.innerHTML = `
            <div class="trash-item-name">${item.trash_name}</div>
            <div class="trash-item-date">${formatDate(item.deleted_at)}</div>
            <div class="trash-item-actions">
                <button onclick="restoreFromTrash('${item.trash_name}')">
                    ↩️ Restore
                </button>
            </div>
        `;
        trashList.appendChild(itemCard);
    });
}
</script>
```

## Safety Features

1. **Triple-check before delete**
   - Is it in uploaded list?
   - Is it in upload directory?
   - Does user confirm?

2. **Trash bin instead of immediate deletion**
   - Can be restored
   - Auto-cleanup after 30 days
   - Manual empty option

3. **Audit log**
   - Track all deletions
   - Who, what, when
   - Can review history

4. **Visual indicators**
   - Uploaded images have badge
   - Delete button only for uploaded
   - Warning messages

## Implementation Priority

### Phase 1 (Essential - 3 hours)
- [ ] Image tracker system
- [ ] Safe delete function
- [ ] `/api/image/delete` endpoint
- [ ] Delete button in UI

### Phase 2 (Important - 2 hours)
- [ ] Trash bin system
- [ ] Restore functionality
- [ ] Trash viewer UI

### Phase 3 (Nice to have - 2 hours)
- [ ] Auto-cleanup old trash
- [ ] Bulk delete
- [ ] Delete confirmation dialog
- [ ] Audit log

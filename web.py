"""
Web API endpoints for piGallery
Handles all Flask routes and web interface functionality
"""

from flask import jsonify, request, send_from_directory, send_file
import os
import sys
import subprocess
import configparser
import threading
import time
import io
import datetime
import json
import pygame
from PIL import Image
from PIL.ExifTags import TAGS
from PIL import IptcImagePlugin
from werkzeug.utils import secure_filename

# These will be set by gallery.py before routes are registered
app = None
slideshow_instance = None
telegram_notifier = None
power_action_in_progress = False
power_action_cancel_event = None
CONFIG_PATH = None
LOG_FILE = None
logger = None


def init_web(app_instance, slideshow_ref, telegram_ref, config_path, log_file, logger_instance):
    """Initialize web module with references to Flask app and global state"""
    global app, slideshow_instance, telegram_notifier, CONFIG_PATH, LOG_FILE, logger
    app = app_instance
    slideshow_instance = slideshow_ref
    telegram_notifier = telegram_ref
    CONFIG_PATH = config_path
    LOG_FILE = log_file
    logger = logger_instance
    register_routes()


def get_image_caption(img_path):
    """Read caption from image metadata (EXIF/IPTC/XMP)
    Returns caption string or None if not found"""

    def sanitize_caption(text):
        """Remove null characters and other problematic characters from caption text"""
        if not text:
            return text
        # Remove null characters and other non-printable characters
        return ''.join(c for c in text if c != '\0' and ord(c) >= 32)

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        from PIL import IptcImagePlugin
        
        if not os.path.exists(img_path):
            return None
        
        img = Image.open(img_path)
        img_format = img.format or 'JPEG'
        caption = None
        
        # For PNG files, check text chunks first
        if img_format == 'PNG':
            try:
                # PNG stores text in info dict
                if img.info:
                    # Check for "Comment" key first (Windows Explorer "Comments" property)
                    if 'Comment' in img.info:
                        caption = img.info['Comment']
                        if caption and isinstance(caption, str) and caption.strip():
                            return sanitize_caption(caption.strip())
                    # Also check for "Description" key (fallback)
                    if 'Description' in img.info:
                        caption = img.info['Description']
                        if caption and isinstance(caption, str) and caption.strip():
                            return sanitize_caption(caption.strip())
                    # Also check for "caption" key
                    if 'caption' in img.info:
                        caption = img.info['caption']
                        if caption and isinstance(caption, str) and caption.strip():
                            return sanitize_caption(caption.strip())
            except Exception:
                pass
        
        # Try EXIF UserComment (tag 37510) - this is the "Comments" field
        # Use piexif for better UserComment reading support
        try:
            import piexif
            with open(img_path, 'rb') as f:
                exif_dict = piexif.load(f.read())
            if 'Exif' in exif_dict and piexif.ExifIFD.UserComment in exif_dict['Exif']:
                comment_data = exif_dict['Exif'][piexif.ExifIFD.UserComment]
                if comment_data:
                    if isinstance(comment_data, bytes):
                        # UserComment format: encoding prefix (e.g., "ASCII\0\0\0" or "UNICODE\0\0\0\0") + text
                        # Try to decode, skipping encoding prefix if present
                        try:
                            # Check for common encoding prefixes
                            if comment_data.startswith(b'ASCII\x00\x00\x00'):
                                caption = comment_data[8:].decode('ascii', errors='replace').strip()
                            elif comment_data.startswith(b'UNICODE\x00\x00\x00\x00'):
                                caption = comment_data[12:].decode('utf-16', errors='replace').strip()
                            elif comment_data.startswith(b'JIS\x00\x00\x00\x00\x00'):
                                caption = comment_data[8:].decode('shift_jis', errors='replace').strip()
                            else:
                                # Try UTF-8 directly
                                caption = comment_data.decode('utf-8', errors='replace').strip()
                            if caption:
                                return sanitize_caption(caption)
                        except Exception:
                            pass
                    elif isinstance(comment_data, str):
                        return sanitize_caption(comment_data.strip())
        except ImportError:
            # piexif not available, try PIL
            pass
        except Exception:
            pass
        
        # Fallback: Try PIL's getexif() for UserComment
        try:
            exif = img.getexif()
            if exif and 37510 in exif:
                caption = exif[37510]
                if caption:
                    if isinstance(caption, str):
                        return sanitize_caption(caption.strip())
                    elif isinstance(caption, bytes):
                        # Try to decode, handling encoding prefix
                        if caption.startswith(b'ASCII\x00\x00\x00'):
                            return sanitize_caption(caption[8:].decode('ascii', errors='replace').strip())
                        else:
                            return sanitize_caption(caption.decode('utf-8', errors='replace').strip())
        except Exception:
            pass
        
        # Try EXIF ImageDescription (tag 270) as fallback
        try:
            exif = img.getexif()
            if exif:
                # EXIF ImageDescription is tag 270
                if 270 in exif:
                    caption = exif[270]
                    if caption and isinstance(caption, str) and caption.strip():
                        return sanitize_caption(caption.strip())
        except Exception:
            pass
        
        # Try IPTC Caption-Abstract
        try:
            iptc = IptcImagePlugin.getiptcinfo(img)
            if iptc:
                # IPTC Caption-Abstract is tag (2, 120)
                if (2, 120) in iptc:
                    caption_data = iptc[(2, 120)]
                    if caption_data:
                        # IPTC data can be bytes, string, or list
                        if isinstance(caption_data, bytes):
                            caption = caption_data.decode('utf-8', errors='replace').strip()
                        elif isinstance(caption_data, str):
                            caption = caption_data.strip()
                        elif isinstance(caption_data, (list, tuple)) and len(caption_data) > 0:
                            # Take first element if it's a list
                            first_item = caption_data[0]
                            if isinstance(first_item, bytes):
                                caption = first_item.decode('utf-8', errors='replace').strip()
                            elif isinstance(first_item, str):
                                caption = first_item.strip()
                            else:
                                caption = str(first_item).strip()
                        else:
                            caption = str(caption_data).strip()
                        
                        if caption and len(caption) > 0:
                            return sanitize_caption(caption)
        except Exception as e:
            # Silently fail IPTC reading - not all images have IPTC data
            pass
        
        # Try XMP (if available via Pillow)
        try:
            # XMP data might be in the image info
            if hasattr(img, 'info') and 'exif' in img.info:
                # Some XMP data might be embedded in EXIF
                pass
        except Exception:
            pass
        
        return None
    except Exception as e:
        print(f"[Caption] Error reading caption from {img_path}: {e}")
        return None


def get_logs(lines=200):
    """Get logs from journalctl (systemd) or log file (cross-platform)"""
    logs = []
    
    if sys.platform == 'linux':
        try:
            service_name = os.environ.get('SERVICE_NAME', 'piGallery.service')
            result = subprocess.run(
                ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip().split('\n')
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
    
    if LOG_FILE and os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return [line.rstrip('\n') for line in all_lines[-lines:]]
        except Exception as e:
            if logger:
                logger.warning(f"Error reading log file: {e}")
            return [f"Error reading log file: {e}"]
    
    return ["No logs available"]


def _format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

def _format_timestamp(timestamp):
    """Format timestamp in human readable format"""
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M')

def register_routes():
    """Register all Flask routes"""
    
    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')
    
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files"""
        return send_from_directory('static', filename)
    
    @app.route('/api/status')
    def api_status():
        """Get current slideshow status"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        # Get system stats
        system_stats = {}
        try:
            from gallery import get_memory_info, get_cpu_usage, get_cpu_temperature, get_disk_usage
            memory = get_memory_info()
            if memory is not None:
                system_stats['memory_free_mb'] = round(memory, 1)
            
            cpu = get_cpu_usage()
            if cpu is not None:
                system_stats['cpu_percent'] = round(cpu, 1)
            
            temp = get_cpu_temperature()
            if temp is not None:
                system_stats['cpu_temp'] = round(temp, 1)
            
            disk = get_disk_usage()
            if disk is not None:
                system_stats['disk_free_gb'] = round(disk['available'] / (1024 * 1024 * 1024), 2)
                system_stats['disk_used_percent'] = round(disk['percent_used'], 1)
        except Exception as e:
            print(f"[API] Error getting system stats: {e}")
        
        # Calculate time remaining until next image
        elapsed = time.time() - slideshow_instance.image_display_start_time
        # Subtract pause duration if currently paused
        if slideshow_instance.paused and slideshow_instance.pause_start_time:
            pause_duration = time.time() - slideshow_instance.pause_start_time
            elapsed -= pause_duration
        time_remaining = max(0, slideshow_instance.display_time_seconds - int(elapsed))
        
        response = {
            'current_image': slideshow_instance.current_img,
            'current_index': slideshow_instance.current_index + 1,
            'total_images': slideshow_instance.total_images,
            'temperature': slideshow_instance.current_temp,
            'weather': slideshow_instance.current_weather,
            'time': datetime.datetime.now().strftime("%I:%M %p"),
            'date': datetime.datetime.now().strftime("%d %b %Y"),
            'paused': slideshow_instance.paused,
            'display_on': slideshow_instance.is_display_on(),
            'manual_override': slideshow_instance.manual_display_override,
            'time_remaining': time_remaining,
            'delay_seconds': slideshow_instance.display_time_seconds
        }
        
        if system_stats:
            response['system'] = system_stats
        
        return jsonify(response)
    
    @app.route('/api/logs')
    def api_logs():
        """Get application logs"""
        lines = request.args.get('lines', 200, type=int)
        # Limit to reasonable range
        lines = max(50, min(1000, lines))
        
        try:
            log_lines = get_logs(lines)
            return jsonify({
                'status': 'ok',
                'lines': log_lines,
                'count': len(log_lines)
            })
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/directories', methods=['GET'])
    def api_directories():
        """List directories for folder selection"""
        path = request.args.get('path', '')
        
        if not path:
            # Return root directories
            if sys.platform == 'win32':
                # Windows: list drive letters
                import string
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
                return jsonify({'directories': drives, 'current_path': ''})
            else:
                # Unix/Linux: start from home directory
                home = os.path.expanduser('~')
                return jsonify({'directories': [home, '/'], 'current_path': ''})
        
        # Expand user path (~)
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return jsonify({'error': 'Path does not exist'}), 404
        
        if not os.path.isdir(path):
            return jsonify({'error': 'Path is not a directory'}), 400
        
        try:
            # List directories only
            dirs = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
            
            dirs.sort()
            return jsonify({
                'directories': dirs,
                'current_path': path,
                'parent_path': os.path.dirname(path) if path != os.path.dirname(path) else None
            })
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_image_path():
        """Helper function to get the current image path"""
        if slideshow_instance is None or not slideshow_instance.current_img:
            return None
        
        # Check if this is an uploaded image
        if slideshow_instance.current_img.startswith("uploaded/"):
            upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
            if upload_dir:
                upload_dir = os.path.expanduser(upload_dir)
                actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                img_path = os.path.join(upload_dir, actual_path)
            else:
                img_path = os.path.join(slideshow_instance.folder, slideshow_instance.current_img)
        else:
            img_path = os.path.join(slideshow_instance.folder, slideshow_instance.current_img)
        
        return img_path if os.path.exists(img_path) else None
    
    def set_image_caption(img_path, caption):
        """Write caption to image metadata (EXIF for JPEG, text chunks for PNG)
        Returns True if successful, False otherwise
        
        JPEG files: Uses piexif library for EXIF UserComment
        PNG files: Uses PIL's text chunk support (tEXt)
        Other formats: Attempts PIL's info dict"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            import tempfile
            import shutil
            
            if not os.path.exists(img_path):
                return False
            
            # Open image to determine format
            img = Image.open(img_path)
            img_format = img.format or 'JPEG'
            
            # Handle PNG files using text chunks
            if img_format == 'PNG':
                try:
                    from PIL import PngImagePlugin
                    
                    # PNG supports text chunks (tEXt, zTXt, iTXt)
                    # Use PngInfo for proper PNG metadata support
                    pnginfo = PngImagePlugin.PngInfo()
                    
                    # Copy existing text chunks from original image (except Comment if we're updating it)
                    if img.info:
                        for key, value in img.info.items():
                            # Skip Comment if we're setting a new caption
                            if key == 'Comment' and caption:
                                continue
                            # Only copy text values (PNG text chunks are strings)
                            if isinstance(value, str):
                                pnginfo.add_text(key, value)
                    
                    # Store caption in PNG text chunk
                    # Try multiple keys for maximum compatibility
                    # "Comment" is the standard PNG text chunk key
                    # Windows Explorer may or may not display this depending on version
                    if caption:
                        pnginfo.add_text("Comment", caption)
                        # Also add as Description for compatibility
                        pnginfo.add_text("Description", caption)
                    # If caption is empty and Comment existed, it will be omitted (removed)
                    
                    # Ensure image is fully loaded (convert to RGB/RGBA if needed for saving)
                    img.load()  # Ensure image is loaded
                    
                    # Convert palette images to RGB for better compatibility
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    elif img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                        # Convert unsupported modes to RGB
                        if img.mode in ('1', 'I', 'F'):
                            img = img.convert('RGB')
                    
                    # Save with PngInfo (this properly writes text chunks)
                    # Note: We need to preserve other PNG settings like compression
                    save_kwargs = {'format': 'PNG', 'pnginfo': pnginfo}
                    if 'compress_level' in (img.info or {}):
                        save_kwargs['compress_level'] = img.info.get('compress_level', 6)
                    
                    # Save to a temporary file first, then move it (safer)
                    import tempfile
                    import shutil
                    temp_fd, temp_path = tempfile.mkstemp(suffix='.png', dir=os.path.dirname(img_path) or '.')
                    try:
                        os.close(temp_fd)
                        img.save(temp_path, **save_kwargs)
                        img.close()
                        
                        # Replace original file
                        shutil.move(temp_path, img_path)
                        
                        # Verify the caption was written
                        verify_img = Image.open(img_path)
                        written_caption = verify_img.info.get('Comment', '')
                        written_description = verify_img.info.get('Description', '')
                        has_comment = 'Comment' in verify_img.info
                        has_description = 'Description' in verify_img.info
                        all_text_keys = [k for k, v in verify_img.info.items() if isinstance(v, str)]
                        verify_img.close()
                        
                        if caption:
                            if written_caption == caption or written_description == caption:
                                print(f"[Caption] Successfully wrote caption to PNG")
                                print(f"[Caption] Text chunks in file: {all_text_keys}")
                                print(f"[Caption] Comment value: '{written_caption}'")
                                print(f"[Caption] Description value: '{written_description}'")
                                print(f"[Caption] Note: Windows Explorer may not display PNG text chunks in Properties.")
                                print(f"[Caption] The comment is embedded in the file and can be read by image viewers.")
                                return True
                            else:
                                print(f"[Caption] Warning: Caption may not have been written correctly.")
                                print(f"[Caption] Expected: '{caption}'")
                                print(f"[Caption] Got Comment: '{written_caption}', Description: '{written_description}'")
                                return False
                        else:
                            # Caption removed
                            if not has_comment and not has_description:
                                print(f"[Caption] Successfully removed caption from PNG")
                                return True
                            else:
                                print(f"[Caption] Warning: Caption may not have been fully removed")
                                return False
                    except Exception as e:
                        # Clean up temp file on error
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except:
                            pass
                        raise e
                except Exception as e:
                    print(f"[Caption] Error writing PNG text chunk: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        img.close()
                    except:
                        pass
                    return False
            
            # Handle JPEG files using EXIF (piexif)
            elif img_format in ('JPEG', 'JPG'):
                try:
                    import piexif
                    
                    # Read current EXIF data (or create new if none exists)
                    try:
                        with open(img_path, 'rb') as f:
                            exif_dict = piexif.load(f.read())
                    except Exception:
                        # No existing EXIF, create new dict
                        exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
                    
                    # Set UserComment (tag 37510 in Exif IFD) - this is the "Comments" field in image viewers
                    # UserComment format: 8-byte encoding identifier + text bytes
                    if 'Exif' not in exif_dict:
                        exif_dict['Exif'] = {}
                    
                    if caption:
                        # Use ASCII encoding prefix for better compatibility
                        # Format: "ASCII\0\0\0" (8 bytes) + text bytes
                        caption_bytes = caption.encode('utf-8')
                        user_comment = b'ASCII\x00\x00\x00' + caption_bytes
                    else:
                        user_comment = b'ASCII\x00\x00\x00'
                    
                    exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment
                    
                    # Convert EXIF dict to bytes
                    exif_bytes = piexif.dump(exif_dict)
                    
                    # Read original image data
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    
                    # Create temporary file for output
                    temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                    try:
                        os.close(temp_fd)
                        
                        # Insert EXIF into image and write to temp file
                        piexif.insert(exif_bytes, img_data, temp_path)
                        
                        # Replace original file with updated one
                        shutil.move(temp_path, img_path)
                        return True
                    except Exception as e:
                        # Clean up temp file on error
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except:
                            pass
                        raise e
                except ImportError:
                    print("[Caption] piexif not available for JPEG. Install with: pip install piexif")
                    return False
                except Exception as e:
                    print(f"[Caption] Error using piexif for JPEG: {e}")
                    return False
            
            # Handle other formats (TIFF, etc.) - try PIL's info dict
            else:
                try:
                    # For other formats, try to save in info dict
                    info = img.info.copy() if img.info else {}
                    if caption:
                        info['caption'] = caption
                    else:
                        if 'caption' in info:
                            del info['caption']
                    
                    # Save with updated info
                    img.save(img_path, format=img_format, **info)
                    return True
                except Exception as e:
                    print(f"[Caption] Error writing caption for {img_format}: {e}")
                    return False
                
        except Exception as e:
            print(f"[Caption] Error setting caption for {img_path}: {e}")
            return False
    
    @app.route('/api/image/preview')
    def api_image_preview():
        """Get image as thumbnail preview (current image or specified path)"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503

        # Check if a specific path was requested
        requested_path = request.args.get('path')

        try:
            from PIL import Image
            from flask import send_file
            import io

            if requested_path:
                # Handle specific path request (for uploaded images modal)
                if requested_path.startswith('uploaded/'):
                    # This is an uploaded image
                    upload_dir = get_upload_directory()
                    if not upload_dir:
                        return jsonify({'error': 'Upload directory not configured'}), 500

                    filename = os.path.basename(requested_path)  # Security: prevent directory traversal
                    img_path = os.path.join(upload_dir, filename)

                    if not os.path.exists(img_path):
                        return jsonify({'error': 'Image not found'}), 404

                    # Verify it's within upload directory
                    if not os.path.commonpath([upload_dir, os.path.abspath(img_path)]).startswith(upload_dir):
                        return jsonify({'error': 'Invalid path'}), 403
                else:
                    # This might be a regular gallery image
                    img_path = os.path.join(slideshow_instance.folder, requested_path)
                    if not os.path.exists(img_path):
                        return jsonify({'error': 'Image not found'}), 404
            else:
                # Default: current slideshow image
                if not slideshow_instance.current_img:
                    return jsonify({'error': 'No image loaded'}), 404

                img_path = get_image_path()
                if not img_path:
                    return jsonify({'error': 'Image file not found'}), 404

            # Create thumbnail (max 200x200 for modal, maintains aspect ratio)
            img = Image.open(img_path)
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)

            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)

            return send_file(img_bytes, mimetype='image/jpeg')

        except ImportError:
            # Fallback: serve original image if PIL not available
            if requested_path:
                if requested_path.startswith('uploaded/'):
                    upload_dir = get_upload_directory()
                    if upload_dir:
                        filename = os.path.basename(requested_path)
                        img_path = os.path.join(upload_dir, filename)
                        if os.path.exists(img_path):
                            return send_from_directory(upload_dir, filename)

                # For gallery images, we can't serve without PIL
                return jsonify({'error': 'PIL required for image processing'}), 500
            else:
                # Original fallback logic
                img_path = get_image_path()
                if img_path:
                    if slideshow_instance.current_img.startswith("uploaded/"):
                        upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
                        if upload_dir:
                            upload_dir = os.path.expanduser(upload_dir)
                            actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                            return send_from_directory(upload_dir, actual_path)
                    else:
                        return send_from_directory(slideshow_instance.folder, slideshow_instance.current_img)
                return jsonify({'error': 'Image not found'}), 404

        except Exception as e:
            print(f"[Web] Error generating preview: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/image/full')
    def api_image_full():
        """Get current image at full resolution"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        if not slideshow_instance.current_img:
            return jsonify({'error': 'No image loaded'}), 404
        
        try:
            img_path = get_image_path()
            if not img_path:
                return jsonify({'error': 'Image file not found'}), 404
            
            if slideshow_instance.current_img.startswith("uploaded/"):
                upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
                if upload_dir:
                    upload_dir = os.path.expanduser(upload_dir)
                    actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                    return send_from_directory(upload_dir, actual_path)
                else:
                    # Fallback: try default uploaded subdirectory in images folder
                    actual_path = slideshow_instance.current_img.replace("uploaded/", "", 1).replace("uploaded\\", "", 1)
                    return send_from_directory(os.path.join(slideshow_instance.folder, 'uploaded'), actual_path)
            else:
                return send_from_directory(slideshow_instance.folder, slideshow_instance.current_img)
        except Exception as e:
            print(f"[Web] Error serving full image: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/image/caption', methods=['GET'])
    def api_get_caption():
        """Get caption from current image metadata"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        if not slideshow_instance.current_img:
            return jsonify({'error': 'No image loaded'}), 404
        
        try:
            img_path = get_image_path()
            if not img_path:
                return jsonify({'error': 'Image file not found'}), 404
            
            caption = get_image_caption(img_path)
            return jsonify({'status': 'ok', 'caption': caption or ''})
        except Exception as e:
            print(f"[Web] Error getting caption: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/image/caption', methods=['POST'])
    def api_set_caption():
        """Set caption in current image metadata"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        if not slideshow_instance.current_img:
            return jsonify({'error': 'No image loaded'}), 404
        
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'error': 'Invalid JSON'}), 400
            
            caption = data.get('caption', '').strip()
            img_path = get_image_path()
            if not img_path:
                return jsonify({'error': 'Image file not found'}), 404
            
            # Check if file is writable
            if not os.access(img_path, os.W_OK):
                return jsonify({'error': 'Image file is not writable'}), 403
            
            success = set_image_caption(img_path, caption)
            if success:
                # Clear cached caption so it reloads on next draw
                if slideshow_instance._cached_caption_image == slideshow_instance.current_img:
                    slideshow_instance._cached_caption = None
                    slideshow_instance._cached_caption_image = None
                # Force redraw to show updated caption immediately
                slideshow_instance.force_redraw = True
                return jsonify({'status': 'ok', 'message': 'Caption saved successfully'})
            else:
                return jsonify({'error': 'Failed to save caption. Make sure piexif is installed: pip install piexif'}), 500
        except Exception as e:
            print(f"[Web] Error setting caption: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/next', methods=['POST'])
    def api_next():
        """Go to next image"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        with slideshow_instance.control_lock:
            slideshow_instance.next_image()
            slideshow_instance.force_redraw = True  # Force immediate redraw
            slideshow_instance.image_display_start_time = time.time()  # Reset countdown
        
        return jsonify({'status': 'ok', 'current_image': slideshow_instance.current_img})
    
    @app.route('/api/prev', methods=['POST'])
    def api_prev():
        """Go to previous image"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        with slideshow_instance.control_lock:
            slideshow_instance.prev_image()
            slideshow_instance.force_redraw = True  # Force immediate redraw
            slideshow_instance.image_display_start_time = time.time()  # Reset countdown
        
        return jsonify({'status': 'ok', 'current_image': slideshow_instance.current_img})
    
    @app.route('/api/pause', methods=['POST'])
    def api_pause():
        """Toggle pause state"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        slideshow_instance.paused = not slideshow_instance.paused
        if slideshow_instance.paused:
            slideshow_instance.pause_start_time = time.time()
        else:
            slideshow_instance.pause_start_time = None
        status = 'paused' if slideshow_instance.paused else 'playing'
        print(f"[Web] Slideshow {status}")
        
        return jsonify({'status': 'ok', 'paused': slideshow_instance.paused})
    
    @app.route('/api/display', methods=['POST'])
    def api_display():
        """Control display on/off"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        data = request.json
        action = data.get('action')  # 'on', 'off', or 'auto'
        
        if action == 'on':
            slideshow_instance.manual_display_override = True
        elif action == 'off':
            slideshow_instance.manual_display_override = False
        elif action == 'auto':
            slideshow_instance.manual_display_override = None
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        # Force immediate redraw to apply display changes
        slideshow_instance.force_redraw = True
        
        print(f"[Web] Display set to: {action}")
        return jsonify({'status': 'ok', 'action': action})
    
    @app.route('/api/system/shutdown', methods=['POST'])
    def api_shutdown():
        """Shutdown the system"""
        global power_action_in_progress, power_action_cancel_event
        
        # Check if a power action is already in progress
        if power_action_in_progress:
            return jsonify({'error': 'A shutdown or restart is already in progress'}), 409
        
        data = request.json or {}
        countdown = int(data.get('countdown', 10))
        
        print(f"[Web] Shutdown requested with {countdown}s countdown")
        
        # Set flag to prevent multiple requests
        power_action_in_progress = True
        
        # Create cancel event
        import threading
        power_action_cancel_event = threading.Event()
        
        # Send notification if telegram is enabled
        if telegram_notifier:
            telegram_notifier.notify_system_alert(
                'shutdown',
                f'Manual shutdown initiated from web UI (countdown: {countdown}s)'
            )
        
        # Start shutdown in a separate thread to allow response to be sent
        def do_shutdown():
            global power_action_in_progress, power_action_cancel_event
            import time
            time.sleep(0.5)  # Give time for response to be sent
            
            try:
                if pygame.get_init():
                    screen = pygame.display.get_surface()
                print(f"[System] Shutdown initiated, countdown={countdown}s")
                
                # Countdown with cancel check
                for remaining in range(countdown, 0, -1):
                    if power_action_cancel_event and power_action_cancel_event.is_set():
                        print("[System] Shutdown cancelled")
                        if screen:
                            screen.fill((0, 0, 0))
                            font = pygame.font.SysFont(None, 48)
                            text = font.render("Shutdown cancelled", True, (255, 255, 255))
                            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                            screen.blit(text, rect)
                            pygame.display.flip()
                            time.sleep(1)  # Brief message, then immediately restore
                        
                        # Force redraw to show image again immediately
                        if slideshow_instance:
                            slideshow_instance.force_redraw = True
                            # Trigger immediate redraw by drawing now
                            try:
                                slideshow_instance.draw_image()
                                pygame.display.flip()
                            except:
                                pass  # If draw fails, force_redraw will handle it on next loop
                        
                        power_action_in_progress = False
                        power_action_cancel_event = None
                        return
                    
                    if screen:
                        screen.fill((0, 0, 0))
                        font = pygame.font.SysFont(None, 48)
                        text = font.render(f"Shutting down in {remaining} seconds...", True, (255, 255, 255))
                        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                        screen.blit(text, rect)
                        pygame.display.flip()
                    else:
                        print(f"Shutting down in {remaining} seconds...")
                    time.sleep(1)
                
                # Execute shutdown - try Linux command, catch failure on Windows
                try:
                    subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # On Windows or if command fails
                    print("[System] Shutdown command not available")
            except subprocess.CalledProcessError as e:
                print(f"Failed to shutdown: {e}")
                power_action_in_progress = False
                power_action_cancel_event = None
        
        thread = threading.Thread(target=do_shutdown, daemon=True)
        thread.start()
        
        return jsonify({'status': 'ok', 'message': f'Shutdown initiated with {countdown}s countdown'})
    
    @app.route('/api/system/restart', methods=['POST'])
    def api_restart():
        """Restart the system"""
        global power_action_in_progress, power_action_cancel_event
        
        # Check if a power action is already in progress
        if power_action_in_progress:
            return jsonify({'error': 'A shutdown or restart is already in progress'}), 409
        
        data = request.json or {}
        countdown = int(data.get('countdown', 10))
        
        print(f"[Web] Restart requested with {countdown}s countdown")
        
        # Set flag to prevent multiple requests
        power_action_in_progress = True
        
        # Create cancel event
        import threading
        power_action_cancel_event = threading.Event()
        
        # Send notification if telegram is enabled
        if telegram_notifier:
            telegram_notifier.notify_system_alert(
                'restart',
                f'Manual restart initiated from web UI (countdown: {countdown}s)'
            )
        
        # Start restart in a separate thread
        def do_restart():
            global power_action_in_progress, power_action_cancel_event
            import time
            time.sleep(0.5)  # Give time for response to be sent
            
            try:
                if pygame.get_init():
                    screen = pygame.display.get_surface()
                print(f"[System] Restart initiated, countdown={countdown}s")
                
                # Countdown with cancel check
                for remaining in range(countdown, 0, -1):
                    if power_action_cancel_event and power_action_cancel_event.is_set():
                        print("[System] Restart cancelled")
                        if screen:
                            screen.fill((0, 0, 0))
                            font = pygame.font.SysFont(None, 48)
                            text = font.render("Restart cancelled", True, (255, 255, 255))
                            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                            screen.blit(text, rect)
                            pygame.display.flip()
                            time.sleep(1)  # Brief message, then immediately restore
                        
                        # Force redraw to show image again immediately
                        if slideshow_instance:
                            slideshow_instance.force_redraw = True
                            # Trigger immediate redraw by drawing now
                            try:
                                slideshow_instance.draw_image()
                                pygame.display.flip()
                            except:
                                pass  # If draw fails, force_redraw will handle it on next loop
                        
                        power_action_in_progress = False
                        power_action_cancel_event = None
                        return
                    
                    if screen:
                        screen.fill((0, 0, 0))
                        font = pygame.font.SysFont(None, 48)
                        text = font.render(f"Restarting in {remaining} seconds...", True, (255, 255, 255))
                        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
                        screen.blit(text, rect)
                        pygame.display.flip()
                    else:
                        print(f"Restarting in {remaining} seconds...")
                    time.sleep(1)
                
                # Restart command - try Linux command, catch failure on Windows
                try:
                    subprocess.run(["sudo", "reboot"], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # On Windows or if command fails
                    print("[System] Restart command not available")
            except subprocess.CalledProcessError as e:
                print(f"Failed to restart: {e}")
                power_action_in_progress = False
                power_action_cancel_event = None
        
        thread = threading.Thread(target=do_restart, daemon=True)
        thread.start()
        
        return jsonify({'status': 'ok', 'message': f'Restart initiated with {countdown}s countdown'})
    
    @app.route('/api/system/cancel', methods=['POST'])
    def api_cancel_power_action():
        """Cancel ongoing shutdown or restart"""
        global power_action_in_progress
    
        if not power_action_in_progress:
            return jsonify({'error': 'No power action in progress'}), 400
        
        if power_action_cancel_event:
            power_action_cancel_event.set()
            print("[Web] Power action cancelled by user")
            # Note: Don't clear power_action_cancel_event here - let the thread detect and clear it
            # We can reset the flag now so user can start another action if needed
            power_action_in_progress = False
            return jsonify({'status': 'ok', 'message': 'Power action cancelled'})
        else:
            return jsonify({'error': 'Cannot cancel at this time'}), 400
    
    @app.route('/api/upload', methods=['POST'])
    def api_upload():
        """Upload new image to separate upload directory"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return jsonify({'error': 'Invalid file type. Only JPG and PNG allowed'}), 400
        
        filename = secure_filename(file.filename)
        
        # Determine upload directory
        upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
        if not upload_dir:
            # Default: create 'uploaded' subdirectory in images directory
            upload_dir = os.path.join(slideshow_instance.folder, 'uploaded')
        else:
            # Use configured upload directory
            upload_dir = os.path.expanduser(upload_dir)  # Support ~ for home directory
        
        # Create upload directory if it doesn't exist
        try:
            os.makedirs(upload_dir, exist_ok=True)
            # Verify directory was actually created
            if not os.path.exists(upload_dir):
                return jsonify({'error': f'Failed to create upload directory: {upload_dir}'}), 500
            if not os.path.isdir(upload_dir):
                return jsonify({'error': f'Upload path exists but is not a directory: {upload_dir}'}), 500
            print(f"[Web] Upload directory: {upload_dir}")
        except PermissionError as e:
            return jsonify({'error': f'Permission denied creating upload directory: {e}'}), 500
        except Exception as e:
            return jsonify({'error': f'Failed to create upload directory: {e}'}), 500
        
        # Verify directory is writable
        try:
            test_file = os.path.join(upload_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            return jsonify({'error': f'Upload directory is not writable: {e}'}), 500
        
        # Save file to upload directory
        filepath = os.path.join(upload_dir, filename)
        
        # Handle filename conflicts (add number if exists)
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base_name}_{counter}{ext}"
            filepath = os.path.join(upload_dir, filename)
            counter += 1
        
        try:
            file.save(filepath)
            print(f"[Web] Uploaded new image: {filename} to {upload_dir}")
        except Exception as e:
            error_msg = f'Failed to save file: {e}'
            if telegram_notifier:
                telegram_notifier.notify_error(error_msg, f"Upload: {filename}")
            return jsonify({'error': error_msg}), 500
        
        # If caption provided, save it to image metadata
        caption = request.form.get('caption', '').strip()
        if caption:
            try:
                success = set_image_caption(filepath, caption)
                if success:
                    print(f"[Web] Added caption to uploaded image: {filename}")
                else:
                    print(f"[Web] Warning: Failed to save caption to {filename}")
            except Exception as e:
                print(f"[Web] Error saving caption to {filename}: {e}")
                # Don't fail the upload if caption saving fails
        
        # Refresh images to include the new upload (refresh_images scans recursively)
        slideshow_instance.refresh_images()
        slideshow_instance.rebuild_navigation_preserve_current()
        slideshow_instance.force_redraw = True
        
        # Notify Telegram of upload
        if telegram_notifier:
            telegram_notifier.notify_upload(filename)
        
        return jsonify({'status': 'ok', 'filename': filename, 'upload_dir': upload_dir, 'caption_added': bool(caption)})

    def get_upload_directory():
        """Get the upload directory path"""
        if slideshow_instance is None:
            return None

        upload_dir = slideshow_instance.config.get('upload_directory', '').strip()
        if not upload_dir:
            # Default: create 'uploaded' subdirectory in images directory
            upload_dir = os.path.join(slideshow_instance.folder, 'uploaded')
        else:
            # Use configured upload directory
            upload_dir = os.path.expanduser(upload_dir)

        return upload_dir

    @app.route('/api/uploaded-images', methods=['GET'])
    def api_list_uploaded_images():
        """List all uploaded images with metadata"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503

        upload_dir = get_upload_directory()
        if not upload_dir or not os.path.exists(upload_dir):
            return jsonify({'images': [], 'total': 0})

        images = []
        try:
            for filename in os.listdir(upload_dir):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')) and not filename.startswith('.'):
                    filepath = os.path.join(upload_dir, filename)
                    stat = os.stat(filepath)

                    # Always read directly from image metadata (source of truth)
                    image_caption = ''
                    try:
                        metadata_caption = get_image_caption(filepath)
                        if metadata_caption:
                            image_caption = metadata_caption
                    except Exception as e:
                        print(f"[Web] Could not read caption from {filename} metadata: {e}")

                    images.append({
                        'filename': filename,
                        'path': f'uploaded/{filename}',  # Relative path for frontend
                        'size': stat.st_size,
                        'size_human': _format_file_size(stat.st_size),
                        'upload_date': stat.st_mtime,
                        'upload_date_human': _format_timestamp(stat.st_mtime),
                        'caption': image_caption
                    })

            # Sort by upload date (newest first)
            images.sort(key=lambda x: x['upload_date'], reverse=True)

        except Exception as e:
            print(f"[Web] Error listing uploaded images: {e}")
            return jsonify({'error': f'Failed to list images: {str(e)}'}), 500

        return jsonify({
            'images': images,
            'total': len(images),
            'upload_directory': upload_dir
        })

    @app.route('/api/uploaded-images/delete', methods=['POST'])
    def api_delete_uploaded_images():
        """Delete selected uploaded images"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503

        try:
            data = request.get_json()
            if not data or 'images' not in data:
                return jsonify({'error': 'No images specified for deletion'}), 400

            images_to_delete = data['images']
            if not isinstance(images_to_delete, list):
                return jsonify({'error': 'Images must be provided as a list'}), 400

            upload_dir = get_upload_directory()
            if not upload_dir:
                return jsonify({'error': 'Upload directory not configured'}), 500

            deleted = []
            failed = []

            for image_path in images_to_delete:
                try:
                    # Security check: ensure the image is within the upload directory
                    # Remove any path traversal attempts
                    safe_path = os.path.basename(image_path)  # Only allow filename, no directory traversal
                    full_path = os.path.join(upload_dir, safe_path)

                    # Additional security: verify the resolved path is still within upload directory
                    if not os.path.commonpath([upload_dir, os.path.abspath(full_path)]).startswith(upload_dir):
                        failed.append({'path': image_path, 'error': 'Invalid path'})
                        continue

                    if not os.path.exists(full_path):
                        failed.append({'path': image_path, 'error': 'File not found'})
                        continue

                    # Only allow deletion of image files
                    if not full_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                        failed.append({'path': image_path, 'error': 'Not an image file'})
                        continue

                    os.remove(full_path)
                    deleted.append(image_path)
                    print(f"[Web] Deleted uploaded image: {safe_path}")

                except Exception as e:
                    failed.append({'path': image_path, 'error': str(e)})

            # Notify Telegram of deletions
            if telegram_notifier and deleted:
                telegram_notifier.notify_system_alert(
                    'image_cleanup',
                    f'Deleted {len(deleted)} uploaded image(s)'
                )

            if deleted:  # Only refresh if images were actually deleted
                slideshow_instance.refresh_images()
                slideshow_instance.rebuild_navigation_preserve_current()
                slideshow_instance.force_redraw = True

            result = {
                'deleted': deleted,
                'failed': failed,
                'total_deleted': len(deleted),
                'total_failed': len(failed)
            }

            if failed:
                result['warning'] = f'{len(failed)} image(s) could not be deleted'

            return jsonify(result)

        except Exception as e:
            print(f"[Web] Error deleting uploaded images: {e}")
            return jsonify({'error': f'Failed to delete images: {str(e)}'}), 500

    @app.route('/api/uploaded-images/rename', methods=['POST'])
    def api_rename_uploaded_image():
        """Rename an uploaded image file"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503

        try:
            data = request.get_json()
            if not data or 'old_filename' not in data or 'new_filename' not in data:
                return jsonify({'error': 'old_filename and new_filename required'}), 400

            old_filename = data['old_filename']
            new_filename = data['new_filename']

            # Validate filenames
            if not old_filename or not new_filename:
                return jsonify({'error': 'Filenames cannot be empty'}), 400

            # Prevent directory traversal
            if '..' in old_filename or '..' in new_filename or '/' in old_filename or '/' in new_filename:
                return jsonify({'error': 'Invalid filename'}), 400

            # Only allow image extensions
            allowed_ext = ['.jpg', '.jpeg', '.png']
            if not any(new_filename.lower().endswith(ext) for ext in allowed_ext):
                return jsonify({'error': 'New filename must have .jpg, .jpeg, or .png extension'}), 400

            upload_dir = get_upload_directory()
            if not upload_dir:
                return jsonify({'error': 'Upload directory not configured'}), 500

            old_path = os.path.join(upload_dir, old_filename)
            new_path = os.path.join(upload_dir, new_filename)

            # Check if old file exists
            if not os.path.exists(old_path):
                return jsonify({'error': 'Original file not found'}), 404

            # Check if new file already exists
            if os.path.exists(new_path):
                return jsonify({'error': 'A file with that name already exists'}), 409

            # Perform the rename
            os.rename(old_path, new_path)

            # Refresh images to update the cache
            slideshow_instance.refresh_images()
            slideshow_instance.force_redraw = True

            print(f"[Web] Renamed uploaded image: {old_filename} -> {new_filename}")
            return jsonify({'status': 'ok', 'old_filename': old_filename, 'new_filename': new_filename})

        except Exception as e:
            print(f"[Web] Error renaming uploaded image: {e}")
            return jsonify({'error': f'Failed to rename image: {str(e)}'}), 500

    @app.route('/api/uploaded-images/caption', methods=['POST'])
    def api_update_uploaded_image_caption():
        """Update caption for an uploaded image"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503

        try:
            data = request.get_json()
            if not data or 'path' not in data:
                return jsonify({'error': 'path and caption required'}), 400

            image_path = data['path']
            caption = data.get('caption', '')

            # Validate path (should be uploaded/filename format)
            if not image_path.startswith('uploaded/'):
                return jsonify({'error': 'Invalid image path'}), 400

            filename = os.path.basename(image_path)
            if not filename:
                return jsonify({'error': 'Invalid filename'}), 400

            upload_dir = get_upload_directory()
            if not upload_dir:
                return jsonify({'error': 'Upload directory not configured'}), 500

            full_path = os.path.join(upload_dir, filename)

            # Check if file exists
            if not os.path.exists(full_path):
                return jsonify({'error': 'Image file not found'}), 404

            # Store caption ONLY in image metadata - JSON is temporary/cache only
            success = set_image_caption(full_path, caption)

            if success:
                print(f"[Web] Successfully embedded caption in {filename} metadata: '{caption}'")

                if slideshow_instance.current_img and slideshow_instance.current_img.endswith(filename):
                    slideshow_instance._cached_caption = None
                    slideshow_instance._cached_caption_image = None

                slideshow_instance.force_redraw = True
                return jsonify({'status': 'ok', 'filename': filename, 'caption': caption})
            else:
                return jsonify({'error': 'Failed to save caption to image metadata'}), 500

        except Exception as e:
            print(f"[Web] Error updating caption: {e}")
            return jsonify({'error': f'Failed to update caption: {str(e)}'}), 500

    @app.route('/api/uploaded-images/cleanup-cache', methods=['POST'])
    def api_cleanup_captions_cache():
        """Clean up temporary captions cache when modal is closed"""
        print("[Web] Cleanup cache endpoint called")
        try:
            upload_dir = get_upload_directory()
            print(f"[Web] Upload directory: {upload_dir}")
            if not upload_dir:
                print("[Web] No upload directory configured")
                return jsonify({'status': 'ok'})  # No upload dir = nothing to clean

            captions_file = os.path.join(upload_dir, '.captions.json')
            print(f"[Web] Checking for cache file: {captions_file}")
            print(f"[Web] Cache file exists: {os.path.exists(captions_file)}")

            if os.path.exists(captions_file):
                try:
                    os.remove(captions_file)
                    print(f"[Web] Successfully removed captions cache: {captions_file}")
                except Exception as e:
                    print(f"[Web] Could not remove captions cache: {e}")
                    return jsonify({'error': 'Could not remove cache file'}), 500
            else:
                print("[Web] No cache file found to remove")

            return jsonify({'status': 'ok'})
        except Exception as e:
            print(f"[Web] Error cleaning up captions cache: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/settings', methods=['GET', 'POST'])
    def api_settings():
        """Get or update settings"""
        if slideshow_instance is None:
            return jsonify({'error': 'Slideshow not initialized'}), 503
        
        if request.method == 'GET':
            return jsonify({
                'show_time': slideshow_instance.config.get('show_time', 'true'),
                'show_date': slideshow_instance.config.get('show_date', 'true'),
                'show_temperature': slideshow_instance.config.get('show_temperature', 'true'),
                'show_weather_code': slideshow_instance.config.get('show_weather_code', 'true'),
                'show_filename': slideshow_instance.config.get('show_filename', 'true'),
                'show_caption': slideshow_instance.config.get('show_caption', 'true'),
                'delay_seconds': slideshow_instance.display_time_seconds,
                'display_off_time': slideshow_instance.config.get('display_off_time', '23:00'),
                'display_on_time': slideshow_instance.config.get('display_on_time', '05:00'),
                'location_city_suburb': slideshow_instance.config.get('location_city_suburb', 'Sydney, Australia'),
                'display_correction_horizontal': slideshow_instance.config.get('display_correction_horizontal', '1.0'),
                'display_correction_vertical': slideshow_instance.config.get('display_correction_vertical', '1.0'),
                'ui_text_alpha': slideshow_instance.config.get('ui_text_alpha', '192'),
                'weather_update_seconds': slideshow_instance.config.get('weather_update_seconds', '900'),
                'upload_directory': slideshow_instance.config.get('upload_directory', ''),
                'images_directory': slideshow_instance.folder,
                'shutdown_on_display_off': slideshow_instance.config.get('shutdown_on_display_off', 'true'),
                'shutdown_countdown_seconds': slideshow_instance.config.get('shutdown_countdown_seconds', '10'),
                'sort_order': slideshow_instance.config.get('sort_order', 'random'),
                'sort_reverse': slideshow_instance.config.get('sort_reverse', 'false')
            })
        
        elif request.method == 'POST':
            data = request.json
            
            # Track changes for Telegram notifications
            # Update config values
            if 'show_time' in data:
                old_val = slideshow_instance.config.get('show_time', 'true')
                new_val = str(data['show_time']).lower()
                slideshow_instance.config['show_time'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('show_time', old_val, new_val)
            if 'show_date' in data:
                old_val = slideshow_instance.config.get('show_date', 'true')
                new_val = str(data['show_date']).lower()
                slideshow_instance.config['show_date'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('show_date', old_val, new_val)
            if 'show_temperature' in data:
                old_val = slideshow_instance.config.get('show_temperature', 'true')
                new_val = str(data['show_temperature']).lower()
                slideshow_instance.config['show_temperature'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('show_temperature', old_val, new_val)
            if 'show_weather_code' in data:
                old_val = slideshow_instance.config.get('show_weather_code', 'true')
                new_val = str(data['show_weather_code']).lower()
                slideshow_instance.config['show_weather_code'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('show_weather_code', old_val, new_val)
            if 'show_filename' in data:
                old_val = slideshow_instance.config.get('show_filename', 'true')
                new_val = str(data['show_filename']).lower()
                slideshow_instance.config['show_filename'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('show_filename', old_val, new_val)
            if 'show_caption' in data:
                old_val = slideshow_instance.config.get('show_caption', 'true')
                new_val = str(data['show_caption']).lower()
                slideshow_instance.config['show_caption'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('show_caption', old_val, new_val)
            if 'delay_seconds' in data:
                old_val = slideshow_instance.display_time_seconds
                new_val = int(data['delay_seconds'])
                slideshow_instance.display_time_seconds = new_val
                # Reset countdown timer when delay changes
                slideshow_instance.image_display_start_time = time.time()
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('delay_seconds', str(old_val), str(new_val))
            if 'display_off_time' in data:
                old_val = slideshow_instance.config.get('display_off_time', '23:00')
                new_val = data['display_off_time']
                slideshow_instance.config['display_off_time'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('display_off_time', old_val, new_val)
            if 'display_on_time' in data:
                old_val = slideshow_instance.config.get('display_on_time', '05:00')
                new_val = data['display_on_time']
                slideshow_instance.config['display_on_time'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('display_on_time', old_val, new_val)
            if 'location_city_suburb' in data:
                old_val = slideshow_instance.config.get('location_city_suburb', 'Sydney, Australia')
                new_val = data['location_city_suburb']
                slideshow_instance.config['location_city_suburb'] = new_val
                # Re-geocode the location
                slideshow_instance.city_suburb = new_val
                from gallery import get_coords_from_place
                lat, lon = get_coords_from_place(new_val)
                if lat and lon:
                    slideshow_instance.lat = lat
                    slideshow_instance.long = lon
                    print(f"[Web] Updated location to {new_val}: lat={lat}, lon={lon}")
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('location_city_suburb', old_val, new_val)
            if 'display_correction_horizontal' in data:
                old_val = slideshow_instance.config.get('display_correction_horizontal', '1.0')
                new_val = str(data['display_correction_horizontal'])
                slideshow_instance.config['display_correction_horizontal'] = new_val
                # Force redraw when correction changes
                slideshow_instance.force_redraw = True
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('display_correction_horizontal', old_val, new_val)
            if 'display_correction_vertical' in data:
                old_val = slideshow_instance.config.get('display_correction_vertical', '1.0')
                new_val = str(data['display_correction_vertical'])
                slideshow_instance.config['display_correction_vertical'] = new_val
                # Force redraw when correction changes
                slideshow_instance.force_redraw = True
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('display_correction_vertical', old_val, new_val)
            if 'ui_text_alpha' in data:
                old_val = slideshow_instance.config.get('ui_text_alpha', '192')
                new_val = str(int(data['ui_text_alpha']))
                slideshow_instance.config['ui_text_alpha'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('ui_text_alpha', old_val, new_val)
            if 'weather_update_seconds' in data:
                old_val = slideshow_instance.config.get('weather_update_seconds', '900')
                new_val = str(int(data['weather_update_seconds']))
                slideshow_instance.config['weather_update_seconds'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('weather_update_seconds', old_val, new_val)
            if 'upload_directory' in data:
                old_val = slideshow_instance.config.get('upload_directory', '')
                new_val = data['upload_directory'].strip()
                slideshow_instance.config['upload_directory'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('upload_directory', old_val or '(empty)', new_val or '(empty)')
            if 'shutdown_on_display_off' in data:
                old_val = slideshow_instance.config.get('shutdown_on_display_off', 'true')
                new_val = str(data['shutdown_on_display_off']).lower()
                slideshow_instance.config['shutdown_on_display_off'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('shutdown_on_display_off', old_val, new_val)
            if 'shutdown_countdown_seconds' in data:
                old_val = slideshow_instance.config.get('shutdown_countdown_seconds', '10')
                new_val = str(int(data['shutdown_countdown_seconds']))
                slideshow_instance.config['shutdown_countdown_seconds'] = new_val
                if telegram_notifier and old_val != new_val:
                    telegram_notifier.notify_settings_change('shutdown_countdown_seconds', old_val, new_val)

            # Handle sorting settings
            sort_settings_changed = False
            if 'sort_order' in data:
                old_val = slideshow_instance.config.get('sort_order', 'random')
                new_val = data['sort_order']
                slideshow_instance.config['sort_order'] = new_val
                if old_val != new_val:
                    sort_settings_changed = True
                    print(f"[Web] Sort order changed: {old_val} -> {new_val}")
            if 'sort_reverse' in data:
                old_val = slideshow_instance.config.get('sort_reverse', 'false')
                new_val = str(data['sort_reverse']).lower()
                slideshow_instance.config['sort_reverse'] = new_val
                if old_val != new_val:
                    sort_settings_changed = True
                    print(f"[Web] Sort reverse changed: {old_val} -> {new_val}")

            # Re-sort existing images if sorting settings changed
            if sort_settings_changed:
                print(f"[Web] Sorting settings changed, rescanning and re-sorting all images")

                # Clear current queue and history to force complete rescan
                old_images = slideshow_instance.images + slideshow_instance.history
                if slideshow_instance.current_img:
                    old_images.append(slideshow_instance.current_img)

                slideshow_instance.images = []
                slideshow_instance.history = []
                slideshow_instance.forward_stack = []
                slideshow_instance.current_index = -1
                slideshow_instance.current_img = None
                # Clear circular navigation cache
                if hasattr(slideshow_instance, '_all_images'):
                    slideshow_instance._all_images = []

                # Rescan directory to get all images with new sorting
                slideshow_instance.refresh_images()

                # If no new images were found (all were already in old_images), we need to sort the old ones
                if not slideshow_instance.images and old_images:
                    print(f"[Web] No new images found, sorting {len(old_images)} existing images")
                    slideshow_instance.images = slideshow_instance.sort_images(list(set(old_images)))

                # Reset slideshow position to start of newly sorted queue
                slideshow_instance.current_index = -1
                slideshow_instance.history = []
                slideshow_instance.forward_stack = []

                # Advance to first image in sorted queue and trigger immediate display
                slideshow_instance.next_image()
                slideshow_instance.force_redraw = True
                print(f"[Web] Reset slideshow with {len(slideshow_instance.images)} sorted images and triggered display update")
            if 'images_directory' in data:
                # Update images directory (requires restart to take full effect)
                old_val = slideshow_instance.folder
                new_dir = data['images_directory'].strip()
                # Only refresh if the directory actually changed
                if new_dir != old_val:
                    if os.path.exists(new_dir) and os.path.isdir(new_dir):
                        slideshow_instance.folder = new_dir
                        slideshow_instance.config['images_directory'] = new_dir
                        # Refresh images from new directory
                        slideshow_instance.images = []
                        slideshow_instance.history = []
                        slideshow_instance.current_index = -1
                        slideshow_instance.refresh_images()
                        if slideshow_instance.images:
                            slideshow_instance.next_image()
                        print(f"[Web] Images directory changed to: {new_dir}")
                        if telegram_notifier and old_val != new_dir:
                            telegram_notifier.notify_settings_change('images_directory', old_val, new_dir)
                    else:
                        return jsonify({'error': 'Invalid directory path'}), 400
                else:
                    # Directory hasn't changed, just update config without refreshing
                    slideshow_instance.config['images_directory'] = new_dir
            
            # Force a redraw to apply settings immediately
            slideshow_instance.force_redraw = True
    
            # If display correction changed, need to reload current image
            if 'display_correction_horizontal' in data or 'display_correction_vertical' in data:
                # Clear cached image so it reloads with new scaling
                if hasattr(slideshow_instance, '_cached_image_name'):
                    slideshow_instance._cached_image_name = None
            
            # Optionally save to config.ini
            save_to_config = data.get('save_to_config', False)
            if save_to_config:
                config = configparser.ConfigParser()
                if os.path.exists(CONFIG_PATH):
                    config.read(CONFIG_PATH)
                
                if 'gallery' not in config:
                    config['gallery'] = {}
                
                # Update config file
                for key in ['show_time', 'show_date', 'show_temperature', 'show_weather_code',
                           'show_filename', 'show_caption', 'display_off_time', 'display_on_time',
                           'location_city_suburb', 'display_correction_horizontal', 'display_correction_vertical',
                           'ui_text_alpha', 'weather_update_seconds', 'upload_directory', 'images_directory',
                           'shutdown_on_display_off', 'shutdown_countdown_seconds', 'sort_order', 'sort_reverse']:
                    if key in data:
                        config['gallery'][key] = str(data[key])
                
                if 'delay_seconds' in data:
                    config['gallery']['delay_seconds'] = str(data['delay_seconds'])
                
                with open(CONFIG_PATH, 'w') as f:
                    config.write(f)
                
                print("[Web] Settings saved to config.ini")
            
            print(f"[Web] Settings updated: {data}")
            return jsonify({'status': 'ok'})


def start_web_server(host='0.0.0.0', port=5000):
    """Start Flask web server in background thread"""
    print(f"[Web] Starting web server on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)
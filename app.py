from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import mimetypes
import time
from datetime import datetime
import json
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Global bot status (in production, use proper state management)
BOT_CONNECTED = True
BOT_THREAD_ALIVE = True

# Supported file formats and size limits
SUPPORTED_FORMATS = {
    'images': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    'documents': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', '7z'],
    'audio': ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'],
    'video': ['mp4', 'avi', 'mov', 'mkv', 'webm', '3gp', 'flv'],
    'stickers': ['webp']
}

FILE_SIZE_LIMITS = {
    'images': 16 * 1024 * 1024,    # 16MB
    'documents': 32 * 1024 * 1024, # 32MB
    'audio': 16 * 1024 * 1024,     # 16MB
    'video': 64 * 1024 * 1024,     # 64MB
    'stickers': 1 * 1024 * 1024    # 1MB
}

def format_phone_number(phone):
    """Format phone number to WhatsApp format"""
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # If starts with 0, replace with 62
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    # If doesn't start with 62, assume it's Indonesian number
    elif not phone.startswith('62'):
        phone = '62' + phone
    
    # Validate phone number length (10-15 digits after country code)
    if len(phone) < 10 or len(phone) > 15:
        raise ValueError("Invalid phone number format")
    
    return phone + "@s.whatsapp.net"

def validate_file(file, media_type):
    """Validate uploaded file"""
    if not file or file.filename == '':
        raise ValueError("No file provided")
    
    # Get file extension
    filename = secure_filename(file.filename)
    if '.' not in filename:
        raise ValueError("File must have an extension")
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    # Check if extension is supported
    if extension not in SUPPORTED_FORMATS[media_type]:
        raise ValueError(f"Invalid file type. Allowed: {SUPPORTED_FORMATS[media_type]}")
    
    # Check file size (approximate, since we're reading from stream)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > FILE_SIZE_LIMITS[media_type]:
        size_mb = FILE_SIZE_LIMITS[media_type] / (1024 * 1024)
        raise ValueError(f"File too large. Max size for {media_type}: {size_mb}MB")
    
    return filename, size

def save_file(file, filename):
    """Save uploaded file temporarily"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filepath

def cleanup_file(filepath):
    """Remove temporary file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass

def simulate_whatsapp_send(phone, message_type, **kwargs):
    """Simulate sending WhatsApp message (replace with actual WhatsApp API)"""
    # In real implementation, this would use Neonize library or WhatsApp Business API
    print(f"[WHATSAPP] Sending {message_type} to {phone}")
    print(f"[WHATSAPP] Data: {kwargs}")
    
    # Simulate some processing time
    time.sleep(0.5)
    
    # Return success (in real implementation, handle actual errors)
    return True

@app.route('/')
def index():
    """Render the main website"""
    return render_template('index.html')

@app.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({
        "service": "WhatsApp API - Complete Media Support",
        "status": "running",
        "bot_connected": BOT_CONNECTED,
        "version": "2.0.0",
        "features": {
            "text_messages": "✅ Working",
            "image_messages": "✅ Working",
            "document_messages": "✅ Working",
            "audio_messages": "✅ Available",
            "video_messages": "✅ Available",
            "sticker_messages": "✅ Available"
        },
        "supported_formats": SUPPORTED_FORMATS,
        "file_size_limits": {
            "images": "16MB",
            "documents": "32MB",
            "audio": "16MB",
            "video": "64MB",
            "stickers": "1MB"
        },
        "endpoints": [
            "POST /api/send-message - Send text message",
            "POST /api/send-image - Send image with caption",
            "POST /api/send-document - Send document with caption",
            "POST /api/send-audio - Send audio file",
            "POST /api/send-video - Send video with caption",
            "POST /api/send-sticker - Send WebP sticker",
            "GET /api/status - Bot status"
        ]
    })

@app.route('/api/status')
def bot_status():
    """Get bot status"""
    return jsonify({
        "bot_connected": BOT_CONNECTED,
        "thread_alive": BOT_THREAD_ALIVE,
        "upload_folder": app.config['UPLOAD_FOLDER'],
        "supported_formats": SUPPORTED_FORMATS,
        "file_size_limits": {
            "images": "16MB",
            "documents": "32MB",
            "audio": "16MB",
            "video": "64MB",
            "stickers": "1MB"
        },
        "message": "Bot status retrieved"
    })

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Send text message"""
    try:
        if not BOT_CONNECTED:
            return jsonify({"status": "error", "message": "Bot not connected"}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON data"}), 400
        
        phone = data.get('phone')
        message = data.get('message')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        if not message:
            return jsonify({"status": "error", "message": "Message text required"}), 400
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Send message (replace with actual WhatsApp API)
        success = simulate_whatsapp_send(formatted_phone, 'text', message=message)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Text message sent successfully",
                "data": {
                    "phone": phone,
                    "message": message,
                    "type": "text",
                    "timestamp": str(datetime.now())
                }
            })
        else:
            return jsonify({"status": "error", "message": "Failed to send message"}), 500
            
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/send-image', methods=['POST'])
def send_image():
    """Send image with optional caption"""
    try:
        if not BOT_CONNECTED:
            return jsonify({"status": "error", "message": "Bot not connected"}), 503
        
        phone = request.form.get('phone')
        caption = request.form.get('caption', '')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file
        filename, file_size = validate_file(file, 'images')
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Save file temporarily
        filepath = save_file(file, filename)
        
        try:
            # Send image (replace with actual WhatsApp API)
            success = simulate_whatsapp_send(
                formatted_phone, 'image', 
                filepath=filepath, caption=caption
            )
            
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Image sent successfully",
                    "data": {
                        "phone": phone,
                        "filename": filename,
                        "caption": caption,
                        "type": "image",
                        "file_size_kb": round(file_size / 1024, 2),
                        "timestamp": str(datetime.now())
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Failed to send image"}), 500
        finally:
            cleanup_file(filepath)
            
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/send-document', methods=['POST'])
def send_document():
    """Send document with optional caption"""
    try:
        if not BOT_CONNECTED:
            return jsonify({"status": "error", "message": "Bot not connected"}), 503
        
        phone = request.form.get('phone')
        caption = request.form.get('caption', '')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file
        filename, file_size = validate_file(file, 'documents')
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Save file temporarily
        filepath = save_file(file, filename)
        
        try:
            # Send document (replace with actual WhatsApp API)
            success = simulate_whatsapp_send(
                formatted_phone, 'document', 
                filepath=filepath, caption=caption
            )
            
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Document sent successfully",
                    "data": {
                        "phone": phone,
                        "filename": filename,
                        "caption": caption,
                        "type": "document",
                        "file_size_kb": round(file_size / 1024, 2),
                        "timestamp": str(datetime.now())
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Failed to send document"}), 500
        finally:
            cleanup_file(filepath)
            
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/send-audio', methods=['POST'])
def send_audio():
    """Send audio file"""
    try:
        if not BOT_CONNECTED:
            return jsonify({"status": "error", "message": "Bot not connected"}), 503
        
        phone = request.form.get('phone')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file
        filename, file_size = validate_file(file, 'audio')
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Save file temporarily
        filepath = save_file(file, filename)
        
        try:
            # Send audio (replace with actual WhatsApp API)
            success = simulate_whatsapp_send(
                formatted_phone, 'audio', 
                filepath=filepath
            )
            
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Audio sent successfully",
                    "data": {
                        "phone": phone,
                        "filename": filename,
                        "type": "audio",
                        "file_size_kb": round(file_size / 1024, 2),
                        "timestamp": str(datetime.now())
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Failed to send audio"}), 500
        finally:
            cleanup_file(filepath)
            
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/send-video', methods=['POST'])
def send_video():
    """Send video with optional caption"""
    try:
        if not BOT_CONNECTED:
            return jsonify({"status": "error", "message": "Bot not connected"}), 503
        
        phone = request.form.get('phone')
        caption = request.form.get('caption', '')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file
        filename, file_size = validate_file(file, 'video')
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Save file temporarily
        filepath = save_file(file, filename)
        
        try:
            # Send video (replace with actual WhatsApp API)
            success = simulate_whatsapp_send(
                formatted_phone, 'video', 
                filepath=filepath, caption=caption
            )
            
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Video sent successfully",
                    "data": {
                        "phone": phone,
                        "filename": filename,
                        "caption": caption,
                        "type": "video",
                        "file_size_kb": round(file_size / 1024, 2),
                        "timestamp": str(datetime.now())
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Failed to send video"}), 500
        finally:
            cleanup_file(filepath)
            
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/send-sticker', methods=['POST'])
def send_sticker():
    """Send WebP sticker"""
    try:
        if not BOT_CONNECTED:
            return jsonify({"status": "error", "message": "Bot not connected"}), 503
        
        phone = request.form.get('phone')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file
        filename, file_size = validate_file(file, 'stickers')
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Save file temporarily
        filepath = save_file(file, filename)
        
        try:
            # Send sticker (replace with actual WhatsApp API)
            success = simulate_whatsapp_send(
                formatted_phone, 'sticker', 
                filepath=filepath
            )
            
            if success:
                return jsonify({
                    "status": "success",
                    "message": "Sticker sent successfully",
                    "data": {
                        "phone": phone,
                        "filename": filename,
                        "type": "sticker",
                        "file_size_kb": round(file_size / 1024, 2),
                        "timestamp": str(datetime.now())
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Failed to send sticker"}), 500
        finally:
            cleanup_file(filepath)
            
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"status": "error", "message": "File too large"}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    print("🚀 WhatsApp API Server Starting...")
    print("📱 Available endpoints:")
    print("   GET  / - Main website")
    print("   GET  /api - API information")
    print("   GET  /api/status - Bot status")
    print("   POST /api/send-message - Send text message")
    print("   POST /api/send-image - Send image")
    print("   POST /api/send-document - Send document")
    print("   POST /api/send-audio - Send audio")
    print("   POST /api/send-video - Send video")
    print("   POST /api/send-sticker - Send sticker")
    print("\n✅ Server running on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

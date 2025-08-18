from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
import os
import mimetypes
import time
from datetime import datetime
import json
import re
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# ==========================================
# KONFIGURASI API WHATSAPP - UBAH DI SINI
# ==========================================
WHATSAPP_API_CONFIG = {
    'host': os.getenv('WHATSAPP_API_HOST', 'IP-API'),  # IP server WhatsApp API
    'port': os.getenv('WHATSAPP_API_PORT', '5000'),           # Port server WhatsApp API
    'use_https': os.getenv('WHATSAPP_API_HTTPS', 'false').lower() == 'true',
    'api_key': os.getenv('WHATSAPP_API_KEY', ''),             # API key jika diperlukan
    'timeout': int(os.getenv('WHATSAPP_API_TIMEOUT', '30'))   # Timeout dalam detik
}

# Build base URL for WhatsApp API
if WHATSAPP_API_CONFIG['use_https']:
    WHATSAPP_API_BASE_URL = f"https://{WHATSAPP_API_CONFIG['host']}:{WHATSAPP_API_CONFIG['port']}"
else:
    WHATSAPP_API_BASE_URL = f"http://{WHATSAPP_API_CONFIG['host']}:{WHATSAPP_API_CONFIG['port']}"

print(f"🔗 WhatsApp API URL: {WHATSAPP_API_BASE_URL}")

# Local bot status for frontend display
LOCAL_BOT_STATUS = {
    'connected': False,
    'last_check': None,
    'api_available': False
}

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

def check_whatsapp_api_status():
    """Check if external WhatsApp API is available"""
    try:
        response = requests.get(
            f"{WHATSAPP_API_BASE_URL}/api/status",
            timeout=5,
            headers={'X-API-Key': WHATSAPP_API_CONFIG['api_key']} if WHATSAPP_API_CONFIG['api_key'] else {}
        )
        
        if response.status_code == 200:
            data = response.json()
            LOCAL_BOT_STATUS['connected'] = data.get('bot_connected', False)
            LOCAL_BOT_STATUS['api_available'] = True
            LOCAL_BOT_STATUS['last_check'] = datetime.now()
            return True
        else:
            LOCAL_BOT_STATUS['connected'] = False
            LOCAL_BOT_STATUS['api_available'] = False
            return False
            
    except Exception as e:
        print(f"❌ WhatsApp API check failed: {e}")
        LOCAL_BOT_STATUS['connected'] = False
        LOCAL_BOT_STATUS['api_available'] = False
        LOCAL_BOT_STATUS['last_check'] = datetime.now()
        return False

def send_to_whatsapp_api(endpoint, method='POST', data=None, files=None):
    """Send request to external WhatsApp API"""
    try:
        url = f"{WHATSAPP_API_BASE_URL}{endpoint}"
        headers = {}
        
        # Add API key if configured
        if WHATSAPP_API_CONFIG['api_key']:
            headers['X-API-Key'] = WHATSAPP_API_CONFIG['api_key']
        
        # Send request
        if method == 'POST':
            if files:
                # For file uploads, don't set Content-Type (let requests handle it)
                response = requests.post(
                    url, 
                    data=data, 
                    files=files, 
                    headers=headers,
                    timeout=WHATSAPP_API_CONFIG['timeout']
                )
            else:
                # For JSON data
                headers['Content-Type'] = 'application/json'
                response = requests.post(
                    url, 
                    json=data, 
                    headers=headers,
                    timeout=WHATSAPP_API_CONFIG['timeout']
                )
        else:
            response = requests.get(
                url, 
                headers=headers,
                timeout=WHATSAPP_API_CONFIG['timeout']
            )
        
        return response
        
    except requests.exceptions.Timeout:
        raise Exception(f"WhatsApp API timeout after {WHATSAPP_API_CONFIG['timeout']} seconds")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Cannot connect to WhatsApp API at {WHATSAPP_API_BASE_URL}")
    except Exception as e:
        raise Exception(f"WhatsApp API error: {str(e)}")

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
    
    return phone

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

# HTML Template (embedded untuk kemudahan copy-paste)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="id" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp API - Complete Media Support | Kirim Pesan, Gambar, Video, Audio</title>
    <meta name="description" content="WhatsApp API lengkap untuk mengirim pesan text, gambar, video, audio, dokumen dan sticker. REST API mudah digunakan dengan dukungan berbagai format media.">
    <meta name="keywords" content="whatsapp api, send message api, whatsapp bot, api wa, kirim pesan whatsapp, whatsapp business api">
    <meta name="author" content="WhatsApp API Service">
    
    <!-- Open Graph -->
    <meta property="og:title" content="WhatsApp API - Complete Media Support">
    <meta property="og:description" content="API lengkap untuk mengirim berbagai jenis pesan WhatsApp dengan mudah">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://yoursite.com">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="WhatsApp API - Complete Media Support">
    <meta name="twitter:description" content="API lengkap untuk mengirim berbagai jenis pesan WhatsApp dengan mudah">
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #25D366 0%, #128C7E 50%, #075E54 100%);
        }
        
        .glass-effect {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .feature-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        
        .api-endpoint {
            border-left: 4px solid #25D366;
            background: linear-gradient(90deg, rgba(37, 211, 102, 0.05) 0%, transparent 100%);
        }
        
        .pulse-green {
            animation: pulse-green 2s infinite;
        }
        
        @keyframes pulse-green {
            0%, 100% { box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(37, 211, 102, 0); }
        }
        
        .pulse-red {
            animation: pulse-red 2s infinite;
        }
        
        @keyframes pulse-red {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        }
        
        .typing-animation::after {
            content: '|';
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
        
        .loading {
            display: none;
        }
        
        .loading.show {
            display: inline-block;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-50 font-sans">
    <!-- Navigation -->
    <nav class="gradient-bg shadow-lg sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center py-4">
                <div class="flex items-center space-x-3">
                    <i class="fab fa-whatsapp text-3xl text-white"></i>
                    <div>
                        <h1 class="text-xl font-bold text-white">WhatsApp API Frontend</h1>
                        <p class="text-xs text-green-100">Connected to {{ api_url }}</p>
                    </div>
                </div>
                
                <div class="hidden md:flex items-center space-x-6">
                    <a href="#features" class="text-white hover:text-green-100 transition-colors">
                        <i class="fas fa-star mr-2"></i>Features
                    </a>
                    <a href="#endpoints" class="text-white hover:text-green-100 transition-colors">
                        <i class="fas fa-code mr-2"></i>API Endpoints
                    </a>
                    <a href="#demo" class="text-white hover:text-green-100 transition-colors">
                        <i class="fas fa-play mr-2"></i>Try Demo
                    </a>
                    <div id="status-indicator" class="flex items-center">
                        <div class="w-3 h-3 bg-gray-400 rounded-full mr-2"></div>
                        <span class="text-gray-200 text-sm">Checking...</span>
                    </div>
                </div>
                
                <!-- Mobile menu button -->
                <button id="mobile-menu-btn" class="md:hidden text-white">
                    <i class="fas fa-bars text-xl"></i>
                </button>
            </div>
            
            <!-- Mobile menu -->
            <div id="mobile-menu" class="md:hidden pb-4 hidden">
                <div class="flex flex-col space-y-3">
                    <a href="#features" class="text-white hover:text-green-100 transition-colors">
                        <i class="fas fa-star mr-2"></i>Features
                    </a>
                    <a href="#endpoints" class="text-white hover:text-green-100 transition-colors">
                        <i class="fas fa-code mr-2"></i>API Endpoints
                    </a>
                    <a href="#demo" class="text-white hover:text-green-100 transition-colors">
                        <i class="fas fa-play mr-2"></i>Try Demo
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- API Connection Status Alert -->
    <div id="api-status-alert" class="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 hidden">
        <div class="flex items-center max-w-6xl mx-auto px-4">
            <i class="fas fa-exclamation-triangle mr-3"></i>
            <div>
                <p class="font-bold">API Connection Status</p>
                <p id="api-status-message">Checking WhatsApp API connection...</p>
            </div>
            <button onclick="checkAPIStatus()" class="ml-auto bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600">
                <i class="fas fa-sync-alt mr-2"></i>Retry
            </button>
        </div>
    </div>

    <!-- Hero Section -->
    <section class="gradient-bg text-white py-20">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <div class="mb-8">
                <i class="fab fa-whatsapp text-8xl mb-6 animate-bounce"></i>
                <h2 class="text-5xl md:text-6xl font-bold mb-6">
                    WhatsApp API<br>
                    <span class="text-green-200 typing-animation">Frontend Interface</span>
                </h2>
                <p class="text-xl md:text-2xl text-green-100 mb-4 max-w-3xl mx-auto">
                    Interface untuk mengirim pesan WhatsApp melalui API yang berjalan di server terpisah.
                </p>
                <div class="bg-white/10 rounded-lg p-4 max-w-2xl mx-auto mb-8">
                    <p class="text-sm text-green-100">
                        <i class="fas fa-server mr-2"></i>
                        <strong>API Server:</strong> {{ api_url }}
                    </p>
                </div>
            </div>
            
            <div class="flex flex-col sm:flex-row justify-center items-center space-y-4 sm:space-y-0 sm:space-x-6 mb-12">
                <a href="#demo" class="bg-white text-green-600 px-8 py-4 rounded-full font-bold text-lg hover:bg-green-50 transform hover:scale-105 transition-all duration-200 shadow-lg">
                    <i class="fas fa-rocket mr-2"></i>Try Demo Now
                </a>
                <a href="#endpoints" class="border-2 border-white text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-white hover:text-green-600 transition-all duration-200">
                    <i class="fas fa-book mr-2"></i>View Documentation
                </a>
            </div>
            
            <!-- Stats -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
                <div class="glass-effect rounded-lg p-6">
                    <i class="fas fa-paper-plane text-3xl text-green-200 mb-2"></i>
                    <div class="text-2xl font-bold">6</div>
                    <div class="text-green-100 text-sm">Message Types</div>
                </div>
                <div class="glass-effect rounded-lg p-6">
                    <i class="fas fa-file text-3xl text-green-200 mb-2"></i>
                    <div class="text-2xl font-bold">25+</div>
                    <div class="text-green-100 text-sm">File Formats</div>
                </div>
                <div class="glass-effect rounded-lg p-6">
                    <i class="fas fa-upload text-3xl text-green-200 mb-2"></i>
                    <div class="text-2xl font-bold">64MB</div>
                    <div class="text-green-100 text-sm">Max File Size</div>
                </div>
                <div class="glass-effect rounded-lg p-6">
                    <i class="fas fa-server text-3xl text-green-200 mb-2"></i>
                    <div class="text-2xl font-bold">API</div>
                    <div class="text-green-100 text-sm">Separated</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Rest of the HTML content would be the same as before -->
    <!-- Demo Section -->
    <section id="demo" class="py-20 bg-white">
        <div class="max-w-4xl mx-auto px-4">
            <div class="text-center mb-16">
                <h3 class="text-4xl font-bold text-gray-800 mb-4">
                    <i class="fas fa-play text-green-500 mr-3"></i>
                    Try Demo
                </h3>
                <p class="text-xl text-gray-600 max-w-3xl mx-auto">
                    Test semua fitur API langsung dari browser. Kirim pesan, gambar, dokumen, dan media lainnya ke server WhatsApp API.
                </p>
            </div>
            
            <div class="bg-gray-50 rounded-xl p-8 shadow-lg">
                <!-- Tab Navigation -->
                <div class="flex flex-wrap justify-center mb-8 bg-white rounded-lg p-2 shadow-inner">
                    <button onclick="showTab('text')" id="tab-text" class="tab-btn active px-4 py-2 rounded-lg text-sm font-medium transition-all">
                        <i class="fas fa-comment mr-2"></i>Text
                    </button>
                    <button onclick="showTab('image')" id="tab-image" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition-all">
                        <i class="fas fa-image mr-2"></i>Image
                    </button>
                    <button onclick="showTab('document')" id="tab-document" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition-all">
                        <i class="fas fa-file mr-2"></i>Document
                    </button>
                    <button onclick="showTab('audio')" id="tab-audio" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition-all">
                        <i class="fas fa-microphone mr-2"></i>Audio
                    </button>
                    <button onclick="showTab('video')" id="tab-video" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition-all">
                        <i class="fas fa-video mr-2"></i>Video
                    </button>
                    <button onclick="showTab('sticker')" id="tab-sticker" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition-all">
                        <i class="fas fa-smile mr-2"></i>Sticker
                    </button>
                </div>
                
                <!-- Phone Number Input (common for all tabs) -->
                <div class="mb-6">
                    <label class="block text-gray-700 font-medium mb-2">
                        <i class="fas fa-phone mr-2"></i>Nomor WhatsApp
                    </label>
                    <input type="tel" id="phone-input" placeholder="081234567890 atau +6281234567890" 
                           class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent">
                    <p class="text-sm text-gray-500 mt-1">
                        <i class="fas fa-info-circle mr-1"></i>
                        Format otomatis ke +62 (Indonesia)
                    </p>
                </div>
                
                <!-- Text Message Tab -->
                <div id="text-tab" class="tab-content">
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-comment mr-2"></i>Pesan Text
                        </label>
                        <textarea id="text-message" placeholder="Tulis pesan Anda di sini..." rows="4"
                                  class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"></textarea>
                    </div>
                    <button onclick="sendTextMessage()" class="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition-colors">
                        <i class="fas fa-paper-plane mr-2"></i>
                        <span>Kirim Pesan</span>
                        <i class="fas fa-spinner loading ml-2"></i>
                    </button>
                </div>
                
                <!-- Image Tab -->
                <div id="image-tab" class="tab-content hidden">
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-image mr-2"></i>Upload Gambar
                        </label>
                        <input type="file" id="image-file" accept="image/*"
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent">
                        <p class="text-sm text-gray-500 mt-1">JPG, PNG, GIF, WebP - Max 16MB</p>
                    </div>
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-comment mr-2"></i>Caption (Optional)
                        </label>
                        <textarea id="image-caption" placeholder="Caption untuk gambar..." rows="3"
                                  class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"></textarea>
                    </div>
                    <button onclick="sendImageMessage()" class="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition-colors">
                        <i class="fas fa-image mr-2"></i>
                        <span>Kirim Gambar</span>
                        <i class="fas fa-spinner loading ml-2"></i>
                    </button>
                </div>
                
                <!-- Document Tab -->
                <div id="document-tab" class="tab-content hidden">
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-file mr-2"></i>Upload Dokumen
                        </label>
                        <input type="file" id="document-file" 
                               accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar,.7z"
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent">
                        <p class="text-sm text-gray-500 mt-1">PDF, DOC, XLS, PPT, TXT, ZIP - Max 32MB</p>
                    </div>
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-comment mr-2"></i>Caption (Optional)
                        </label>
                        <textarea id="document-caption" placeholder="Deskripsi dokumen..." rows="3"
                                  class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"></textarea>
                    </div>
                    <button onclick="sendDocumentMessage()" class="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition-colors">
                        <i class="fas fa-file mr-2"></i>
                        <span>Kirim Dokumen</span>
                        <i class="fas fa-spinner loading ml-2"></i>
                    </button>
                </div>
                
                <!-- Audio Tab -->
                <div id="audio-tab" class="tab-content hidden">
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-microphone mr-2"></i>Upload Audio
                        </label>
                        <input type="file" id="audio-file" accept="audio/*"
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent">
                        <p class="text-sm text-gray-500 mt-1">MP3, WAV, OGG, M4A, AAC, FLAC - Max 16MB</p>
                    </div>
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center">
                            <i class="fas fa-info-circle text-blue-500 mr-2"></i>
                            <div class="text-sm text-blue-700">
                                <strong>Audio Tips:</strong> File akan dikirim sebagai voice message di WhatsApp.
                            </div>
                        </div>
                    </div>
                    <button onclick="sendAudioMessage()" class="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition-colors">
                        <i class="fas fa-microphone mr-2"></i>
                        <span>Kirim Audio</span>
                        <i class="fas fa-spinner loading ml-2"></i>
                    </button>
                </div>
                
                <!-- Video Tab -->
                <div id="video-tab" class="tab-content hidden">
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-video mr-2"></i>Upload Video
                        </label>
                        <input type="file" id="video-file" accept="video/*"
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent">
                        <p class="text-sm text-gray-500 mt-1">MP4, AVI, MOV, MKV, WebM, 3GP - Max 64MB</p>
                    </div>
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-comment mr-2"></i>Caption (Optional)
                        </label>
                        <textarea id="video-caption" placeholder="Caption untuk video..." rows="3"
                                  class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"></textarea>
                    </div>
                    <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center">
                            <i class="fas fa-info-circle text-purple-500 mr-2"></i>
                            <div class="text-sm text-purple-700">
                                <strong>Video Tips:</strong> File besar akan dicompress otomatis. Thumbnail akan dibuat secara otomatis.
                            </div>
                        </div>
                    </div>
                    <button onclick="sendVideoMessage()" class="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition-colors">
                        <i class="fas fa-video mr-2"></i>
                        <span>Kirim Video</span>
                        <i class="fas fa-spinner loading ml-2"></i>
                    </button>
                </div>
                
                <!-- Sticker Tab -->
                <div id="sticker-tab" class="tab-content hidden">
                    <div class="mb-6">
                        <label class="block text-gray-700 font-medium mb-2">
                            <i class="fas fa-smile mr-2"></i>Upload Sticker
                        </label>
                        <input type="file" id="sticker-file" accept=".webp"
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent">
                        <p class="text-sm text-gray-500 mt-1">WebP format only - Max 1MB</p>
                    </div>
                    <div class="bg-pink-50 border border-pink-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center mb-3">
                            <i class="fas fa-info-circle text-pink-500 mr-2"></i>
                            <div class="text-sm text-pink-700 font-medium">Sticker Requirements:</div>
                        </div>
                        <ul class="text-sm text-pink-700 space-y-1 ml-6">
                            <li>• Format: WebP only</li>
                            <li>• Size: Maximum 1MB</li>
                            <li>• Dimensions: Recommended 512x512px</li>
                            <li>• Background: Transparent recommended</li>
                        </ul>
                        <div class="mt-3 text-xs text-pink-600">
                            💡 <strong>Tip:</strong> Convert PNG/JPG to WebP using online tools
                        </div>
                    </div>
                    <button onclick="sendStickerMessage()" class="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600 transition-colors">
                        <i class="fas fa-smile mr-2"></i>
                        <span>Kirim Sticker</span>
                        <i class="fas fa-spinner loading ml-2"></i>
                    </button>
                </div>
                
                <!-- Response Area -->
                <div id="response-area" class="mt-8 p-4 bg-white rounded-lg border border-gray-200 hidden">
                    <h4 class="font-bold text-gray-800 mb-2">
                        <i class="fas fa-terminal mr-2"></i>Response
                    </h4>
                    <pre id="response-content" class="text-sm text-gray-600 whitespace-pre-wrap"></pre>
                </div>
            </div>
        </div>
    </section>

    <!-- JavaScript -->
    <script>
        // Configuration for external WhatsApp API
        const FRONTEND_API_BASE = window.location.origin;
        
        // Mobile menu toggle
        document.getElementById('mobile-menu-btn').addEventListener('click', function() {
            const mobileMenu = document.getElementById('mobile-menu');
            mobileMenu.classList.toggle('hidden');
        });

        // Tab functionality
        function showTab(tabName) {
            // Hide all tab contents
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => content.classList.add('hidden'));
            
            // Remove active class from all tab buttons
            const tabButtons = document.querySelectorAll('.tab-btn');
            tabButtons.forEach(btn => {
                btn.classList.remove('active', 'bg-green-500', 'text-white');
                btn.classList.add('text-gray-600', 'hover:text-gray-800');
            });
            
            // Show selected tab content
            document.getElementById(tabName + '-tab').classList.remove('hidden');
            
            // Add active class to selected tab button
            const activeBtn = document.getElementById('tab-' + tabName);
            activeBtn.classList.add('active', 'bg-green-500', 'text-white');
            activeBtn.classList.remove('text-gray-600', 'hover:text-gray-800');
        }

        // Initialize default tab
        showTab('text');

        // Show response function
        function showResponse(response, isError = false) {
            const responseArea = document.getElementById('response-area');
            const responseContent = document.getElementById('response-content');
            
            responseArea.classList.remove('hidden');
            responseContent.textContent = JSON.stringify(response, null, 2);
            
            if (isError) {
                responseArea.classList.add('border-red-500', 'bg-red-50');
                responseArea.classList.remove('border-gray-200', 'bg-white', 'border-green-500', 'bg-green-50');
            } else {
                responseArea.classList.add('border-green-500', 'bg-green-50');
                responseArea.classList.remove('border-gray-200', 'bg-white', 'border-red-500', 'bg-red-50');
            }
            
            // Scroll to response
            responseArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Show loading state
        function showLoading(button) {
            const loading = button.querySelector('.loading');
            const span = button.querySelector('span');
            loading.classList.add('show');
            span.textContent = 'Sending...';
            button.disabled = true;
        }

        // Hide loading state
        function hideLoading(button, originalText) {
            const loading = button.querySelector('.loading');
            const span = button.querySelector('span');
            loading.classList.remove('show');
            span.textContent = originalText;
            button.disabled = false;
        }

        // Get phone number
        function getPhoneNumber() {
            const phone = document.getElementById('phone-input').value.trim();
            if (!phone) {
                throw new Error('Nomor WhatsApp harus diisi');
            }
            return phone;
        }

        // Send text message via frontend API
        async function sendTextMessage() {
            const button = event.target;
            const originalText = 'Kirim Pesan';
            
            try {
                showLoading(button);
                
                const phone = getPhoneNumber();
                const message = document.getElementById('text-message').value.trim();
                
                if (!message) {
                    throw new Error('Pesan text harus diisi');
                }

                const response = await fetch(`${FRONTEND_API_BASE}/api/send-message`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        phone: phone,
                        message: message
                    })
                });

                const result = await response.json();
                
                if (response.ok) {
                    showResponse(result);
                    document.getElementById('text-message').value = '';
                } else {
                    showResponse(result, true);
                }
                
            } catch (error) {
                showResponse({ error: error.message }, true);
            } finally {
                hideLoading(button, originalText);
            }
        }

        // Send image message
        async function sendImageMessage() {
            const button = event.target;
            const originalText = 'Kirim Gambar';
            
            try {
                showLoading(button);
                
                const phone = getPhoneNumber();
                const fileInput = document.getElementById('image-file');
                const caption = document.getElementById('image-caption').value.trim();
                
                if (!fileInput.files[0]) {
                    throw new Error('File gambar harus dipilih');
                }

                const formData = new FormData();
                formData.append('phone', phone);
                formData.append('file', fileInput.files[0]);
                if (caption) formData.append('caption', caption);

                const response = await fetch(`${FRONTEND_API_BASE}/api/send-image`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    showResponse(result);
                    fileInput.value = '';
                    document.getElementById('image-caption').value = '';
                } else {
                    showResponse(result, true);
                }
                
            } catch (error) {
                showResponse({ error: error.message }, true);
            } finally {
                hideLoading(button, originalText);
            }
        }

        // Send document message
        async function sendDocumentMessage() {
            const button = event.target;
            const originalText = 'Kirim Dokumen';
            
            try {
                showLoading(button);
                
                const phone = getPhoneNumber();
                const fileInput = document.getElementById('document-file');
                const caption = document.getElementById('document-caption').value.trim();
                
                if (!fileInput.files[0]) {
                    throw new Error('File dokumen harus dipilih');
                }

                const formData = new FormData();
                formData.append('phone', phone);
                formData.append('file', fileInput.files[0]);
                if (caption) formData.append('caption', caption);

                const response = await fetch(`${FRONTEND_API_BASE}/api/send-document`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    showResponse(result);
                    fileInput.value = '';
                    document.getElementById('document-caption').value = '';
                } else {
                    showResponse(result, true);
                }
                
            } catch (error) {
                showResponse({ error: error.message }, true);
            } finally {
                hideLoading(button, originalText);
            }
        }

        // Send audio message
        async function sendAudioMessage() {
            const button = event.target;
            const originalText = 'Kirim Audio';
            
            try {
                showLoading(button);
                
                const phone = getPhoneNumber();
                const fileInput = document.getElementById('audio-file');
                
                if (!fileInput.files[0]) {
                    throw new Error('File audio harus dipilih');
                }

                const formData = new FormData();
                formData.append('phone', phone);
                formData.append('file', fileInput.files[0]);

                const response = await fetch(`${FRONTEND_API_BASE}/api/send-audio`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    showResponse(result);
                    fileInput.value = '';
                } else {
                    showResponse(result, true);
                }
                
            } catch (error) {
                showResponse({ error: error.message }, true);
            } finally {
                hideLoading(button, originalText);
            }
        }

        // Send video message
        async function sendVideoMessage() {
            const button = event.target;
            const originalText = 'Kirim Video';
            
            try {
                showLoading(button);
                
                const phone = getPhoneNumber();
                const fileInput = document.getElementById('video-file');
                const caption = document.getElementById('video-caption').value.trim();
                
                if (!fileInput.files[0]) {
                    throw new Error('File video harus dipilih');
                }

                const formData = new FormData();
                formData.append('phone', phone);
                formData.append('file', fileInput.files[0]);
                if (caption) formData.append('caption', caption);

                const response = await fetch(`${FRONTEND_API_BASE}/api/send-video`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    showResponse(result);
                    fileInput.value = '';
                    document.getElementById('video-caption').value = '';
                } else {
                    showResponse(result, true);
                }
                
            } catch (error) {
                showResponse({ error: error.message }, true);
            } finally {
                hideLoading(button, originalText);
            }
        }

        // Send sticker message
        async function sendStickerMessage() {
            const button = event.target;
            const originalText = 'Kirim Sticker';
            
            try {
                showLoading(button);
                
                const phone = getPhoneNumber();
                const fileInput = document.getElementById('sticker-file');
                
                if (!fileInput.files[0]) {
                    throw new Error('File sticker harus dipilih');
                }

                // Check file extension
                const fileName = fileInput.files[0].name.toLowerCase();
                if (!fileName.endsWith('.webp')) {
                    throw new Error('Sticker harus dalam format WebP');
                }

                const formData = new FormData();
                formData.append('phone', phone);
                formData.append('file', fileInput.files[0]);

                const response = await fetch(`${FRONTEND_API_BASE}/api/send-sticker`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    showResponse(result);
                    fileInput.value = '';
                } else {
                    showResponse(result, true);
                }
                
            } catch (error) {
                showResponse({ error: error.message }, true);
            } finally {
                hideLoading(button, originalText);
            }
        }

        // Check API status on page load
        async function checkAPIStatus() {
            try {
                const response = await fetch(`${FRONTEND_API_BASE}/api/status`);
                const result = await response.json();
                
                const statusIndicator = document.getElementById('status-indicator');
                const statusDot = statusIndicator.querySelector('div');
                const statusText = statusIndicator.querySelector('span');
                const alertDiv = document.getElementById('api-status-alert');
                const alertMessage = document.getElementById('api-status-message');
                
                if (result.api_available && result.bot_connected) {
                    // API available and bot connected
                    statusDot.className = 'w-3 h-3 bg-green-400 rounded-full pulse-green mr-2';
                    statusText.textContent = 'Online';
                    statusText.className = 'text-green-100 text-sm';
                    alertDiv.classList.add('hidden');
                } else if (result.api_available && !result.bot_connected) {
                    // API available but bot not connected
                    statusDot.className = 'w-3 h-3 bg-yellow-400 rounded-full mr-2';
                    statusText.textContent = 'API OK, Bot Offline';
                    statusText.className = 'text-yellow-100 text-sm';
                    alertDiv.classList.remove('hidden');
                    alertDiv.className = 'bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4';
                    alertMessage.textContent = 'WhatsApp API server tersedia, tetapi bot WhatsApp belum terhubung.';
                } else {
                    // API not available
                    statusDot.className = 'w-3 h-3 bg-red-400 rounded-full pulse-red mr-2';
                    statusText.textContent = 'API Offline';
                    statusText.className = 'text-red-100 text-sm';
                    alertDiv.classList.remove('hidden');
                    alertDiv.className = 'bg-red-100 border-l-4 border-red-500 text-red-700 p-4';
                    alertMessage.textContent = 'Tidak dapat terhubung ke WhatsApp API server. Periksa koneksi dan konfigurasi.';
                }
                
                // Update status info
                if (result.last_check) {
                    alertMessage.textContent += ` (Last check: ${result.last_check})`;
                }
                
            } catch (error) {
                console.error('Failed to check API status:', error);
                const statusIndicator = document.getElementById('status-indicator');
                const statusDot = statusIndicator.querySelector('div');
                const statusText = statusIndicator.querySelector('span');
                const alertDiv = document.getElementById('api-status-alert');
                const alertMessage = document.getElementById('api-status-message');
                
                statusDot.className = 'w-3 h-3 bg-gray-400 rounded-full mr-2';
                statusText.textContent = 'Unknown';
                statusText.className = 'text-gray-200 text-sm';
                alertDiv.classList.remove('hidden');
                alertDiv.className = 'bg-red-100 border-l-4 border-red-500 text-red-700 p-4';
                alertMessage.textContent = 'Error checking API status: ' + error.message;
            }
        }

        // File size validation
        function validateFileSize(input, maxSizeMB) {
            const file = input.files[0];
            if (file && file.size > maxSizeMB * 1024 * 1024) {
                alert(`File terlalu besar. Maksimum ${maxSizeMB}MB`);
                input.value = '';
                return false;
            }
            return true;
        }

        // Add file size validation to file inputs
        document.getElementById('image-file').addEventListener('change', function() {
            validateFileSize(this, 16);
        });

        document.getElementById('document-file').addEventListener('change', function() {
            validateFileSize(this, 32);
        });

        document.getElementById('audio-file').addEventListener('change', function() {
            validateFileSize(this, 16);
            
            // Additional audio file validation
            const file = this.files[0];
            if (file) {
                const allowedTypes = ['audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a', 'audio/aac', 'audio/flac', 'audio/mpeg'];
                if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().match(/\.(mp3|wav|ogg|m4a|aac|flac)$/)) {
                    alert('Format audio tidak didukung. Gunakan: MP3, WAV, OGG, M4A, AAC, FLAC');
                    this.value = '';
                }
            }
        });

        document.getElementById('video-file').addEventListener('change', function() {
            validateFileSize(this, 64);
            
            // Additional video file validation
            const file = this.files[0];
            if (file) {
                const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm', 'video/3gp'];
                if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().match(/\.(mp4|avi|mov|mkv|webm|3gp|flv)$/)) {
                    alert('Format video tidak didukung. Gunakan: MP4, AVI, MOV, MKV, WebM, 3GP');
                    this.value = '';
                }
            }
        });

        document.getElementById('sticker-file').addEventListener('change', function() {
            validateFileSize(this, 1);
            
            // Additional sticker file validation
            const file = this.files[0];
            if (file) {
                if (!file.name.toLowerCase().endsWith('.webp')) {
                    alert('Sticker harus dalam format WebP');
                    this.value = '';
                    return;
                }
                
                // Check image dimensions (optional)
                const img = new Image();
                img.onload = function() {
                    if (this.width > 512 || this.height > 512) {
                        if (confirm('Sticker lebih besar dari 512x512px. Lanjutkan mengirim?')) {
                            return;
                        } else {
                            document.getElementById('sticker-file').value = '';
                        }
                    }
                };
                img.src = URL.createObjectURL(file);
            }
        });

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            checkAPIStatus();
            
            // Check status every 30 seconds
            setInterval(checkAPIStatus, 30000);
        });

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    </script>
</body>
</html>'''

@app.route('/')
def index():
    """Render the main website"""
    # Check API status for display
    check_whatsapp_api_status()
    
    return render_template_string(HTML_TEMPLATE, 
                                api_url=WHATSAPP_API_BASE_URL)

@app.route('/api')
def api_info():
    """API information endpoint - proxy to external API"""
    try:
        response = send_to_whatsapp_api('/api', 'GET')
        return response.json(), response.status_code
    except Exception as e:
        return jsonify({
            "service": "WhatsApp API Frontend",
            "status": "error",
            "message": f"Cannot connect to WhatsApp API: {str(e)}",
            "external_api": WHATSAPP_API_BASE_URL,
            "version": "2.0.0-frontend"
        }), 503

@app.route('/api/status')
def bot_status():
    """Get bot status from external API"""
    check_whatsapp_api_status()
    
    try:
        response = send_to_whatsapp_api('/api/status', 'GET')
        external_data = response.json()
        
        # Combine external data with local status
        return jsonify({
            **external_data,
            "api_available": LOCAL_BOT_STATUS['api_available'],
            "last_check": str(LOCAL_BOT_STATUS['last_check']),
            "frontend_version": "2.0.0-frontend",
            "external_api_url": WHATSAPP_API_BASE_URL
        })
        
    except Exception as e:
        return jsonify({
            "bot_connected": False,
            "api_available": False,
            "error": str(e),
            "external_api_url": WHATSAPP_API_BASE_URL,
            "last_check": str(LOCAL_BOT_STATUS['last_check']),
            "message": "Cannot connect to external WhatsApp API"
        }), 503

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Send text message via external API"""
    try:
        # Check if external API is available
        if not LOCAL_BOT_STATUS['api_available']:
            return jsonify({
                "status": "error", 
                "message": f"WhatsApp API not available at {WHATSAPP_API_BASE_URL}"
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON data"}), 400
        
        phone = data.get('phone')
        message = data.get('message')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        if not message:
            return jsonify({"status": "error", "message": "Message text required"}), 400
        
        # Forward to external WhatsApp API
        response = send_to_whatsapp_api('/api/send-message', 'POST', data)
        
        return response.json(), response.status_code
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to send message: {str(e)}"
        }), 500

@app.route('/api/send-image', methods=['POST'])
def send_image():
    """Send image via external API"""
    try:
        # Check if external API is available
        if not LOCAL_BOT_STATUS['api_available']:
            return jsonify({
                "status": "error", 
                "message": f"WhatsApp API not available at {WHATSAPP_API_BASE_URL}"
            }), 503
        
        phone = request.form.get('phone')
        caption = request.form.get('caption', '')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file locally first
        filename, file_size = validate_file(file, 'images')
        
        # Prepare data for external API
        files = {'file': (filename, file, file.content_type)}
        data = {'phone': phone}
        if caption:
            data['caption'] = caption
        
        # Forward to external WhatsApp API
        response = send_to_whatsapp_api('/api/send-image', 'POST', data, files)
        
        return response.json(), response.status_code
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to send image: {str(e)}"
        }), 500

@app.route('/api/send-document', methods=['POST'])
def send_document():
    """Send document via external API"""
    try:
        # Check if external API is available
        if not LOCAL_BOT_STATUS['api_available']:
            return jsonify({
                "status": "error", 
                "message": f"WhatsApp API not available at {WHATSAPP_API_BASE_URL}"
            }), 503
        
        phone = request.form.get('phone')
        caption = request.form.get('caption', '')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file locally first
        filename, file_size = validate_file(file, 'documents')
        
        # Prepare data for external API
        files = {'file': (filename, file, file.content_type)}
        data = {'phone': phone}
        if caption:
            data['caption'] = caption
        
        # Forward to external WhatsApp API
        response = send_to_whatsapp_api('/api/send-document', 'POST', data, files)
        
        return response.json(), response.status_code
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to send document: {str(e)}"
        }), 500

@app.route('/api/send-audio', methods=['POST'])
def send_audio():
    """Send audio via external API"""
    try:
        # Check if external API is available
        if not LOCAL_BOT_STATUS['api_available']:
            return jsonify({
                "status": "error", 
                "message": f"WhatsApp API not available at {WHATSAPP_API_BASE_URL}"
            }), 503
        
        phone = request.form.get('phone')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file locally first
        filename, file_size = validate_file(file, 'audio')
        
        # Prepare data for external API
        files = {'file': (filename, file, file.content_type)}
        data = {'phone': phone}
        
        # Forward to external WhatsApp API
        response = send_to_whatsapp_api('/api/send-audio', 'POST', data, files)
        
        return response.json(), response.status_code
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to send audio: {str(e)}"
        }), 500

@app.route('/api/send-video', methods=['POST'])
def send_video():
    """Send video via external API"""
    try:
        # Check if external API is available
        if not LOCAL_BOT_STATUS['api_available']:
            return jsonify({
                "status": "error", 
                "message": f"WhatsApp API not available at {WHATSAPP_API_BASE_URL}"
            }), 503
        
        phone = request.form.get('phone')
        caption = request.form.get('caption', '')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file locally first
        filename, file_size = validate_file(file, 'video')
        
        # Prepare data for external API
        files = {'file': (filename, file, file.content_type)}
        data = {'phone': phone}
        if caption:
            data['caption'] = caption
        
        # Forward to external WhatsApp API
        response = send_to_whatsapp_api('/api/send-video', 'POST', data, files)
        
        return response.json(), response.status_code
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to send video: {str(e)}"
        }), 500

@app.route('/api/send-sticker', methods=['POST'])
def send_sticker():
    """Send sticker via external API"""
    try:
        # Check if external API is available
        if not LOCAL_BOT_STATUS['api_available']:
            return jsonify({
                "status": "error", 
                "message": f"WhatsApp API not available at {WHATSAPP_API_BASE_URL}"
            }), 503
        
        phone = request.form.get('phone')
        file = request.files.get('file')
        
        if not phone:
            return jsonify({"status": "error", "message": "Phone number required"}), 400
        
        # Validate file locally first
        filename, file_size = validate_file(file, 'stickers')
        
        # Prepare data for external API
        files = {'file': (filename, file, file.content_type)}
        data = {'phone': phone}
        
        # Forward to external WhatsApp API
        response = send_to_whatsapp_api('/api/send-sticker', 'POST', data, files)
        
        return response.json(), response.status_code
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to send sticker: {str(e)}"
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    check_whatsapp_api_status()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': str(datetime.now()),
        'version': '2.0.0-frontend',
        'external_api': {
            'url': WHATSAPP_API_BASE_URL,
            'available': LOCAL_BOT_STATUS['api_available'],
            'bot_connected': LOCAL_BOT_STATUS['connected'],
            'last_check': str(LOCAL_BOT_STATUS['last_check'])
        }
    })

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
    print("🚀 WhatsApp API Frontend Starting...")
    print("=" * 60)
    print(f"📱 Frontend Server: http://localhost:8000")
    print(f"🔗 WhatsApp API: {WHATSAPP_API_BASE_URL}")
    print("=" * 60)
    print("📋 Configuration:")
    print(f"   • API Host: {WHATSAPP_API_CONFIG['host']}")
    print(f"   • API Port: {WHATSAPP_API_CONFIG['port']}")
    print(f"   • Use HTTPS: {WHATSAPP_API_CONFIG['use_https']}")
    print(f"   • API Key: {'Set' if WHATSAPP_API_CONFIG['api_key'] else 'Not Set'}")
    print(f"   • Timeout: {WHATSAPP_API_CONFIG['timeout']}s")
    print("=" * 60)
    print("✅ Frontend running on http://localhost:8000")
    print("🔍 Check connection status at startup...")
    
    # Initial API check
    check_whatsapp_api_status()
    print(f"🔗 WhatsApp API Status: {'✅ Available' if LOCAL_BOT_STATUS['api_available'] else '❌ Not Available'}")
    
    app.run(debug=True, host='0.0.0.0', port=8000)

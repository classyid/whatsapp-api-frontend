# 🚀 WhatsApp API Frontend

<div align="center">
    
![WhatsApp API Frontend](https://img.shields.io/badge/WhatsApp-API%20Frontend-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-3.0+-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

**Complete web interface for WhatsApp API with separated server architecture**

</div>

---

## 📋 Overview

WhatsApp API Frontend adalah web interface modern yang memungkinkan Anda mengirim berbagai jenis pesan WhatsApp melalui API server yang terpisah. Built dengan Flask dan Tailwind CSS, aplikasi ini menyediakan antarmuka yang user-friendly untuk mengelola komunikasi WhatsApp bisnis.

### 🏗️ Architecture

```
┌─────────────────────┐    HTTP Request    ┌─────────────────────┐
│   Frontend Server   │ =================> │  WhatsApp API Server│
│   localhost:8000    │                    │    xx.xx.xx.xx:5000 │
│                     │                    │                     │
│ • Web Interface     │                    │ • WhatsApp Bot      │
│ • File Validation   │                    │ • Message Sending   │
│ • API Proxy         │                    │ • Media Processing  │
└─────────────────────┘                    └─────────────────────┘
```

## 🎯 Features

### ✨ Core Features
- 📱 **6 Message Types**: Text, Image, Document, Audio, Video, Sticker
- 🌐 **Web Interface**: Modern, responsive design with Tailwind CSS
- 🔄 **Real-time Status**: Live connection monitoring with WhatsApp API
- 📁 **File Validation**: Client-side validation for size and format
- ⚡ **Fast Performance**: Optimized for speed and reliability
- 🔧 **Easy Configuration**: Simple .env file configuration

### 📊 Supported Media Formats

| Media Type | Formats | Max Size | Caption Support |
|------------|---------|----------|-----------------|
| **Images** | JPG, PNG, GIF, WebP | 16MB | ✅ Yes |
| **Documents** | PDF, DOC, XLS, PPT, TXT, ZIP, RAR | 32MB | ✅ Yes |
| **Audio** | MP3, WAV, OGG, M4A, AAC, FLAC | 16MB | ❌ No |
| **Video** | MP4, AVI, MOV, MKV, WebM, 3GP | 64MB | ✅ Yes |
| **Stickers** | WebP | 1MB | ❌ No |

### 🛡️ Production Ready
- 🔒 **Security**: Environment variables, input validation
- 📈 **Scalability**: Separated architecture for horizontal scaling
- 🐳 **Docker Support**: Ready for containerization
- 🔍 **Monitoring**: Health checks and status endpoints
- 📝 **Logging**: Comprehensive error tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ 
- WhatsApp API Server running on separate machine

### 1-Minute Setup

```bash
# Clone repository
git clone https://github.com/classyid/whatsapp-api-frontend.git
cd whatsapp-api-frontend

# Run automatic setup
python setup_frontend.py

# Test connection to WhatsApp API
python test_connection.py

# Start frontend
python app.py
```

**Access your application at**: http://localhost:8000

## 🛠️ Installation

### Method 1: Automatic Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/classyid/whatsapp-api-frontend.git
cd whatsapp-api-frontend

# 2. Run setup script
python setup_frontend.py
# Script will ask for WhatsApp API server IP

# 3. Test connection
python test_connection.py

# 4. Start application
python app.py
```

### Method 2: Manual Setup

```bash
# 1. Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env file with your WhatsApp API server details

# 4. Create directories
mkdir -p uploads logs static/{css,js,images}

# 5. Start application
python app.py
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# WhatsApp API Server Configuration
WHATSAPP_API_HOST=10.122.25.221
WHATSAPP_API_PORT=5000
WHATSAPP_API_HTTPS=false
WHATSAPP_API_TIMEOUT=30

# Optional: API Key for authentication
# WHATSAPP_API_KEY=your-api-key-here

# Frontend Server Configuration
FLASK_ENV=development
FLASK_DEBUG=true
HOST=0.0.0.0
PORT=8000

# File Upload Configuration
MAX_CONTENT_LENGTH=67108864  # 64MB
UPLOAD_FOLDER=uploads

# Security
SECRET_KEY=your-secret-key-here
```

### Quick Configuration Change

Update WhatsApp API server in `app.py` line 22-30:

```python
WHATSAPP_API_CONFIG = {
    'host': os.getenv('WHATSAPP_API_HOST', 'localhost'),  # ← Change IP here
    'port': os.getenv('WHATSAPP_API_PORT', '5000'),           # ← Change port here
    'use_https': os.getenv('WHATSAPP_API_HTTPS', 'false').lower() == 'true',
    'api_key': os.getenv('WHATSAPP_API_KEY', ''),
    'timeout': int(os.getenv('WHATSAPP_API_TIMEOUT', '30'))
}
```

## 📖 Documentation

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/api/status` | GET | Get connection status |
| `/api/send-message` | POST | Send text message |
| `/api/send-image` | POST | Send image with caption |
| `/api/send-document` | POST | Send document |
| `/api/send-audio` | POST | Send audio file |
| `/api/send-video` | POST | Send video with caption |
| `/api/send-sticker` | POST | Send WebP sticker |
| `/health` | GET | Health check endpoint |

### Example Usage

#### Send Text Message
```bash
curl -X POST http://localhost:8000/api/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "6281234567890",
    "message": "Hello from WhatsApp API!"
  }'
```

#### Send Image
```bash
curl -X POST http://localhost:8000/api/send-image \
  -F "phone=6281234567890" \
  -F "caption=Beautiful sunset!" \
  -F "file=@image.jpg"
```

### Testing Connection

```bash
# Test WhatsApp API connectivity
python test_connection.py

# Expected output:
# 🧪 Testing WhatsApp API Connection
# ✅ API Info endpoint: OK
# ✅ API Status endpoint: OK
```

## 🐳 Docker Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  whatsapp-frontend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WHATSAPP_API_HOST=localhost
      - WHATSAPP_API_PORT=5000
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped
```

### Run with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🔧 Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run production server
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 app:app
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        client_max_body_size 64M;
        proxy_read_timeout 300s;
    }
}
```

## 🚨 Troubleshooting

### Common Issues

#### Connection Failed
```bash
❌ Error: "Cannot connect to WhatsApp API"

Solutions:
✅ Check WhatsApp API server is running
✅ Verify IP address in .env file
✅ Test: curl http://localhost:5000/api/status
✅ Check firewall settings
```

#### Port Already in Use
```bash
❌ Error: "Port 8000 already in use"

Solutions:
✅ Change port in .env: PORT=8001
✅ Kill existing process: lsof -ti:8000 | xargs kill -9
```

#### File Upload Issues
```bash
❌ Error: "File too large"

Solutions:
✅ Check file size limits
✅ Verify MAX_CONTENT_LENGTH in .env
✅ Ensure WhatsApp API server accepts large files
```

### Debug Mode

```bash
# Enable debug mode
export FLASK_DEBUG=1
python app.py

# Or edit .env
FLASK_DEBUG=true
```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-16 10:30:00",
  "version": "2.0.0-frontend",
  "external_api": {
    "url": "http://10.122.25.221:5000",
    "available": true,
    "bot_connected": true
  }
}
```

### Status Indicators

- 🟢 **Online**: API available & bot connected
- 🟡 **API OK, Bot Offline**: API reachable but bot disconnected
- 🔴 **API Offline**: Cannot reach WhatsApp API server

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/classyid/whatsapp-api-frontend.git

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run linting
flake8 app.py
black app.py
```

## 📝 Changelog

### v2.0.0 (Latest)
- ✅ Complete media support (6 message types)
- ✅ Separated server architecture
- ✅ Real-time connection monitoring
- ✅ Production-ready features
- ✅ Docker support

### v1.0.0
- ✅ Basic text messaging
- ✅ Image support
- ✅ Simple web interface

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework
- [Font Awesome](https://fontawesome.com/) - Icons
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp) - WhatsApp integration

## 📞 Support

- 📖 **Documentation**: Check this README and docs/ folder
- 🐛 **Bug Reports**: [Create an issue](https://github.com/yourusername/whatsapp-api-frontend/issues)
- 💡 **Feature Requests**: [Create an issue](https://github.com/yourusername/whatsapp-api-frontend/issues)
- 💬 **Discussions**: [Join the discussion](https://github.com/yourusername/whatsapp-api-frontend/discussions)

## 🌟 Star History

If this project helps you, please consider giving it a ⭐!

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/whatsapp-api-frontend&type=Date)](https://star-history.com/#yourusername/whatsapp-api-frontend&Date)

---

<div align="center">

**Made with ❤️ for developers by developers**

[🚀 Get Started](#-quick-start) • [📖 Documentation](#-documentation) • [🤝 Contributing](#-contributing)

</div>

# AI Voice Translator Pro 🎙️🌍

Real-time multilingual voice translation application with instant transcription, neural translation, and natural speech synthesis. Built for speed, accuracy, and seamless user experience.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![React](https://img.shields.io/badge/react-19.0-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)

## ✨ Features

- **⚡ Lightning Fast**: 0.3s partial transcription, ~3s end-to-end pipeline
- **🌍 50+ Languages**: Comprehensive support including Indian languages (Telugu, Tamil, Hindi, etc.)
- **🎙️ Real-Time Processing**: Live transcription with WebSocket streaming
- **🔊 Natural Voice Output**: Browser-native TTS with optimized voice selection
- **🧠 State-of-the-Art AI**: Whisper (faster-whisper), NLLB-200, Silero VAD
- **💾 History Management**: SQLite-based translation history with export capabilities
- **⚙️ Configurable**: Adjustable models, VAD thresholds, and performance settings
- **🎯 Production Ready**: Rate limiting, logging, error handling, and middleware

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- 8GB RAM minimum (16GB recommended)
- Windows, Linux, or macOS

### Installation

**1. Clone the repository**
```bash
git clone <repository-url>
cd ai-voice-translator-pro
```

**2. Backend Setup**
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

**3. Frontend Setup**
```bash
cd frontend
npm install
```

### Running the Application

**Start Backend (Terminal 1)**
```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Frontend (Terminal 2)**
```bash
cd frontend
npm run dev
```

**Access the Application**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🏗️ Architecture

### Project Structure
```
ai-voice-translator-pro/
├── backend/
│   ├── api/              # REST API endpoints
│   ├── config/           # Configuration management
│   ├── database/         # SQLite models & connection
│   ├── middleware/       # Logging & rate limiting
│   ├── models/           # Downloaded AI models cache
│   ├── services/         # Business logic layer
│   ├── speech/           # Whisper & VAD processing
│   ├── translation/      # NLLB & Marian engines
│   ├── tts/              # Text-to-speech engines
│   ├── utils/            # Helper functions
│   ├── websocket/        # WebSocket handlers
│   ├── main.py           # FastAPI application
│   └── requirements.txt  # Python dependencies
└── frontend/
    ├── public/           # Static assets
    ├── src/
    │   ├── components/   # React components
    │   ├── hooks/        # Custom React hooks
    │   ├── services/     # API & WebSocket clients
    │   ├── store/        # State management (Zustand)
    │   ├── types/        # TypeScript definitions
    │   └── App.tsx       # Main application
    └── package.json      # Node dependencies
```

### Technology Stack

**Backend**
- **Framework**: FastAPI (async Python web framework)
- **Speech Recognition**: faster-whisper (optimized Whisper implementation)
- **Translation**: NLLB-200 (Meta's No Language Left Behind), Marian MT
- **VAD**: Silero Voice Activity Detection
- **Database**: SQLite with SQLAlchemy ORM
- **Streaming**: WebSocket for real-time communication

**Frontend**
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS v4
- **State Management**: Zustand
- **Animation**: Framer Motion
- **Audio**: Web Audio API, MediaRecorder, SpeechSynthesis

## 📋 Core Components

### Backend Services

**Speech Service** (`services/speech_service.py`)
- Audio preprocessing and VAD
- Whisper model integration
- Partial and final transcription handling

**Translation Service** (`services/translation_service.py`)
- NLLB-200 neural translation
- Marian model fallback
- Translation caching (LRU)
- Language detection

**TTS Service** (`services/tts_service.py`)
- Piper TTS integration
- Coqui TTS support
- Audio format conversion

**History Service** (`services/history_service.py`)
- Translation history persistence
- Search and filtering
- Export functionality (JSON, CSV)

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/speech/transcribe` | POST | Transcribe audio |
| `/api/translation/translate` | POST | Translate text |
| `/api/tts/synthesize` | POST | Generate speech |
| `/api/history` | GET/POST | Manage history |
| `/api/export` | POST | Export translations |
| `/api/settings` | GET/PUT | App settings |
| `/ws/speech` | WS | Real-time speech streaming |

## ⚙️ Configuration

### Backend Configuration

Create/edit `backend/.env`:

```env
# Model Settings
WHISPER_MODEL=small                    # tiny, base, small, medium, large
WHISPER_COMPUTE_TYPE=int8              # int8, float16, float32
WHISPER_BEAM_SIZE=1                    # 1 for greedy (fastest)
TRANSLATION_MODEL=nllb-200-distilled-600M

# Audio Settings
SAMPLE_RATE=16000
CHUNK_SIZE=1024
VAD_THRESHOLD=0.5                      # 0.0-1.0
VAD_MIN_SPEECH_DURATION_MS=250
VAD_MIN_SILENCE_DURATION_MS=1000

# Performance
MAX_WORKERS=3                          # Parallel processing threads
CACHE_SIZE=256                         # Translation cache entries
MAX_AUDIO_LENGTH_SECONDS=60

# Database
DATABASE_URL=sqlite:///./data/translator.db

# Server
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=INFO
```

### Frontend Configuration

Edit `frontend/src/config/`:
- API endpoint URLs
- WebSocket connection settings
- Audio recording parameters
- UI preferences

## 🌐 Supported Languages

**Major Languages**: English, Spanish, French, German, Italian, Portuguese, Russian, Chinese (Simplified/Traditional), Japanese, Korean, Arabic

**Indian Languages**: Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu

**European Languages**: Dutch, Polish, Swedish, Norwegian, Danish, Finnish, Czech, Slovak, Romanian, Hungarian, Ukrainian, Bulgarian, Croatian, Serbian, Greek

**Other Languages**: Turkish, Hebrew, Persian, Thai, Vietnamese, Indonesian, Malay, Swahili, Afrikaans, Catalan, Lithuanian, Latvian, Estonian

**Total**: 50+ languages supported

## 🎯 Performance Optimizations

### Speed Enhancements
- **Greedy Decoding**: beam_size=1 (3-5x faster than beam search)
- **INT8 Quantization**: Reduced model size, faster inference
- **Partial Processing**: Process only recent audio (1.5s) for live updates
- **Parallel Workers**: 3 concurrent threads for transcription/translation
- **LRU Caching**: 256-entry translation cache with MD5 keys
- **Token Limiting**: max_new_tokens=200 for faster generation

### Quality Improvements
- **VAD Gating**: Energy threshold + Silero VAD filtering
- **Hallucination Detection**: Filter common Whisper artifacts
- **Smart Chunking**: Split long text (>400 chars) intelligently
- **Post-processing**: Punctuation and capitalization fixes

## 📊 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores (Intel i7/AMD Ryzen 7) |
| **RAM** | 8GB | 16GB+ |
| **Storage** | 5GB free | 10GB+ SSD |
| **GPU** | None (CPU-only) | NVIDIA GTX 1060+ (CUDA 11.8+) |
| **Network** | N/A | Low latency for API calls |
| **OS** | Windows 10, Ubuntu 20.04, macOS 11+ | Latest stable versions |

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm run test
```

## 📦 Building for Production

**Frontend Build**
```bash
cd frontend
npm run build
# Output in frontend/dist/
```

**Backend Deployment**
```bash
cd backend
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🐛 Troubleshooting

**Models not downloading**
- Check internet connection
- Verify HuggingFace access (some models require authentication)
- Clear cache in `backend/models/` and retry

**Audio not recording**
- Grant microphone permissions in browser
- Check browser compatibility (Chrome/Edge recommended)
- Verify audio input device in system settings

**Translation errors**
- Check language pair support in NLLB-200
- Verify backend logs in `backend/logs/app.log`
- Clear translation cache

**Performance issues**
- Reduce WHISPER_MODEL to "tiny" or "base"
- Decrease MAX_WORKERS
- Enable GPU if available
- Close other heavy applications

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Development Guidelines**
- Follow PEP 8 for Python code
- Use ESLint/Prettier for TypeScript
- Add tests for new features
- Update documentation

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition models
- [Meta NLLB](https://github.com/facebookresearch/fairseq/tree/nllb) - Neural translation
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper implementation
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library

## 📧 Support

For bugs, features, or questions:
- Open an [Issue](../../issues)
- Check [Discussions](../../discussions)
- Review [Documentation](../../wiki)

---

**Built with ❤️ for seamless global communication**

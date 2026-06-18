# Multilingual Voice Translation Engine

Enterprise-grade voice translator with instant transcription (0.3s), blazing-fast translation, and natural speech output. Supports 50+ languages with specialized Telugu optimization. Built with Whisper small, NLLB-200, React, FastAPI. Real-time streaming.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![React](https://img.shields.io/badge/react-19.0-blue.svg)

## ✨ Key Features

- **⚡ Ultra-Fast Performance**: 0.3s partial transcription, ~3s end-to-end processing
- **🌍 50+ Languages**: Including Telugu, Tamil, Kannada, Malayalam with native TTS
- **🎙️ Real-Time Streaming**: Text appears as you speak with instant updates
- **🔊 Natural Speech Output**: Optimized Telugu voice (0.65 rate), quality-based voice selection
- **🧠 Advanced AI Models**: Whisper small, NLLB-200 with greedy decoding
- **💪 Production-Ready**: Parallel processing, caching, optimized for CPU

## 🚀 Performance Metrics

| Metric | Time |
|--------|------|
| Partial Transcription | 0.3s |
| Silence Detection | 1.0s |
| Final Transcription | 0.5-1s |
| Translation | 0.3-0.8s |
| TTS Response | 0.3s |
| **Total (Speaking → Audio)** | **~3 seconds** |

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI + Python 3.10+
- **Speech Recognition**: Whisper small (faster-whisper, int8, beam_size=1)
- **Translation**: NLLB-200 distilled 600M (greedy decoding, max_tokens=200)
- **VAD**: Silero VAD with energy gating
- **Streaming**: Native WebSocket with 3 parallel workers

### Frontend
- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4
- **State**: Zustand
- **Animation**: Framer Motion
- **TTS**: Browser SpeechSynthesis API

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+
- 8GB RAM minimum
- Optional: NVIDIA GPU with CUDA 11.8+ (for faster processing)

## 🔧 Installation

### Method 1: Automated Install (Windows)

```powershell
# Run as Administrator
.\install.ps1
```

### Method 2: Manual Install

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### Method 3: Docker

```bash
docker-compose up -d --build
```

## 🎯 Running the Application

**Backend:**
```bash
cd backend
venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**Access**: http://localhost:5173

## 🌐 Supported Languages (50+)

English, Spanish, French, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Arabic, Hindi, **Telugu**, **Tamil**, **Kannada**, **Malayalam**, Marathi, Bengali, Gujarati, Punjabi, Urdu, Turkish, Dutch, Polish, Swedish, Norwegian, Danish, Finnish, Czech, Slovak, Romanian, Hungarian, Ukrainian, Bulgarian, Croatian, Serbian, Greek, Hebrew, Persian, Thai, Vietnamese, Indonesian, Malay, Swahili, Afrikaans, Catalan, Lithuanian, Latvian, Estonian

## ⚙️ Optimizations Applied

### Speed Optimizations
- **Greedy Decoding**: beam_size=1 for Whisper & NLLB (3-5x faster)
- **Partial Processing**: Only last 1.5s of audio processed for real-time updates
- **Parallel Workers**: 3 ThreadPoolExecutor workers for concurrent processing
- **Reduced Tokens**: max_new_tokens=200 (48% reduction)
- **CPU Threading**: MKL/OMP optimized with 2 threads
- **Translation Cache**: 256-entry LRU cache with MD5 keys

### Quality Optimizations
- **VAD-Gated Buffering**: Energy gate (0.002) + Silero VAD filtering
- **Hallucination Filter**: Common phrase detection and repetition checking
- **Sentence Chunking**: Smart splitting for utterances >400 chars
- **NLLB Cleaning**: Automatic punctuation and capitalization fixes

## 🔧 Configuration

Edit `backend/.env`:

```env
# Model Settings
WHISPER_MODEL=small
WHISPER_BEAM_SIZE=5
TRANSLATION_MODEL=nllb-200

# Audio Settings
SAMPLE_RATE=16000
VAD_THRESHOLD=0.5

# Performance
WORKERS=3
```

## 📊 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB+ |
| CPU | 4 cores | 8+ cores |
| Storage | 5GB | 10GB+ |
| GPU | None (CPU-only) | NVIDIA GTX 1060+ |

## 🎨 Features in Detail

### Real-Time Transcription
- Partial transcripts every 0.3s while speaking
- Non-blocking fire-and-forget processing
- Smooth UI updates with fade animations

### Telugu Voice Optimization
- Native voice prioritization (Microsoft Heera)
- Slower speech rate (0.65) for clarity
- Longer sentence pauses (300ms)
- Romanization support for pronunciation hints

### Translation Pipeline
- Cache-first lookup (MD5-based keys)
- Fallback to Marian models when available
- Language pair blocklist for unsupported combinations
- Automatic chunking for long sentences

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **OpenAI Whisper** - Speech recognition
- **Meta NLLB-200** - Neural translation
- **Silero VAD** - Voice activity detection
- **FastAPI** - Backend framework
- **React Team** - Frontend framework

## 📧 Contact

For issues and questions, please open a GitHub issue.

---

**Built with ❤️ for real-time multilingual communication**

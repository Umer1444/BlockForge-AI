<div align="center">

<h1>⛏ BlockForge AI</h1>

<p><strong>GPU-Accelerated AI Video Watermark Removal & Enhancement Studio</strong></p>

<p>
  <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.11-3b82f6?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/CUDA-12.2-76B900?style=for-the-badge&logo=nvidia&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
</p>

<p>
  <img src="https://img.shields.io/github/stars/yourusername/blockforge-ai?style=social" />
  <img src="https://img.shields.io/github/forks/yourusername/blockforge-ai?style=social" />
</p>

</div>

---

## 📖 Overview

**BlockForge AI** is a production-grade video processing studio that removes watermarks, logos, text overlays, and unwanted objects from videos using state-of-the-art AI models — all while preserving pristine video quality.

Built on a fully asynchronous, GPU-accelerated pipeline with real-time progress streaming via WebSockets, BlockForge AI is designed to handle large video files efficiently in both local and containerised environments.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **SAM Segmentation** | Click-to-select AI mask generation using Meta's Segment Anything Model |
| 🎨 **LaMa Inpainting** | GPU-accelerated deep inpainting with global texture reconstruction |
| 🌊 **Temporal Smoothing** | Optical flow consistency for flicker-free frame sequences |
| ✨ **Real-ESRGAN** | Optional upscaling & quality enhancement (4×) |
| 🧠 **Multi-modal Detection** | PaddleOCR + YOLOv8 for automated watermark detection |
| 🎮 **Pixel-Art Studio UI** | Custom Minecraft-themed interface built with Next.js |
| ⚡ **Real-time Updates** | WebSocket-powered live processing progress |
| 🐳 **Docker Ready** | Single-command deployment with GPU passthrough |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Browser                       │
│              Next.js 16 + React 19 + Tailwind 4             │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTP / WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                           │
│           REST API  ·  WebSocket Hub  ·  Job Manager        │
└──────────┬─────────────────────────────────────┬────────────┘
           │  Celery Tasks                        │  Pub/Sub
┌──────────▼──────────┐               ┌──────────▼──────────┐
│    GPU Worker(s)    │               │        Redis 7       │
│  PyTorch + CUDA 12  │               │   Broker + Results   │
│  SAM · LaMa · ESRGAN│               └─────────────────────┘
└─────────────────────┘
```

### Processing Pipeline

```
Upload → Extract Frames → Auto-Detect / Manual Mask
       → GPU Inpaint (LaMa) → Temporal Smooth (Optical Flow)
       → Enhance (Real-ESRGAN, optional) → Rebuild → Export
```

---

## 🛠 Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Web Framework | FastAPI 0.109+ |
| Task Queue | Celery 5.3+ |
| Message Broker | Redis 7 |
| Deep Learning | PyTorch 2.1+ with CUDA 12 |
| Segmentation | SAM (Segment Anything Model) |
| Inpainting | LaMa (Large Mask Inpainting) |
| Enhancement | Real-ESRGAN |
| OCR Detection | PaddleOCR |
| Object Detection | Ultralytics YOLOv8 |
| Video Processing | OpenCV + FFmpeg |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript 5 |
| UI Library | React 19 |
| Styling | Tailwind CSS 4 |
| Icons | Lucide React |

### Infrastructure
| Layer | Technology |
|---|---|
| Containerisation | Docker + Docker Compose |
| GPU Passthrough | NVIDIA Container Toolkit |
| Reverse Proxy | (Nginx — optional) |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- NVIDIA GPU with CUDA 12+ drivers
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/blockforge-ai.git
cd blockforge-ai
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

### 3. Download AI Models

```bash
mkdir -p ai_models/sam ai_models/lama ai_models/realesrgan

# SAM ViT-H (Segment Anything)
wget -O ai_models/sam/sam_vit_h_4b8939.pth \
  https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

# LaMa (Large Mask Inpainting)
# Download from: https://huggingface.co/Sanster/models/resolve/main/big-lama.pt
# Save as: ai_models/lama/big-lama  (no file extension)

# Real-ESRGAN x4 (Optional Quality Enhancement)
wget -O ai_models/realesrgan/RealESRGAN_x4plus.pth \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
```

### 4. Launch with Docker

```bash
docker compose up --build
```

### 5. Open the Studio

| Service | URL |
|---|---|
| **Studio** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

---

## 🍎 Apple Silicon (M1/M2/M3) Local Setup

### Prerequisites

```bash
brew install ffmpeg redis
brew services start redis
```

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install torch torchvision torchaudio
pip install basicsr --no-deps     # Critical: avoids Python 3.11 compat issue
pip install -r requirements.txt

uvicorn main:app --reload
```

### Celery Worker (separate terminal)

```bash
source backend/venv/bin/activate
celery -A workers.tasks.celery_app worker --loglevel=info --pool=solo
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚙ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery task broker |
| `GPU_DEVICE` | `cuda:0` | GPU device (`mps` for Apple, `cpu` fallback) |
| `USE_FP16` | `true` | Mixed precision inference |
| `GPU_BATCH_SIZE` | `4` | Frames processed per GPU batch |
| `DEFAULT_CRF` | `18` | Output quality (0=lossless, 51=worst) |
| `DEFAULT_CODEC` | `libx264` | Video encoder |
| `MAX_VIDEO_SIZE_MB` | `500` | Max upload size in MB |

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a video file |
| `GET` | `/api/upload/{id}/frame` | Fetch a preview frame |
| `POST` | `/api/process` | Start a processing job |
| `GET` | `/api/status/{id}` | Poll job status |
| `GET` | `/api/status/{id}/download` | Download processed video |
| `WS` | `/ws/{id}` | Real-time progress stream |
| `GET` | `/health` | Service health check |

Full interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit with conventional commits: `git commit -m "feat: add xyz"`
4. Push and open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

## 🤝 Code of Conduct

We are committed to fostering a welcoming, inclusive, and respectful community. By participating in this project, you agree to abide by our Code of Conduct.

Please read the full [`Code of Conduct`](CODE_OF_CONDUCT.md) before contributing.

---

<div align="center">
  <sub>Built with ⛏ by the BlockForge Team</sub>
</div>

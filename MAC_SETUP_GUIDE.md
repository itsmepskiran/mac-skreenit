# Mac Setup Guide for Skreenit Backend

## Quick Start

```bash
# Clone and navigate to the project
cd mac-skreenit

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements-mac.txt

# Run the backend
python main.py
```

---

## System Requirements

| Requirement | Intel Mac | Apple Silicon (M1/M2/M3) |
|------------|-----------|--------------------------|
| **Python** | 3.10+ | 3.10+ (ARM-native preferred) |
| **RAM** | 8GB minimum, 16GB+ recommended | 8GB minimum, 16GB+ recommended |
| **Disk Space** | 10GB+ (for ML models) | 10GB+ (for ML models) |
| **Acceleration** | CPU only | Metal GPU acceleration (auto) |
| **Performance** | Moderate | Better with M1/M2/M3 Metal |

---

## Installation Instructions

### 1. **Install Xcode Command Line Tools**

```bash
xcode-select --install
```

### 2. **Install Homebrew Dependencies**

```bash
# Install FFmpeg (required for video processing)
brew install ffmpeg

# Install audio libraries
brew install libsndfile

# Install libffi (sometimes needed for cryptography)
brew install libffi

# Optional: Install Ollama for local LLM (download from https://ollama.com)
# After installation, run: ollama serve
```

### 3. **Install Python (Recommended: Use pyenv)**

For **Apple Silicon Macs** (M1/M2/M3):
```bash
# Install pyenv
brew install pyenv

# Install ARM-native Python
pyenv install 3.12.0
pyenv local 3.12.0
```

For **Intel Macs**:
```bash
# Ensure you're using native Python, not Rosetta
python3 --version  # Should show Python 3.10+
```

### 4. **Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate

# Verify activation (you should see (venv) in your terminal)
which python
```

### 5. **Install Dependencies**

```bash
# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Install requirements for Mac
pip install -r requirements-mac.txt

# Note: This may take 10-20 minutes depending on your Mac specs
```

### 6. **Verify Installation**

```bash
# Verify PyTorch
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CPU Available: {torch.cuda.is_available() == False}')"

# Verify OpenCV
python -c "import cv2; print(f'OpenCV {cv2.__version__}')"

# Verify ONNX Runtime (CPU version)
python -c "import onnxruntime; print(f'ONNX Runtime {onnxruntime.__version__}')"

# Verify MediaPipe
python -c "import mediapipe; print('MediaPipe installed')"

# Verify FastAPI
python -c "from fastapi import FastAPI; print('FastAPI ready')"
```

---

## Running the Backend

### Start the Backend Server

```bash
source venv/bin/activate  # If not already activated
python main.py
```

The server should start on `http://localhost:8000`

### Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Run in Production Mode

```bash
ENVIRONMENT=production python main.py
```

---

## Configuration Files

### 1. **.env File**

Copy and configure the .env file:

```bash
cp .env.example .env  # If example exists, or create new
```

Key variables to set:
```
ENVIRONMENT=development
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/skreenit
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
JWT_SECRET_KEY=your-secret-key-here
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret
OLLAMA_API_URL=http://localhost:11434
```

### 2. **Database Setup**

You need MySQL running locally:

```bash
# Install MySQL via Homebrew
brew install mysql

# Start MySQL
brew services start mysql

# Create database
mysql -u root -p -e "CREATE DATABASE skreenit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run migrations
python run_migrations.py
```

---

## Performance Notes for Mac

### Why Mac is Slower

| Operation | GPU (Windows/Linux) | CPU (Mac) | Relative Speed |
|-----------|-------------------|----------|-----------------|
| Video Analysis (1 min) | 30-60 sec | 3-5 min | 3-5x slower |
| Resume Parsing | 2-5 sec | 5-10 sec | 2-3x slower |
| Interview Transcription | 30 sec (1 min video) | 1-2 min | 2-4x slower |
| Face/Emotion Detection | 5-10 sec | 20-40 sec | 2-4x slower |

### Optimize for Mac

1. **Use Metal Acceleration on M1/M2/M3**
   - PyTorch automatically uses Metal GPU acceleration
   - No additional setup needed
   - Performance: ~2x faster than CPU-only

2. **CPU Parallelization with Ray**
   - Ray distributes processing across all CPU cores
   - Already included in requirements-mac.txt
   - Good for batch processing

3. **Model Size**
   - Use smaller Whisper models: `tiny` or `base` instead of `medium`
   - Trade-off: Speed vs. accuracy

4. **Disable Unused Features**
   - If you don't need certain ML features, disable them in `config.py`

---

## Troubleshooting

### Issue: `pip install` fails for OpenCV or MediaPipe

**Solution**:
```bash
# Clear pip cache
pip install --no-cache-dir -r requirements-mac.txt

# Or install packages individually with verbose output
pip install --no-cache-dir opencv-python -v
```

### Issue: ModuleNotFoundError for M1/M2/M3 Macs

**Problem**: Binary packages not compiled for ARM architecture

**Solution**:
```bash
# Set architecture flag
export ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future
pip install -r requirements-mac.txt
```

### Issue: FFmpeg not found when processing videos

**Solution**:
```bash
# Reinstall FFmpeg
brew uninstall ffmpeg
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### Issue: "No module named 'torch'"

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall PyTorch
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio
```

### Issue: MySQL connection fails

**Solution**:
```bash
# Check if MySQL is running
brew services list

# Start MySQL if stopped
brew services start mysql

# Verify connection
mysql -u root -p
```

### Issue: Port 8000 already in use

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
PORT=8001 python main.py
```

---

## Advanced: Setup for Development

### 1. **Install Development Tools**

```bash
pip install pytest pytest-asyncio black isort flake8 mypy
```

### 2. **Run Tests**

```bash
pytest tests/ -v
```

### 3. **Code Formatting**

```bash
black .
isort .
```

### 4. **Type Checking**

```bash
mypy .
```

---

## Using Ollama for Local LLM

### 1. **Download and Install Ollama**

Visit https://ollama.com and download for Mac

### 2. **Start Ollama Service**

```bash
ollama serve
```

This starts Ollama on `http://localhost:11434`

### 3. **Pull a Model**

In another terminal:
```bash
ollama pull llama2
# or
ollama pull llama3.2
```

### 4. **Verify in Backend**

Update `.env`:
```
OLLAMA_API_URL=http://localhost:11434
```

Test connection:
```bash
python -c "
import requests
try:
    response = requests.get('http://localhost:11434/api/tags')
    print('Ollama connected:', response.json())
except Exception as e:
    print('Ollama not running:', e)
"
```

---

## Key Differences: requirements.txt vs requirements-mac.txt

| Aspect | Original (requirements.txt) | Mac Version (requirements-mac.txt) |
|--------|---------------------------|----------------------------------|
| PyTorch | `torch==2.2.0+cu121` (CUDA GPU) | `torch==2.2.0` (CPU/Metal) |
| ONNX Runtime | `onnxruntime-gpu` | `onnxruntime` (CPU) |
| GPU Monitoring | Includes `pynvml`, `GPUtil` | Removed (not applicable) |
| Hardware Target | Linux/Windows workstation | Mac (Intel & Apple Silicon) |
| Performance | GPU accelerated | CPU/Metal accelerated |
| Setup Complexity | Medium | Low-Medium |

---

## Resources

- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
- [Ollama Documentation](https://ollama.ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MySQL on Mac](https://dev.mysql.com/doc/mysql-installation-excerpt/en/macos-installation.html)

---

## Support

For issues specific to Mac setup:

1. Check the **Troubleshooting** section above
2. Verify Python version: `python --version`
3. Check virtual environment: `which python` (should show path with `venv`)
4. Review error messages carefully - most are self-explanatory
5. Try searching the error message on StackOverflow

---

**Last Updated**: 2026-06-18  
**Compatible with**: Python 3.10+, macOS 11+, Intel & Apple Silicon Macs

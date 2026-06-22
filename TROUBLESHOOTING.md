# Skreenit Backend - Troubleshooting Guide

## Issue 1: ModuleNotFoundError: No module named 'pkg_resources'

### Root Cause
`pkg_resources` is provided by `setuptools` package. When razorpay (or other packages) try to import it, setuptools must be installed.

### Solution
Installed `setuptools>=65.0` in requirements files.

### Fix Applied
```
setuptools>=65.0
wheel>=0.40.0
```

These are now included in both `requirements-mac.txt` and `requirements.txt`.

---

## Issue 2: RequestsDependencyWarning about urllib3/chardet/charset_normalizer

### Root Cause
Version mismatch between:
- `requests` package
- `urllib3` (used by requests)
- `chardet` or `charset_normalizer` (encoding detection)

### Solution
Pinned compatible versions:
```
requests>=2.31.0
urllib3>=2.0.0,<3.0.0
charset-normalizer>=3.0.0
```

### Why These Versions?
- `requests>=2.31.0` - Modern version with good compatibility
- `urllib3>=2.0.0,<3.0.0` - Latest stable 2.x series
- `charset-normalizer>=3.0.0` - Modern, preferred over chardet

---

## Installation Fix Steps

### 1. **Reinstall with Updated Requirements**

```bash
cd ~/Projects/Skreenit/mac-skreenit

# Activate virtual environment
source venv/bin/activate

# Clear old installations
pip uninstall -y setuptools requests urllib3 charset-normalizer

# Reinstall from updated requirements
pip install -r requirements-mac.txt

# Verify installation
pip check
```

### 2. **Verify All Critical Packages**

```bash
python -c "
import sys
packages = ['setuptools', 'requests', 'urllib3', 'charset_normalizer', 'pkg_resources', 'razorpay']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError as e:
        print(f'❌ {pkg}: {e}')
"
```

### 3. **Run Backend Again**

```bash
uvicorn main:app --port 8080 --reload --host 0.0.0.0
```

---

## Common Errors & Solutions

### Error: `RequestsDependencyWarning`

**Message:**
```
urllib3 (2.7.0) or chardet (7.4.3)/charset_normalizer (3.4.7) doesn't match a supported version!
```

**Fix:**
```bash
pip install --upgrade requests urllib3 charset-normalizer
```

---

### Error: `No module named 'pkg_resources'`

**Message:**
```
ModuleNotFoundError: No module named 'pkg_resources'
```

**Fix:**
```bash
pip install setuptools>=65.0
```

---

### Error: `No module named 'XXX'` (Generic)

**Diagnosis:**
```bash
# Check if all dependencies are installed
pip check

# List all installed packages
pip list | grep -i razorpay
pip list | grep -i requests
```

**Fix:**
```bash
# Reinstall requirements
pip install -r requirements-mac.txt --upgrade --no-cache-dir
```

---

## Verification Checklist

After installation, verify:

- [ ] Virtual environment activated: `which python` shows venv path
- [ ] All packages installed: `pip check` shows no errors
- [ ] Key packages present:
  - [ ] `setuptools` - `python -c "import setuptools; print(setuptools.__version__)"`
  - [ ] `pkg_resources` - `python -c "import pkg_resources"`
  - [ ] `razorpay` - `python -c "import razorpay; print(razorpay.__version__)"`
  - [ ] `requests` - `python -c "import requests; print(requests.__version__)"`
  - [ ] `urllib3` - `python -c "import urllib3; print(urllib3.__version__)"`

- [ ] Backend starts: `python main.py` (or `uvicorn main:app --reload`)
- [ ] No import errors in logs
- [ ] FastAPI docs accessible: http://localhost:8080/docs

---

## Quick Start (After Fixing)

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Verify setup
pip check

# 3. Start backend
uvicorn main:app --port 8080 --reload --host 0.0.0.0

# 4. Open browser
open http://localhost:8080/docs
```

---

## If Issues Persist

### Step 1: Clean Install

```bash
# Remove virtual environment
rm -rf venv

# Create fresh environment
python3.12 -m venv venv
source venv/bin/activate

# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements-mac.txt

# Verify
pip check
```

### Step 2: Check Python Version

```bash
python --version  # Should be 3.10+
python -c "import platform; print(platform.machine())"  # Should be arm64
```

### Step 3: Verify Dependencies

```bash
# Check core dependencies
python -c "
import torch
import fastapi
import sqlalchemy
import razorpay
import setuptools
print('All core dependencies OK!')
"
```

### Step 4: Run with Debugging

```bash
# Run with full traceback
python main.py 2>&1 | head -50

# Or with uvicorn debug
uvicorn main:app --reload --log-level debug
```

---

## Platform-Specific Notes

### macOS (Intel & Apple Silicon)

- Python should be ARM64 native: `python -c "import platform; print(platform.machine())"`  → should be `arm64`
- If showing `x86_64`, you're running under Rosetta (slower)
- Install ARM64 Python: `pyenv install 3.12.0 && pyenv local 3.12.0`

### Linux/Windows

- CUDA must be installed for GPU support
- Verify with: `python -c "import torch; print(torch.cuda.is_available())"`

---

## Performance Checklist

After successful startup, verify performance features:

```bash
python << 'EOF'
import torch
import platform

print("=== System Info ===")
print(f"Platform: {platform.system()} ({platform.machine()})")
print(f"Python: {platform.python_version()}")

print("\n=== PyTorch ===")
print(f"PyTorch: {torch.__version__}")
if platform.system() == "Darwin":
    print(f"Metal Available: {torch.backends.mps.is_available()}")
elif platform.system() == "Linux":
    print(f"CUDA Available: {torch.cuda.is_available()}")

print("\n=== Backend Ready ===")
print("✅ Backend configuration verified")
EOF
```

---

## Getting Help

If issues continue after following this guide:

1. Check the error message carefully - it usually points to the issue
2. Search error in: Google, GitHub Issues, Stack Overflow
3. Run `pip check` to identify dependency conflicts
4. Clean install virtual environment (see "Clean Install" section)
5. Verify you're on correct Python version and architecture

---

**Last Updated**: 2026-06-18  
**Applies to**: Python 3.10+, macOS/Linux/Windows

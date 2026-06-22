# SciPy Installation Fix for Mac

## Issue
scipy build fails with: "ERROR: Dependency 'OpenBLAS' not found"

## Root Causes
1. OpenBLAS not installed on Mac
2. Python might be running under Rosetta (x86_64) instead of ARM64
3. Build tools not properly configured

## Solution

### Step 1: Install OpenBLAS via Homebrew
```bash
brew install openblas
```

### Step 2: Set Environment Variables
```bash
export OPENBLAS=$(brew --prefix openblas)
export LDFLAGS="-L${OPENBLAS}/lib"
export CPPFLAGS="-I${OPENBLAS}/include"
```

### Step 3: Verify ARM64 Architecture (Important!)
```bash
# Check current Python architecture
python -c "import platform; print(platform.machine())"

# Should print: arm64
# If it prints x86_64, you're running via Rosetta (slower!)
```

### Step 4: If Running x86_64 (Rosetta) - Fix It!
```bash
# Check if you're using Rosetta
arch
# Should print: arm64
# If it prints i386, you need to fix this

# Solution: Use pyenv to install ARM64 Python
brew install pyenv
pyenv install 3.12.0
pyenv local 3.12.0
cd ~/Projects/Skreenit/mac-skreenit
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
```

### Step 5: Install Requirements
```bash
# Activate venv
source venv/bin/activate

# With OpenBLAS environment set
export OPENBLAS=$(brew --prefix openblas)
export LDFLAGS="-L${OPENBLAS}/lib"
export CPPFLAGS="-I${OPENBLAS}/include"

# Install packages
pip install --upgrade pip setuptools wheel
pip install -r requirements-mac.txt
```

## Quick Fix Script

Save as `install_scipy_mac.sh`:

```bash
#!/bin/bash

# Install OpenBLAS
echo "Installing OpenBLAS..."
brew install openblas

# Set environment variables
export OPENBLAS=$(brew --prefix openblas)
export LDFLAGS="-L${OPENBLAS}/lib"
export CPPFLAGS="-I${OPENBLAS}/include"
export LD_LIBRARY_PATH="${OPENBLAS}/lib:$LD_LIBRARY_PATH"

# Verify architecture
echo "Checking Python architecture..."
ARCH=$(python -c "import platform; print(platform.machine())")
echo "Current architecture: $ARCH"

if [ "$ARCH" = "x86_64" ]; then
    echo "WARNING: Running x86_64 (Rosetta) - SLOW!"
    echo "Install ARM64 Python: brew install pyenv && pyenv install 3.12.0"
fi

# Install requirements
echo "Installing requirements..."
pip install --upgrade pip setuptools wheel
pip install -r requirements-mac.txt

echo "✅ Done!"
```

## Permanent Fix (Add to ~/.zshrc or ~/.bash_profile)

```bash
# OpenBLAS for scipy
export OPENBLAS=$(brew --prefix openblas)
export LDFLAGS="-L${OPENBLAS}/lib"
export CPPFLAGS="-I${OPENBLAS}/include"
export LD_LIBRARY_PATH="${OPENBLAS}/lib:$LD_LIBRARY_PATH"
```

Then reload shell:
```bash
source ~/.zshrc  # or ~/.bash_profile
```

## Verify Installation

```bash
python -c "import scipy; print(f'SciPy: {scipy.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
```

## If Still Failing

```bash
# Try installing scipy separately with verbose output
pip install --no-cache-dir -v scipy==1.12.0

# Or use pre-built wheel
pip install --only-binary :all: scipy
```

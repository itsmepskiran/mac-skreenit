# SciPy 1.12.0 Wheel Issue - Mac ARM64 Fix

## Problem
scipy 1.12.0 doesn't have pre-built wheels for Mac ARM64, causing build failures.

## Solution
Updated scipy to >=1.14.0 which has proper wheel support for Mac ARM64.

## Installation Steps

### Step 1: Clean Previous Install Attempt
```bash
cd ~/Projects/Skreenit/mac-skreenit
source venv/bin/activate
pip cache purge
```

### Step 2: Reinstall with Updated Requirements
```bash
# Install with --only-binary to use pre-built wheels only
pip install --only-binary :all: -r requirements-mac.txt
```

### Step 3: If Above Fails, Try Individual Install
```bash
# First update numpy
pip install --upgrade numpy

# Then scipy with wheels only
pip install --only-binary :all: scipy>=1.14.0

# Then rest of requirements
pip install -r requirements-mac.txt
```

### Step 4: Verify
```bash
python -c "import scipy; print(f'✅ SciPy {scipy.__version__}')"
```

## What Changed
- scipy: 1.12.0 → >=1.14.0
- Reason: 1.14.0+ has pre-built wheels for Mac ARM64
- No need to compile from source
- Faster installation

## Run This Now:
```bash
cd ~/Projects/Skreenit/mac-skreenit
source venv/bin/activate
pip cache purge
pip install --only-binary :all: -r requirements-mac.txt
```

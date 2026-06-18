"""
Platform detection utilities for Mac, Linux, and Windows compatibility.
Enables automatic detection and optimization for the current platform.
"""

import platform
import sys
from typing import Literal
from utils_others.logger import logger


def get_platform() -> Literal["darwin", "linux", "windows", "unknown"]:
    """Get current platform: darwin (Mac), linux, windows, or unknown."""
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    return "unknown"


def is_mac() -> bool:
    """Check if running on macOS."""
    return get_platform() == "darwin"


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform() == "linux"


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform() == "windows"


def get_temp_dir() -> str:
    """Get platform-appropriate temp directory."""
    import tempfile
    return tempfile.gettempdir()


def get_available_acceleration() -> Literal["mps", "cuda", "cpu"]:
    """
    Detect available GPU acceleration on current platform.

    Returns:
        "mps" - Apple Silicon Metal Performance Shaders
        "cuda" - NVIDIA CUDA GPU
        "cpu" - CPU only
    """
    try:
        import torch

        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            logger.info("Metal Performance Shaders (MPS) available - using Apple GPU acceleration")
            return "mps"
        elif torch.cuda.is_available():
            logger.info(f"CUDA available - using NVIDIA GPU acceleration (Device: {torch.cuda.get_device_name(0)})")
            return "cuda"
        else:
            logger.info("No GPU acceleration available - using CPU")
            return "cpu"
    except ImportError:
        logger.warning("PyTorch not available - cannot detect GPU acceleration")
        return "cpu"


def get_system_info() -> dict:
    """Get comprehensive system information."""
    try:
        import psutil

        system_info = {
            "platform": get_platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "gpu_acceleration": get_available_acceleration(),
        }
        return system_info
    except ImportError:
        logger.warning("psutil not available - limited system info")
        return {
            "platform": get_platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "gpu_acceleration": get_available_acceleration(),
        }


def print_system_info():
    """Print formatted system information at startup."""
    info = get_system_info()
    platform_name = info["platform"]

    if platform_name == "darwin":
        cores = info.get("cpu_cores", "?")
        memory = info.get("memory_gb", "?")
        gpu = info.get("gpu_acceleration", "cpu")
        machine = info.get("machine", "unknown")
        print(f"🍎 macOS Mode: {machine} | {cores} cores | {memory:.1f}GB RAM | GPU: {gpu}")
    elif platform_name == "linux":
        cores = info.get("cpu_cores", "?")
        memory = info.get("memory_gb", "?")
        gpu = info.get("gpu_acceleration", "cpu")
        print(f"🐧 Linux Mode: {cores} cores | {memory:.1f}GB RAM | GPU: {gpu}")
    elif platform_name == "windows":
        cores = info.get("cpu_cores", "?")
        memory = info.get("memory_gb", "?")
        gpu = info.get("gpu_acceleration", "cpu")
        print(f"🪟 Windows Mode: {cores} cores | {memory:.1f}GB RAM | GPU: {gpu}")
    else:
        print(f"❓ Unknown Platform: {platform_name}")

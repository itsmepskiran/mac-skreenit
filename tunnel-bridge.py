#!/usr/bin/env python3
"""
=============================================================================
SKREENIT TUNNEL BRIDGE - Local Server to Cloudflare Pages
=============================================================================
This script creates a bridge between your local backend server and the
Cloudflare Pages frontend using Cloudflare's quick tunnel.

Architecture:
- Backend: Local machine (Xeon E-2276M + 64GB RAM + Quadro T2000)
- Frontend: Cloudflare Pages (*.skreenit.com)
- Bridge: Cloudflare tunnel (*.trycloudflare.com)

Usage:
    python tunnel-bridge.py

Prerequisites:
    1. cloudflared installed (https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)
    2. Backend server running on http://localhost:8080
    3. Python 3.10+
=============================================================================
"""

import subprocess
import sys
import json
import re
import time
import os
from pathlib import Path


class TunnelBridge:
    """Manages the tunnel bridge between local backend and Cloudflare Pages frontend."""

    def __init__(self, backend_port: int = 8080):
        self.backend_port = backend_port
        self.tunnel_url = None
        self.tunnel_process = None
        self.backend_dir = Path(__file__).parent / "backend"

    def check_cloudflared(self) -> bool:
        """Check if cloudflared is installed."""
        try:
            result = subprocess.run(
                ["cloudflared", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def update_env_file(self, tunnel_url: str):
        """Update the .env file with the new tunnel URL."""
        env_path = self.backend_dir / ".env"

        if not env_path.exists():
            print(f"⚠️  Warning: {env_path} not found")
            return

        content = env_path.read_text()

        # Update or add TUNNEL_BACKEND_URL
        if "TUNNEL_BACKEND_URL=" in content:
            content = re.sub(
                r'TUNNEL_BACKEND_URL=.*',
                f'TUNNEL_BACKEND_URL={tunnel_url}',
                content
            )
        else:
            content += f"\nTUNNEL_BACKEND_URL={tunnel_url}\n"

        env_path.write_text(content)
        print(f"✅ Updated .env with tunnel URL: {tunnel_url}")

    def start_tunnel(self) -> subprocess.Popen:
        """Start the Cloudflare tunnel."""
        print(f"🚀 Starting tunnel to localhost:{self.backend_port}...")
        print("⏳ Waiting for tunnel URL...\n")

        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{self.backend_port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        return process

    def extract_tunnel_url(self, line: str) -> str:
        """Extract tunnel URL from cloudflared output."""
        # Match https://*.trycloudflare.com
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            return match.group(0)
        return None

    def print_instructions(self, tunnel_url: str):
        """Print setup instructions."""
        print("\n" + "=" * 70)
        print("🎉 TUNNEL BRIDGE ESTABLISHED!")
        print("=" * 70)
        print(f"\n🔗 Backend Local:     http://localhost:{self.backend_port}")
        print(f"🌐 Tunnel URL:        {tunnel_url}")
        print(f"☁️  Frontend Pages:    https://*.skreenit.com")
        print("\n" + "=" * 70)
        print("📋 FRONTEND CONFIGURATION:")
        print("=" * 70)
        print(f"""
Update your Cloudflare Pages frontend JavaScript to use:

    const API_BASE = "{tunnel_url}";
    
Or set the environment variable:

    VITE_API_BASE_URL={tunnel_url}

The tunnel will remain active as long as this script is running.
Press Ctrl+C to stop.
""")
        print("=" * 70 + "\n")

    def run(self):
        """Main entry point."""
        print("\n" + "=" * 70)
        print("   SKREENIT TUNNEL BRIDGE")
        print("   Local Server (Xeon + 64GB + Quadro T2000) → Cloudflare Pages")
        print("=" * 70 + "\n")

        # Check cloudflared
        if not self.check_cloudflared():
            print("❌ ERROR: cloudflared is not installed!")
            print("""
Please install cloudflared:
  1. Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
  2. Or use winget: winget install --id Cloudflare.cloudflared
  3. Or use brew: brew install cloudflared (macOS/Linux)
""")
            sys.exit(1)

        print("✅ cloudflared is installed")
        print(f"✅ Backend target: http://localhost:{self.backend_port}")
        print()

        # Start tunnel
        self.tunnel_process = self.start_tunnel()

        try:
            # Monitor output for tunnel URL
            url_found = False
            for line in self.tunnel_process.stdout:
                print(line, end='')

                if not url_found:
                    tunnel_url = self.extract_tunnel_url(line)
                    if tunnel_url:
                        self.tunnel_url = tunnel_url
                        url_found = True
                        self.update_env_file(tunnel_url)
                        self.print_instructions(tunnel_url)

        except KeyboardInterrupt:
            print("\n\n🛑 Stopping tunnel...")
            self.tunnel_process.terminate()
            print("✅ Tunnel closed")
        finally:
            if self.tunnel_process.poll() is None:
                self.tunnel_process.kill()


def main():
    """Main entry point."""
    bridge = TunnelBridge(backend_port=8080)
    bridge.run()


if __name__ == "__main__":
    main()

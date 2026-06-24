#!/usr/bin/env bash
# =============================================================================
#  build_apk.sh — Restaurant POS Android APK Builder
#  Run this script inside WSL2 (Ubuntu 20.04+) or any native Linux machine.
#  Usage:  bash build_apk.sh
# =============================================================================

set -e

echo "============================================="
echo " Restaurant POS — Android APK Builder"
echo "============================================="

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git zip unzip openjdk-17-jdk \
    libffi-dev libssl-dev \
    build-essential ccache \
    autoconf libtool \
    libltdl-dev

# ── 2. Python packages ────────────────────────────────────────────────────────
echo "[2/5] Installing Python build tools..."
pip3 install --upgrade pip
pip3 install buildozer cython

# ── 3. Android SDK/NDK (Buildozer handles this automatically) ─────────────────
echo "[3/5] Buildozer will auto-download Android SDK & NDK on first run."
echo "      (~2 GB download — this takes time on first build.)"

# ── 4. Build the APK ──────────────────────────────────────────────────────────
echo "[4/5] Building debug APK..."
cd "$(dirname "$0")"

buildozer -v android debug

# ── 5. Copy to delivery folder ────────────────────────────────────────────────
echo "[5/5] Copying APK to RestaurantPOS_Android_Build/..."
mkdir -p ../RestaurantPOS_Android_Build
cp bin/*.apk ../RestaurantPOS_Android_Build/RestaurantPOS.apk

echo ""
echo "============================================="
echo " BUILD COMPLETE!"
echo " APK saved to: RestaurantPOS_Android_Build/RestaurantPOS.apk"
echo "============================================="

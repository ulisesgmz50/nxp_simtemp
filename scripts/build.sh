#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# NXP SimTemp Build Script
# Builds kernel module and sets up user-space applications
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Determine project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  NXP SimTemp Build System"
echo "========================================="
echo ""

# Check for kernel headers
echo "[1/4] Checking kernel headers..."
KDIR="${KDIR:-/lib/modules/$(uname -r)/build}"

if [ ! -d "$KDIR" ]; then
    echo -e "${RED}ERROR: Kernel headers not found at $KDIR${NC}"
    echo ""
    echo "Please install kernel headers:"
    echo "  Ubuntu/Debian: sudo apt install linux-headers-\$(uname -r)"
    echo "  Fedora/RHEL:   sudo dnf install kernel-devel"
    echo "  Arch:          sudo pacman -S linux-headers"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓${NC} Kernel headers found: $KDIR"

# Build kernel module
echo ""
echo "[2/4] Building kernel module..."
cd "$PROJECT_ROOT/kernel"
make KDIR="$KDIR" clean > /dev/null 2>&1 || true
if make KDIR="$KDIR"; then
    echo -e "${GREEN}✓${NC} Kernel module built successfully"
    ls -lh nxp_simtemp.ko
else
    echo -e "${RED}✗${NC} Kernel module build failed"
    exit 1
fi

# Check for Python 3
echo ""
echo "[3/4] Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 not found${NC}"
    echo "Please install Python 3.8 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Setup user-space applications
echo ""
echo "[4/4] Setting up user-space applications..."

# CLI application
if [ -f "$PROJECT_ROOT/user/cli/requirements.txt" ]; then
    cd "$PROJECT_ROOT/user/cli"
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment for CLI..."
        python3 -m venv venv
    fi
    echo "  Installing CLI dependencies..."

    source $PROJECT_ROOT/user/cli/venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    deactivate
    echo -e "${GREEN}✓${NC} CLI application ready"
else
    echo -e "${YELLOW}⚠${NC} CLI requirements.txt not found (will be created in Phase 8)"
fi

# GUI application
if [ -f "$PROJECT_ROOT/user/gui/requirements.txt" ]; then
    cd "$PROJECT_ROOT/user/gui"
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment for GUI..."
        python3 -m venv venv
    fi
    echo "  Installing GUI dependencies..."
    source $PROJECT_ROOT/user/gui/venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    deactivate
    echo -e "${GREEN}✓${NC} GUI application ready"
else
    echo -e "${YELLOW}⚠${NC} GUI requirements.txt not found"
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}✓ Build completed successfully!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Load module:   sudo insmod kernel/nxp_simtemp.ko"
echo "  2. Check device:  ls -l /dev/simtemp"
echo "  3. Run demo:      sudo ./scripts/run_demo.sh"
echo ""

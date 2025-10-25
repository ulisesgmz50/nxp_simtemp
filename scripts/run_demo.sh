#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# NXP SimTemp Demo Script
# Automated demonstration of the virtual temperature sensor
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo "========================================="
echo "  NXP SimTemp Automated Demo"
echo "========================================="
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    if lsmod | grep -q nxp_simtemp; then
        rmmod nxp_simtemp || true
        echo "Module unloaded"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Check if module exists
if [ ! -f "$PROJECT_ROOT/kernel/nxp_simtemp.ko" ]; then
    echo -e "${RED}ERROR: Kernel module not found${NC}"
    echo "Please run: ./scripts/build.sh"
    exit 1
fi

# Unload module if already loaded
if lsmod | grep -q nxp_simtemp; then
    echo "Module already loaded, unloading..."
    rmmod nxp_simtemp || true
    sleep 1
fi

# Load the module
echo "[1/5] Loading kernel module..."
if insmod "$PROJECT_ROOT/kernel/nxp_simtemp.ko"; then
    echo -e "${GREEN}✓${NC} Module loaded successfully"
    sleep 1
else
    echo -e "${RED}✗${NC} Failed to load module"
    dmesg | tail -20
    exit 1
fi

# Verify device creation
echo ""
echo "[2/5] Verifying device creation..."
if [ -e /dev/simtemp ]; then
    echo -e "${GREEN}✓${NC} /dev/simtemp exists"
    ls -l /dev/simtemp
else
    echo -e "${RED}✗${NC} /dev/simtemp not found"
    exit 1
fi

# Check sysfs attributes (when implemented)
echo ""
echo "[3/5] Checking sysfs attributes..."
SYSFS_PATH="/sys/class/misc/simtemp"
if [ -d "$SYSFS_PATH" ]; then
    echo -e "${GREEN}✓${NC} Sysfs directory exists: $SYSFS_PATH"
    ls -la "$SYSFS_PATH/" 2>/dev/null || echo "  (Attributes will be added in Phase 5)"
else
    echo -e "${YELLOW}⚠${NC} Sysfs attributes not yet implemented (Phase 5)"
fi

# Show kernel messages
echo ""
echo "[4/5] Recent kernel messages:"
dmesg | grep -i simtemp | tail -10

# Run CLI test (when implemented)
echo ""
echo "[5/5] Running CLI test..."
if [ -f "$PROJECT_ROOT/user/cli/simtemp_cli.py" ] && [ -x "$PROJECT_ROOT/user/cli/simtemp_cli.py" ]; then
    cd "$PROJECT_ROOT/user/cli"
    source venv/bin/activate 2>/dev/null || true
    if python3 simtemp_cli.py test 2>/dev/null; then
        echo -e "${GREEN}✓${NC} CLI test passed"
    else
        echo -e "${YELLOW}⚠${NC} CLI test not yet implemented (Phase 9)"
    fi
    deactivate 2>/dev/null || true
else
    echo -e "${YELLOW}⚠${NC} CLI application not yet implemented (Phase 8)"
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}✓ Demo completed successfully!${NC}"
echo "========================================="
echo ""
echo "Module is still loaded. To unload manually:"
echo "  sudo rmmod nxp_simtemp"
echo ""

# Disable cleanup on successful exit
trap - EXIT

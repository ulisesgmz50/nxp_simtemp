#!/bin/bash
# Launch script for NXP SimTemp GUI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if kernel module is loaded
if [ ! -e "/dev/simtemp" ]; then
    echo "ERROR: /dev/simtemp not found!"
    echo ""
    echo "Please load the kernel module first:"
    echo "  sudo insmod ../../kernel/nxp_simtemp.ko"
    echo ""
    exit 1
fi

# Check if sysfs interface exists
if [ ! -d "/sys/class/misc/simtemp" ]; then
    echo "ERROR: Sysfs interface not found!"
    echo ""
    echo "Please ensure the kernel module is properly loaded."
    echo ""
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found!"
    exit 1
fi

# Launch GUI
echo "Launching NXP SimTemp Monitor GUI..."
echo "Device: /dev/simtemp"
echo "Sysfs: /sys/class/misc/simtemp"
echo ""

python3 main.py

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "GUI exited with error code: $EXIT_CODE"
    echo "Check the error messages above."
fi

exit $EXIT_CODE

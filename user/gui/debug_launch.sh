#!/bin/bash
# Debug script to find segmentation fault location

echo "==================================="
echo "SimTemp GUI Debugger"
echo "==================================="
echo ""

# Enable core dumps
ulimit -c unlimited
echo "✓ Core dumps enabled"

# Check display
if [ -z "$DISPLAY" ]; then
    echo "✗ No DISPLAY set, using :0"
    export DISPLAY=:0
else
    echo "✓ DISPLAY=$DISPLAY"
fi

# Check dependencies
echo ""
echo "Checking dependencies..."
python3 -c "import tkinter; print('✓ tkinter available')" 2>/dev/null || echo "✗ tkinter missing"
python3 -c "import customtkinter; print('✓ customtkinter:', customtkinter.__version__)" 2>/dev/null || echo "✗ customtkinter missing"

echo ""
echo "==================================="
echo "Running with Python faulthandler..."
echo "==================================="
echo ""

# Run with faulthandler and verbose output
python3 -X dev -X faulthandler user/gui/modern_main.py 2>&1 | tee debug_output.log

EXIT_CODE=$?

echo ""
echo "==================================="
echo "Exit code: $EXIT_CODE"
echo "==================================="

# Check for core dump
if [ -f core ]; then
    echo ""
    echo "Core dump found! Analyzing with gdb..."
    echo ""
    gdb -batch -ex "bt" -ex "quit" python3 core
elif [ -f core.* ]; then
    CORE_FILE=$(ls -t core.* | head -1)
    echo ""
    echo "Core dump found: $CORE_FILE"
    echo "Analyzing with gdb..."
    echo ""
    gdb -batch -ex "bt" -ex "quit" python3 "$CORE_FILE"
else
    echo "No core dump generated"
fi

echo ""
echo "Debug output saved to: debug_output.log"
echo ""

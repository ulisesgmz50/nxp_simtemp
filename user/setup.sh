#!/bin/bash

#################################################################
# SimTemp Monitor - Setup Script
# Installs required dependencies for the modern GUI
#################################################################

set -e  # Exit on error

echo "==========================================="
echo "    SimTemp Monitor - Setup Script"
echo "==========================================="
echo

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )[\d.]+')
min_version="3.8"

if [ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" != "$min_version" ]; then
    echo "❌ Error: Python 3.8+ is required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version found"
echo

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo

# Test imports
echo "Testing imports..."
python3 -c "
import customtkinter
import matplotlib
import numpy
print('✅ All imports successful')
"
echo

echo "==========================================="
echo "    Setup Complete! 🎉"
echo "==========================================="
echo
echo "To run the modern GUI:"
echo "  1. Activate venv:  source venv/bin/activate"
echo "  2. Run application: python3 gui/modern_main.py"
echo
echo "Or run directly: venv/bin/python gui/modern_main.py"
echo
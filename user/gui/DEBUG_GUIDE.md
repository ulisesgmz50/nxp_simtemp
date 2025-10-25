# Segmentation Fault Debugging Guide

## Quick Start - Find the Problem Fast

### Method 1: Run the Debug Script (Easiest)
```bash
cd /home/med/Documents/uli-nxp
chmod +x user/gui/debug_launch.sh
./user/gui/debug_launch.sh
```

This will:
- Enable core dumps
- Run with Python faulthandler
- Show exactly where it crashes
- Analyze core dump if generated

### Method 2: Run Minimal Test (Isolate Problem)
```bash
cd /home/med/Documents/uli-nxp
python3 user/gui/minimal_test.py
```

This tests each component step by step. The last message printed before crash shows the problem area.

### Method 3: Run Debug Version (Detailed)
```bash
cd /home/med/Documents/uli-nxp
python3 user/gui/debug_main.py
```

This has print statements at every single step. Look for the last DEBUG message before crash.

---

## Understanding the Output

### If it crashes on "Creating CTk root window"
**Problem**: CustomTkinter or Tkinter initialization issue

**Solutions**:
```bash
# Check customtkinter version
pip3 show customtkinter

# Reinstall customtkinter
pip3 uninstall customtkinter
pip3 install customtkinter

# Check tkinter
python3 -c "import tkinter; print(tkinter.TkVersion)"

# Install tkinter if missing (Ubuntu/Debian)
sudo apt-get install python3-tk
```

### If it crashes on "Creating Canvas"
**Problem**: X11/Graphics driver issue

**Solutions**:
```bash
# Check X11 connection
xdpyinfo | head

# Try with software rendering
LIBGL_ALWAYS_SOFTWARE=1 python3 user/gui/minimal_test.py

# Update graphics drivers
sudo apt-get update
sudo apt-get upgrade
```

### If it crashes on "Creating CTkTextbox"
**Problem**: CustomTkinter version incompatibility

**Solutions**:
```bash
# Downgrade to stable version
pip3 install customtkinter==5.1.2

# Or try latest
pip3 install --upgrade customtkinter
```

### If it crashes on "_textbox tag configuration"
**Problem**: Private API access issue

**Solution**: This is already fixed in debug_app.py, but you can verify by commenting out lines 417-421 in modern_app.py

---

## Advanced Debugging

### Get Stack Trace with GDB

```bash
# Enable core dumps
ulimit -c unlimited

# Run the app
python3 user/gui/modern_main.py

# If it crashes, analyze the core dump
gdb python3 core

# In gdb, type:
bt          # Show backtrace
bt full     # Show full backtrace with variables
frame 0     # Go to crash frame
print var   # Print variable values
quit        # Exit gdb
```

### Use Python Faulthandler

```bash
# Run with faulthandler enabled
python3 -X faulthandler user/gui/modern_main.py
```

Output will show exact Python line that caused segfault:
```
Fatal Python error: Segmentation fault

Current thread 0x00007f8a9c9d2740 (most recent call first):
  File "/path/to/file.py", line 123, in function_name
```

### Enable All Debug Output

```bash
# Maximum verbosity
python3 -X dev -X faulthandler -X tracemalloc user/gui/debug_main.py 2>&1 | tee full_debug.log
```

### Check System Logs

```bash
# Check kernel logs for crashes
dmesg | tail -50

# Check X11 errors
grep -i "error\|segfault" ~/.xsession-errors
```

---

## Common Causes and Solutions

### 1. Missing Display
**Error**: `No DISPLAY environment variable set`

**Fix**:
```bash
export DISPLAY=:0
python3 user/gui/modern_main.py
```

### 2. Permission Issues
**Error**: `_tkinter.TclError: couldn't connect to display`

**Fix**:
```bash
# Allow X11 connections
xhost +local:

# Run as your user (not sudo)
python3 user/gui/modern_main.py
```

### 3. Font Issues
**Error**: Segfault when creating labels with specific fonts

**Fix**:
```bash
# Install common fonts
sudo apt-get install fonts-liberation fonts-dejavu

# Or use system default fonts (edit modern_app.py)
# Change: font=("Arial", 20)
# To: font=("TkDefaultFont", 20)
```

### 4. Graphics Driver Issues
**Error**: Segfault in OpenGL/graphics libraries

**Fix**:
```bash
# Use software rendering
export LIBGL_ALWAYS_SOFTWARE=1
python3 user/gui/modern_main.py

# Or disable hardware acceleration
export QT_X11_NO_MITSHM=1
python3 user/gui/modern_main.py
```

### 5. CustomTkinter Version Issues
**Error**: Segfault in customtkinter code

**Fix**:
```bash
# Try specific working versions
pip3 install customtkinter==5.1.3  # Known stable
# or
pip3 install customtkinter==5.2.0
```

---

## Step-by-Step Debugging Process

### Step 1: Basic Environment Check
```bash
echo "Python version:"
python3 --version

echo "Display:"
echo $DISPLAY

echo "Tkinter:"
python3 -c "import tkinter; print('OK')"

echo "CustomTkinter:"
python3 -c "import customtkinter; print('OK')"
```

### Step 2: Run Minimal Test
```bash
python3 user/gui/minimal_test.py
```
Note which TEST number fails.

### Step 3: Run Debug Version
```bash
python3 user/gui/debug_main.py 2>&1 | tee debug.log
```
Check debug.log for last successful DEBUG line.

### Step 4: Analyze Core Dump
```bash
ulimit -c unlimited
python3 user/gui/modern_main.py
# After crash:
ls -lh core*
gdb python3 core -ex bt -ex quit
```

### Step 5: Test Fixes
Based on where it crashes, apply appropriate fix and test:
```bash
# After applying fix:
python3 user/gui/debug_main.py
```

---

## Report Format (for getting help)

If you need to report this issue, provide:

```
**Environment:**
- OS: [uname -a output]
- Python: [python3 --version]
- CustomTkinter: [pip3 show customtkinter]
- Display: [echo $DISPLAY]

**Last successful debug line:**
[Copy from debug_main.py output]

**GDB backtrace:**
[Copy from gdb output]

**Full debug log:**
[Attach debug.log]
```

---

## Quick Fix Checklist

Try these in order:

- [ ] `export DISPLAY=:0`
- [ ] `xhost +local:`
- [ ] `pip3 install --upgrade customtkinter`
- [ ] `sudo apt-get install python3-tk`
- [ ] `export LIBGL_ALWAYS_SOFTWARE=1`
- [ ] Use debug_main.py to find exact crash location
- [ ] Try minimal_test.py to isolate component
- [ ] Downgrade customtkinter: `pip3 install customtkinter==5.1.3`
- [ ] Check system logs: `dmesg | tail`
- [ ] Reboot (graphics driver issues)

---

## Still Crashing?

Run the complete diagnostic:

```bash
cd /home/med/Documents/uli-nxp

# Create diagnostic report
{
    echo "=== System Info ==="
    uname -a
    python3 --version
    echo "DISPLAY=$DISPLAY"

    echo -e "\n=== Python Packages ==="
    pip3 list | grep -E "tkinter|customtkinter"

    echo -e "\n=== Minimal Test ==="
    python3 user/gui/minimal_test.py 2>&1

    echo -e "\n=== Debug Run ==="
    python3 user/gui/debug_main.py 2>&1

    echo -e "\n=== System Logs ==="
    dmesg | tail -20
} > diagnostic_report.txt 2>&1

echo "Diagnostic complete! Check diagnostic_report.txt"
```

Then share the diagnostic_report.txt content.

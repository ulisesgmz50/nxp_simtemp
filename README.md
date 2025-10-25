# NXP SimTemp - Virtual Temperature Sensor

A Linux kernel module that simulates a hardware temperature sensor with configurable behavior, real-time monitoring, and event-driven alerts.

---

## Quick Start

```bash
# Build everything
./scripts/build.sh

# Run automated demo
sudo ./scripts/run_demo.sh

# Load module manually
sudo insmod kernel/nxp_simtemp.ko

# Check device
ls -l /dev/simtemp

# Monitor temperature with CLI
cd user/cli
pip3 install -r requirements.txt
./simtemp_cli.py monitor
```

---

##  Features

-  **Kernel Module**: Platform driver with Device Tree support
-  **Character Device**: `/dev/simtemp` for binary sample reading
-  **Poll/Epoll Support**: Efficient event-driven reading
-  **Sysfs Configuration**: Runtime configuration via `/sys/class/misc/simtemp/`
-  **Threshold Alerts**: Event notification when temperature exceeds threshold
-  **Multiple Modes**: Normal, noisy, and ramp temperature patterns
-  **CLI Application**: Python-based command-line interface
-  **GUI Application**: Optional graphical monitoring (PyQt5/Tkinter)
-  **Automated Testing**: Built-in test mode for validation

---

##  Requirements

### System Requirements
- Linux kernel 4.15 or later
- Kernel headers matching your running kernel
- GCC and build tools
- Python 3.8 or later

### Installation (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r)
sudo apt install python3 python3-pip python3-venv
```
---

##  Build Instructions

### 1. Clone Repository
```bash
git clone <repository-url>
cd uli-nxp
```

### 2. Build Kernel Module and User Applications
```bash
./scripts/build.sh
```

This will:
- Detect kernel headers
- Compile the kernel module
- Setup Python virtual environments
- Install dependencies

### 3. Load the Module
```bash
sudo insmod kernel/nxp_simtemp.ko
```

### 4. Verify Installation
```bash
# Check if device exists
ls -l /dev/simtemp

# Check sysfs attributes
ls /sys/class/misc/simtemp/

# View kernel messages
dmesg | grep simtemp
```

---

##  Usage

### Basic Reading
```bash
# Read raw binary samples
od -A x -t x8,x4,x4 /dev/simtemp | head

# Read with CLI (when implemented)
cd user/cli
source venv/bin/activate
python3 simtemp_cli.py monitor
```

### Configuration via Sysfs
```bash
# Change sampling rate to 50ms
echo 50 | sudo tee /sys/class/misc/simtemp/sampling_ms

# Set threshold to 42°C
echo 42000 | sudo tee /sys/class/misc/simtemp/threshold_mC

# Change mode to noisy
echo "noisy" | sudo tee /sys/class/misc/simtemp/mode

# View statistics
cat /sys/class/misc/simtemp/stats
```

### CLI Commands
```bash
cd user/cli
pip3 install -r requirements.txt

# View device information
./simtemp_cli.py info

# Monitor continuously
./simtemp_cli.py monitor

# Monitor 10 samples
./simtemp_cli.py monitor -n 10

# Configure device
sudo ./simtemp_cli.py config --sampling 100 --threshold 45.0 --mode normal

# Show configuration
./simtemp_cli.py config --show

# View statistics
./simtemp_cli.py stats

# Run automated test suite (CRITICAL)
./simtemp_cli.py test -v
```

### GUI Application
```bash
cd user/gui
source venv/bin/activate
python3 main.py
```

---

##  Testing

### Quick Test
```bash
./TEST_NOW.sh
```

Interactive test launcher that guides you through complete testing.

### Automated Kernel Module Tests 
```bash
sudo ./scripts/test_module.sh
```

Tests:
- Module load/unload
- Device creation (/dev/simtemp)
- Sysfs interface
- Read/write operations
- Kernel error checking

Expected output: `✓ ALL TESTS PASSED`

### Automated CLI Tests 
```bash
cd user/cli
pip3 install -r requirements.txt
./simtemp_cli.py test -v
```

Tests:
- Sysfs configuration
- Temperature modes
- Device reading
- Continuous monitoring
- Statistics verification
- Non-blocking mode

Expected output: `✓ ALL TESTS PASSED (6/6)`

### Manual Test Plan
See [TESTPLAN.md](TESTPLAN.md) for detailed test procedures.

### Load/Unload Stress Test
```bash
for i in {1..100}; do
    sudo insmod kernel/nxp_simtemp.ko
    sleep 0.1
    sudo rmmod nxp_simtemp
done
dmesg | grep -i "warn\|error\|bug"  # Should be empty
```

---

##  Documentation

- **[DESIGN.md](DESIGN.md)** - System architecture and design decisions
- **[TESTPLAN.md](TESTPLAN.md)** - Testing strategy and results
- **[AI_NOTES.md](AI_NOTES.md)** - AI assistance documentation

---

##  Troubleshooting

### Module Won't Load
```bash
# Check kernel version compatibility
uname -r

# Verify kernel headers
ls /lib/modules/$(uname -r)/build

# Check for detailed error messages
dmesg | tail -20
```

### Device Not Created
```bash
# Check if module is loaded
lsmod | grep nxp_simtemp

# Check kernel messages
dmesg | grep simtemp

# Verify miscdevice registration (Phase 3+)
ls /sys/class/misc/
```

### Permission Denied
```bash
# Check device permissions
ls -l /dev/simtemp

# Run as root or add user to appropriate group
sudo usermod -aG dialout $USER
# (log out and back in)
```

### Build Failures
```bash
# Install missing dependencies
sudo apt install build-essential linux-headers-$(uname -r)

# Clean and rebuild
cd kernel
make clean
make

# Check for specific error messages
```

---

##  License

GPL-2.0 - See kernel module source for details.

---

##  Author

**Ulises Mauricio Gomez Villa** - Systems Software Engineer Position

---

##  Acknowledgments

- NXP Semiconductors for the challenge opportunity
- Linux kernel community for excellent documentation
- Claude AI for development assistance (see AI_NOTES.md)

---

**Last Updated:** 2025-10-24

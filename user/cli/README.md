# NXP SimTemp CLI

Command-line interface for the NXP SimTemp virtual temperature sensor kernel module.

## Installation

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x simtemp_cli.py
```

## Usage

### Basic Commands

```bash
# Display help
./simtemp_cli.py --help

# Show device information
./simtemp_cli.py info

# Monitor temperature in real-time
./simtemp_cli.py monitor

# Monitor 10 samples
./simtemp_cli.py monitor -n 10

# View current configuration
./simtemp_cli.py config --show

# Change configuration (requires sudo)
sudo ./simtemp_cli.py config --sampling 200
sudo ./simtemp_cli.py config --threshold 45.5
sudo ./simtemp_cli.py config --mode noisy

# Display statistics
./simtemp_cli.py stats

# Watch statistics update
./simtemp_cli.py stats -w

# Run automated test suite
./simtemp_cli.py test
./simtemp_cli.py test --duration 30 -v
```

## Commands

### `monitor`
Real-time temperature monitoring. Continuously reads and displays temperature samples.

**Options:**
- `-n, --count` - Number of samples to read
- `-i, --interval` - Override sampling interval
- `-v, --verbose` - Verbose output
- `--no-color` - Disable colored output

### `config`
Configure device parameters via sysfs.

**Options:**
- `--show` - Show current configuration
- `--sampling MS` - Set sampling period (10-10000 ms)
- `--threshold CELSIUS` - Set threshold (-40.0 to 125.0°C)
- `--mode MODE` - Set mode (normal/noisy/ramp)

### `stats`
Display module statistics.

**Options:**
- `-w, --watch` - Continuously update
- `-i, --interval` - Update interval in seconds

### `test`
Run automated test suite (challenge requirement).

**Options:**
- `--duration` - Test duration in seconds
- `--threshold` - Threshold for testing
- `-v, --verbose` - Verbose output

### `info`
Display device information and status.

## Architecture

```
simtemp_cli.py         # Main CLI application (Click framework)
  └─> simtemp_device.py  # Low-level device interface
        ├─> /dev/simtemp              (character device)
        └─> /sys/class/misc/simtemp/  (sysfs attributes)
```

## Binary Protocol

The CLI reads 16-byte binary structures from `/dev/simtemp`:

```c
struct simtemp_sample {
    __u64 timestamp_ns;  // Monotonic timestamp (nanoseconds)
    __s32 temp_mC;       // Temperature (milli-Celsius)
    __u32 flags;         // Event flags
} __packed;
```

## Requirements

- Python 3.7+
- Click 8.0+
- Linux system with NXP SimTemp kernel module loaded

## Troubleshooting

**"Device not found" error:**
```bash
# Check if module is loaded
lsmod | grep nxp_simtemp

# Load the module
sudo insmod ../../kernel/nxp_simtemp.ko

# Check device exists
ls -l /dev/simtemp
```

**"Permission denied" error:**
```bash
# Run with sudo for configuration changes
sudo ./simtemp_cli.py config --sampling 200

# Or change device permissions (not recommended for production)
sudo chmod 666 /dev/simtemp
```

**"Module 'click' not found" error:**
```bash
# Install dependencies
pip install -r requirements.txt
```

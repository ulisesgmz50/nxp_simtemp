#!/usr/bin/env python3
"""
NXP SimTemp CLI Application
Command-line interface for interacting with the NXP SimTemp kernel module
"""

import click
import sys
import time
import signal
from typing import Optional
from simtemp_device import SimTempDevice, celsius_to_mC, mC_to_celsius


# Color definitions
class Colors:
    NORMAL = '\033[92m'  # Green
    WARNING = '\033[93m'  # Yellow
    ALERT = '\033[91m'  # Red
    INFO = '\033[94m'  # Blue
    RESET = '\033[0m'  # Reset
    BOLD = '\033[1m'


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Colorize text if terminal supports it"""
    if sys.stdout.isatty():
        prefix = Colors.BOLD if bold else ''
        return f"{prefix}{color}{text}{Colors.RESET}"
    return text


def print_error(message: str):
    """Print error message"""
    click.echo(colorize(f"ERROR: {message}", Colors.ALERT, bold=True), err=True)


def print_success(message: str):
    """Print success message"""
    click.echo(colorize(f"✓ {message}", Colors.NORMAL))


def print_warning(message: str):
    """Print warning message"""
    click.echo(colorize(f"⚠ {message}", Colors.WARNING))


def print_info(message: str):
    """Print info message"""
    click.echo(colorize(message, Colors.INFO))


def check_device_availability():
    """Check if device is available"""
    if not SimTempDevice.is_device_available():
        print_error(f"Device /dev/simtemp not found")
        print_info("Is the kernel module loaded? Try: sudo insmod kernel/nxp_simtemp.ko")
        sys.exit(1)

    if not SimTempDevice.is_sysfs_available():
        print_warning("Sysfs interface not available at /sys/class/misc/simtemp")


# Signal handler for graceful shutdown
interrupted = False


def signal_handler(sig, frame):
    global interrupted
    interrupted = True
    click.echo("\n" + colorize("Interrupted by user", Colors.WARNING))


signal.signal(signal.SIGINT, signal_handler)


# Main CLI group
@click.group()
@click.version_option(version="1.0", prog_name="simtemp")
def cli():
    """
    NXP SimTemp CLI - Interface for virtual temperature sensor

    A command-line tool to interact with the NXP SimTemp kernel module.
    Supports real-time monitoring, configuration, and automated testing.
    """
    pass


# Monitor command
@cli.command()
@click.option('-n', '--count', type=int, default=None,
              help='Number of samples to read (default: infinite)')
@click.option('-i', '--interval', type=float, default=None,
              help='Override sampling interval in seconds')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
def monitor(count: Optional[int], interval: Optional[float], no_color: bool, verbose: bool):
    """
    Monitor temperature readings in real-time

    Continuously displays temperature samples from the device.
    Press Ctrl+C to stop.

    Examples:
        simtemp monitor              # Monitor indefinitely
        simtemp monitor -n 10        # Read 10 samples
        simtemp monitor -i 0.5       # Override to 500ms interval
    """
    check_device_availability()

    try:
        with SimTempDevice() as device:
            if verbose:
                config = device.get_config()
                print_info(f"Configuration: {config['mode']} mode, "
                          f"sampling={config['sampling_ms']}ms, "
                          f"threshold={config['threshold_celsius']:.1f}°C")
                print_info(f"Reading {'infinite' if count is None else count} samples...\n")

            samples_read = 0
            start_time = time.time()

            for sample in device.read_samples_continuous(count=count):
                if interrupted:
                    break

                # Determine color based on temperature
                if no_color:
                    temp_str = f"{sample.temp_celsius:6.2f}°C"
                elif sample.is_threshold_crossed:
                    temp_str = colorize(f"{sample.temp_celsius:6.2f}°C", Colors.ALERT, bold=True)
                elif sample.temp_celsius > 50:
                    temp_str = colorize(f"{sample.temp_celsius:6.2f}°C", Colors.WARNING)
                else:
                    temp_str = colorize(f"{sample.temp_celsius:6.2f}°C", Colors.NORMAL)

                # Format output
                elapsed = time.time() - start_time
                output = f"[{elapsed:7.2f}s] {temp_str} ({sample.temp_mC:6d} mC)"

                if sample.is_threshold_crossed:
                    output += colorize(" ⚠ THRESHOLD", Colors.ALERT, bold=True)

                click.echo(output)
                samples_read += 1

                # Apply custom interval if specified
                if interval is not None and not interrupted:
                    time.sleep(interval)

            if verbose:
                elapsed = time.time() - start_time
                rate = samples_read / elapsed if elapsed > 0 else 0
                print_info(f"\nRead {samples_read} samples in {elapsed:.2f}s ({rate:.2f} samples/s)")

    except PermissionError:
        print_error("Permission denied accessing device. Try: sudo simtemp monitor")
        sys.exit(1)
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# Config command
@cli.command()
@click.option('--sampling', type=int, metavar='MS',
              help='Set sampling period in milliseconds (10-10000)')
@click.option('--threshold', type=float, metavar='CELSIUS',
              help='Set threshold in Celsius (-40.0 to 125.0)')
@click.option('--mode', type=click.Choice(['normal', 'noisy', 'ramp'], case_sensitive=False),
              help='Set temperature generation mode')
@click.option('--show', is_flag=True, help='Show current configuration')
def config(sampling: Optional[int], threshold: Optional[float], mode: Optional[str], show: bool):
    """
    Configure device parameters via sysfs

    View or modify device configuration without reloading the module.
    All changes take effect immediately.

    Examples:
        simtemp config --show                    # Show current config
        simtemp config --sampling 200            # Set 200ms sampling
        simtemp config --threshold 45.5          # Set 45.5°C threshold
        simtemp config --mode noisy              # Set noisy mode
        simtemp config --mode ramp --sampling 50 # Multiple changes
    """
    check_device_availability()

    device = SimTempDevice()

    try:
        # Show current configuration
        if show or (sampling is None and threshold is None and mode is None):
            config_data = device.get_config()
            click.echo(colorize("\n📊 Current Configuration:", Colors.INFO, bold=True))
            click.echo(f"  Sampling Period: {config_data['sampling_ms']} ms")
            click.echo(f"  Threshold:       {config_data['threshold_celsius']:.1f}°C ({config_data['threshold_mC']} mC)")
            click.echo(f"  Mode:            {config_data['mode']}")
            return

        # Apply changes
        changes_made = []

        if sampling is not None:
            device.set_sampling_ms(sampling)
            changes_made.append(f"sampling={sampling}ms")

        if threshold is not None:
            threshold_mC = celsius_to_mC(threshold)
            device.set_threshold_mC(threshold_mC)
            changes_made.append(f"threshold={threshold:.1f}°C")

        if mode is not None:
            device.set_mode(mode.lower())
            changes_made.append(f"mode={mode}")

        if changes_made:
            print_success(f"Configuration updated: {', '.join(changes_made)}")
        else:
            click.echo("No changes specified. Use --help for options.")

    except PermissionError as e:
        print_error(f"{e}")
        print_info("Try running with sudo: sudo simtemp config ...")
        sys.exit(1)
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to configure device: {e}")
        sys.exit(1)


# Stats command
@cli.command()
@click.option('-w', '--watch', is_flag=True, help='Continuously update statistics')
@click.option('-i', '--interval', type=float, default=1.0, help='Update interval in seconds (default: 1.0)')
def stats(watch: bool, interval: float):
    """
    Display module statistics

    Shows statistics counters from the kernel module including
    total samples generated, threshold alerts, and operation counts.

    Examples:
        simtemp stats           # Show stats once
        simtemp stats -w        # Watch stats update continuously
        simtemp stats -w -i 0.5 # Update every 500ms
    """
    check_device_availability()

    device = SimTempDevice()

    try:
        if watch:
            click.clear()
            last_stats = None

            while not interrupted:
                stats_data = device.get_stats()

                # Clear screen and print header
                click.clear()
                click.echo(colorize("📈 NXP SimTemp Statistics (Press Ctrl+C to stop)\n", Colors.INFO, bold=True))

                # Print statistics with delta
                for key, value in stats_data.items():
                    delta_str = ""
                    if last_stats and key in last_stats:
                        delta = value - last_stats[key]
                        if delta > 0:
                            delta_str = colorize(f" (+{delta})", Colors.NORMAL)

                    click.echo(f"  {key:20s}: {value:12d}{delta_str}")

                click.echo(f"\n  Updated: {time.strftime('%H:%M:%S')} (every {interval}s)")

                last_stats = stats_data
                time.sleep(interval)

        else:
            stats_data = device.get_stats()
            click.echo(colorize("\n📈 Module Statistics:", Colors.INFO, bold=True))
            for key, value in stats_data.items():
                click.echo(f"  {key:20s}: {value:12d}")

    except KeyboardInterrupt:
        click.echo("\n" + colorize("Stopped by user", Colors.WARNING))
    except Exception as e:
        print_error(f"Failed to read statistics: {e}")
        sys.exit(1)


# Test command (CRITICAL REQUIREMENT)
@cli.command()
@click.option('--duration', type=int, default=10, help='Test duration in seconds (default: 10)')
@click.option('--threshold', type=float, default=45.0, help='Threshold for testing (default: 45.0°C)')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
def test(duration: int, threshold: float, verbose: bool):
    """
    Run automated test suite

    Performs comprehensive testing of the kernel module including:
    - Configuration changes (all modes)
    - Temperature reading
    - Threshold detection
    - Statistics verification

    This is the automated test mode required by the challenge.

    Examples:
        simtemp test                    # Run default 10s test
        simtemp test --duration 30      # Run 30s test
        simtemp test --threshold 40 -v  # Verbose test with 40°C threshold
    """
    check_device_availability()

    click.echo(colorize("\n🧪 NXP SimTemp Automated Test Suite", Colors.INFO, bold=True))
    click.echo(f"Duration: {duration}s, Threshold: {threshold}°C\n")

    device = SimTempDevice()
    test_results = []

    def test_step(name: str, func):
        """Execute a test step and track results"""
        try:
            click.echo(colorize(f"→ Testing: {name}...", Colors.INFO))
            func()
            print_success(f"PASS: {name}")
            test_results.append((name, True, None))
            return True
        except Exception as e:
            print_error(f"FAIL: {name} - {e}")
            test_results.append((name, False, str(e)))
            return False

    # Test 1: Sysfs configuration
    def test_sysfs():
        original_config = device.get_config()
        if verbose:
            click.echo(f"  Original: {original_config}")

        # Test sampling period
        device.set_sampling_ms(150)
        assert device.get_sampling_ms() == 150, "Sampling period not set correctly"

        # Test threshold
        threshold_mC = celsius_to_mC(threshold)
        device.set_threshold_mC(threshold_mC)
        assert abs(device.get_threshold_mC() - threshold_mC) < 10, "Threshold not set correctly"

        if verbose:
            click.echo(f"  Modified: sampling=150ms, threshold={threshold}°C")

    test_step("Sysfs Configuration", test_sysfs)

    # Test 2: Temperature modes
    def test_modes():
        for mode in ['normal', 'noisy', 'ramp']:
            device.set_mode(mode)
            current = device.get_mode()
            assert current == mode, f"Mode '{mode}' not set correctly (got '{current}')"
            if verbose:
                click.echo(f"  Mode '{mode}' set successfully")
            time.sleep(0.2)

    test_step("Temperature Modes", test_modes)

    # Test 3: Device reading
    def test_reading():
        with SimTempDevice() as dev:
            sample = dev.read_sample()
            assert sample.temp_mC != 0, "Temperature reading is zero"
            assert -40000 <= sample.temp_mC <= 125000, "Temperature out of range"
            if verbose:
                click.echo(f"  Sample: {sample}")

    test_step("Device Reading", test_reading)

    # Test 4: Continuous monitoring
    def test_continuous():
        samples_to_read = max(5, duration // 2)
        threshold_crossings = 0
        temps = []

        with SimTempDevice() as dev:
            for i, sample in enumerate(dev.read_samples_continuous(count=samples_to_read)):
                temps.append(sample.temp_celsius)
                if sample.is_threshold_crossed:
                    threshold_crossings += 1
                    if verbose:
                        click.echo(f"  Threshold crossed at sample {i+1}: {sample.temp_celsius:.2f}°C")

        if verbose:
            avg_temp = sum(temps) / len(temps)
            min_temp = min(temps)
            max_temp = max(temps)
            click.echo(f"  Read {len(temps)} samples: min={min_temp:.1f}°C, max={max_temp:.1f}°C, avg={avg_temp:.1f}°C")
            click.echo(f"  Threshold crossings: {threshold_crossings}")

    test_step("Continuous Monitoring", test_continuous)

    # Test 5: Statistics verification
    def test_statistics():
        stats = device.get_stats()
        assert stats['total_samples'] > 0, "No samples generated"
        assert stats['read_count'] > 0, "No reads recorded"
        if verbose:
            click.echo(f"  Stats: {stats}")

    test_step("Statistics Verification", test_statistics)

    # Test 6: Non-blocking mode
    def test_nonblocking():
        dev = SimTempDevice()
        dev.open(non_blocking=True)
        try:
            # Give time for a sample
            time.sleep(0.2)
            try:
                sample = dev.read_sample()
                if verbose:
                    click.echo(f"  Non-blocking read: {sample.temp_celsius:.2f}°C")
            except TimeoutError:
                # Expected if no data yet
                if verbose:
                    click.echo("  Non-blocking mode working (no data available)")
        finally:
            dev.close()

    test_step("Non-blocking Mode", test_nonblocking)

    # Print test summary
    click.echo("\n" + colorize("=" * 60, Colors.INFO))
    click.echo(colorize("📊 Test Summary", Colors.INFO, bold=True))
    click.echo(colorize("=" * 60, Colors.INFO))

    passed = sum(1 for _, result, _ in test_results if result)
    total = len(test_results)

    for name, result, error in test_results:
        status = colorize("✓ PASS", Colors.NORMAL) if result else colorize("✗ FAIL", Colors.ALERT)
        click.echo(f"{status} - {name}")
        if error and verbose:
            click.echo(f"       Error: {error}")

    click.echo(colorize("=" * 60, Colors.INFO))

    if passed == total:
        click.echo(colorize(f"✓ ALL TESTS PASSED ({passed}/{total})", Colors.NORMAL, bold=True))
        sys.exit(0)
    else:
        click.echo(colorize(f"✗ SOME TESTS FAILED ({passed}/{total})", Colors.ALERT, bold=True))
        sys.exit(1)


# Info command
@cli.command()
def info():
    """
    Display device information

    Shows device status, paths, and availability.
    """
    click.echo(colorize("\n📋 NXP SimTemp Device Information", Colors.INFO, bold=True))

    # Check device
    device_avail = SimTempDevice.is_device_available()
    device_status = colorize("✓ Available", Colors.NORMAL) if device_avail else colorize("✗ Not Found", Colors.ALERT)
    click.echo(f"\nCharacter Device: {device_status}")
    click.echo(f"  Path: /dev/simtemp")

    # Check sysfs
    sysfs_avail = SimTempDevice.is_sysfs_available()
    sysfs_status = colorize("✓ Available", Colors.NORMAL) if sysfs_avail else colorize("✗ Not Found", Colors.ALERT)
    click.echo(f"\nSysfs Interface: {sysfs_status}")
    click.echo(f"  Path: /sys/class/misc/simtemp/")

    if sysfs_avail:
        click.echo(f"  Attributes:")
        click.echo(f"    - sampling_ms (RW)")
        click.echo(f"    - threshold_mC (RW)")
        click.echo(f"    - mode (RW)")
        click.echo(f"    - stats (RO)")

    if device_avail:
        try:
            device = SimTempDevice()
            config = device.get_config()
            click.echo(f"\nCurrent Configuration:")
            click.echo(f"  Sampling: {config['sampling_ms']} ms")
            click.echo(f"  Threshold: {config['threshold_celsius']:.1f}°C")
            click.echo(f"  Mode: {config['mode']}")
        except:
            pass

    if not device_avail:
        click.echo(colorize("\n⚠ Module not loaded. Try:", Colors.WARNING))
        click.echo("  sudo insmod kernel/nxp_simtemp.ko")


if __name__ == '__main__':
    cli()

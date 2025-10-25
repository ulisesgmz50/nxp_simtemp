# NXP SimTemp - System Design Document

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component Interactions](#component-interactions)
3. [Kernel Module Design](#kernel-module-design)
4. [User-Kernel Interface](#user-kernel-interface)
5. [Locking Strategy](#locking-strategy)
6. [API Specifications](#api-specifications)
7. [Device Tree Integration](#device-tree-integration)
8. [Performance Analysis](#performance-analysis)
9. [Security Considerations](#security-considerations)

---

## Architecture Overview

### System Block Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER SPACE                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │  CLI App     │              │   GUI App    │            │
│  │  (Python)    │              │  (Python)    │            │
│  │              │              │              │            │
│  │  - Monitor   │              │  - Live Plot │            │
│  │  - Configure │              │  - Controls  │            │
│  │  - Test Mode │              │  - Alerts    │            │
│  └──────┬───────┘              └──────┬───────┘            │
│         │                             │                     │
│         └─────────┬───────────────────┘                     │
│                   ▼                                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │         User-Kernel Interface                      │    │
│  │                                                     │    │
│  │  /dev/simtemp  │  /sys/class/misc/simtemp/*       │    │
│  │  (read, poll)  │  (sampling_ms, threshold_mC,     │    │
│  │                │   mode, stats)                    │    │
│  └────────────────┬───────────────────────────────────┘    │
└────────────────────┼────────────────────────────────────────┘
                     │ System Call Boundary
                     │ (copy_to_user, copy_from_user)
═══════════════════╧════════════════════════════════════════
┌────────────────────┼────────────────────────────────────────┐
│                    ▼         KERNEL SPACE                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           nxp_simtemp Kernel Module                  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────┐ │  │
│  │  │ Platform │  │   Char   │  │ Sysfs  │  │  DT   │ │  │
│  │  │  Driver  │  │  Device  │  │  Attrs │  │ Parse │ │  │
│  │  └────┬─────┘  └────┬─────┘  └───┬────┘  └───┬───┘ │  │
│  ├───────┴──────────────┴────────────┴───────────┴─────┤  │
│  │                 Core Data Structures                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────┐ │  │
│  │  │ HRTimer  │  │   Ring   │  │  Wait  │  │ Stats │ │  │
│  │  │(Periodic)│  │  Buffer  │  │  Queue │  │Counter│ │  │
│  │  └────┬─────┘  └────┬─────┘  └───┬────┘  └───┬───┘ │  │
│  └───────┴──────────────┴────────────┴───────────┴─────┘  │
│           │              │            │           │         │
│     Generate Temp → Store Sample → Wake Readers → Update   │
└──────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Kernel handles hardware abstraction, userspace handles presentation
2. **Stable ABI**: Binary interface versioned and documented
3. **Event-Driven**: No polling loops, use wait queues and poll/epoll
4. **Thread-Safe**: Proper locking for concurrent access
5. **Fail-Safe**: Graceful error handling and cleanup

---

## Component Interactions

### Data Flow

1. **Temperature Generation** (Timer Context - Atomic)
   - HRTimer fires every `sampling_ms` milliseconds
   - Timer callback generates temperature sample
   - Sample stored in ring buffer (spinlock protected)
   - Wait queue woken to unblock readers
   - Statistics updated

2. **Reading Path** (Process Context - Can Sleep)
   - User calls `read()` on `/dev/simtemp`
   - If no data available, process sleeps on wait queue
   - When data arrives, process wakes
   - Sample copied to user space with `copy_to_user()`
   - Ring buffer tail pointer advanced

3. **Configuration Path** (Process Context - Can Sleep)
   - User writes to sysfs attribute (e.g., `echo 50 > sampling_ms`)
   - Sysfs store callback invoked with mutex held
   - Value validated and stored
   - Timer updated if sampling period changed
   - Configuration takes effect immediately

4. **Poll/Epoll Path** (Process Context)
   - User calls `poll()` or `epoll_wait()`
   - Kernel adds file to wait queue
   - Returns immediately if data available
   - Otherwise blocks until woken by timer
   - Returns `POLLIN` for new data, `POLLPRI` for threshold alert

### Event Signaling

- **New Sample Event**: Set when timer generates new sample
  - Flag: `SIMTEMP_FLAG_NEW_SAMPLE`
  - Poll mask: `POLLIN | POLLRDNORM`

- **Threshold Crossed Event**: Set when temp exceeds threshold
  - Flag: `SIMTEMP_FLAG_THRESHOLD_CROSSED`
  - Poll mask: `POLLPRI`
  - Urgent notification for alert condition

---

## Kernel Module Design

### Module Structure

```c
struct simtemp_device {
    /* Platform device */
    struct platform_device *pdev;

    /* Character device */
    struct miscdevice miscdev;

    /* Timer for periodic sampling */
    struct hrtimer timer;
    ktime_t sampling_period;

    /* Ring buffer (spinlock protected) */
    struct simtemp_ringbuf ringbuf;

    /* Wait queue for blocking I/O */
    wait_queue_head_t wait_queue;

    /* Configuration (mutex protected) */
    struct mutex config_lock;
    u32 sampling_ms;
    s32 threshold_mC;
    enum simtemp_mode mode;

    /* Temperature state */
    s32 current_temp_mC;
    bool ramp_direction;

    /* Statistics */
    struct simtemp_stats stats;
};
```

### Initialization Sequence

1. `module_init()` → `platform_driver_register()`
2. Platform bus matches Device Tree node
3. `simtemp_probe()` called
4. Parse DT properties
5. Allocate device structure
6. Initialize ring buffer, wait queue, locks
7. Register character device (Phase 3)
8. Create sysfs attributes (Phase 5)
9. Start timer
10. Device ready

### Cleanup Sequence

1. `module_exit()` → `platform_driver_unregister()`
2. `simtemp_remove()` called
3. Cancel timer (critical - must be first!)
4. Wake all sleeping processes
5. Remove sysfs attributes
6. Unregister character device
7. Free device structure
8. Module unloaded

---

## User-Kernel Interface

### Character Device: `/dev/simtemp`

**Operations:**
- `open()`: Increment reference count
- `read()`: Return binary sample (blocking/non-blocking)
- `poll()`: Wait for events (new sample, threshold)
- `release()`: Decrement reference count

**Binary Format:**
```c
struct simtemp_sample {
    __u64 timestamp_ns;   // 8 bytes
    __s32 temp_mC;        // 4 bytes
    __u32 flags;          // 4 bytes
} __attribute__((packed));  // Total: 16 bytes
```

**Endianness:** Native (same as host CPU)
**Versioning:** V1 (no version field yet, size determines version)

### Sysfs Attributes: `/sys/class/misc/simtemp/`

| Attribute | Type | Permissions | Range | Description |
|-----------|------|-------------|-------|-------------|
| `sampling_ms` | u32 | 0644 (rw) | 1-10000 | Sampling period in milliseconds |
| `threshold_mC` | s32 | 0644 (rw) | -40000-125000 | Alert threshold in milli-°C |
| `mode` | string | 0644 (rw) | normal/noisy/ramp | Temperature generation mode |
| `stats` | string | 0444 (ro) | N/A | Statistics counters |

---

## Locking Strategy

### Design Rationale

**Two-Lock Strategy:**
1. **Spinlock** for ring buffer (atomic context, fast path)
2. **Mutex** for configuration (process context, slow path)

### Spinlock: `ringbuf.lock`

**Purpose:** Protect ring buffer data structure

**Context:** Atomic (can be called from timer interrupt)

**Protected Data:**
- `ringbuf.head` (write pointer)
- `ringbuf.tail` (read pointer)
- `ringbuf.buffer[]` (sample array)

**Critical Sections:**
```c
// Producer (timer callback - atomic context)
spin_lock(&dev->ringbuf.lock);
dev->ringbuf.buffer[head] = sample;
dev->ringbuf.head = (head + 1) & RING_BUFFER_MASK;
spin_unlock(&dev->ringbuf.lock);

// Consumer (read() - process context)
spin_lock(&dev->ringbuf.lock);
sample = dev->ringbuf.buffer[tail];
dev->ringbuf.tail = (tail + 1) & RING_BUFFER_MASK;
spin_unlock(&dev->ringbuf.lock);
```

**Why Spinlock?**
- Timer callback runs in interrupt context (cannot sleep)
- Very short critical section (few instructions)
- No memory allocation or I/O inside lock
- Lock-free algorithms considered but spinlock simpler and sufficient

### Mutex: `config_lock`

**Purpose:** Protect configuration changes

**Context:** Process context only (sysfs callbacks)

**Protected Data:**
- `dev->sampling_ms`
- `dev->threshold_mC`
- `dev->mode`
- Timer reconfiguration

**Critical Sections:**
```c
// Sysfs store callback
mutex_lock(&dev->config_lock);
dev->sampling_ms = new_value;
dev->sampling_period = ms_to_ktime(new_value);
hrtimer_cancel(&dev->timer);
hrtimer_start(&dev->timer, dev->sampling_period, HRTIMER_MODE_REL);
mutex_unlock(&dev->config_lock);
```

**Why Mutex?**
- Called only from process context (sysfs)
- May sleep (timer operations, validation)
- Longer critical section
- Reader-writer lock not needed (config changes rare)

### Wait Queue

**No explicit lock needed** - wait queue has internal synchronization

**Usage:**
```c
// Reader blocks if no data
wait_event_interruptible(dev->wait_queue, !ringbuf_empty(&dev->ringbuf));

// Timer wakes readers
wake_up_interruptible(&dev->wait_queue);
```

### Lock Ordering

**Rule:** Always acquire in this order to prevent deadlock:
1. `config_lock` (if needed)
2. `ringbuf.lock` (if needed)

**Example:**
```c
// Correct: config_lock → ringbuf.lock
mutex_lock(&dev->config_lock);
spin_lock(&dev->ringbuf.lock);
// ... critical section ...
spin_unlock(&dev->ringbuf.lock);
mutex_unlock(&dev->config_lock);

// Incorrect: ringbuf.lock → config_lock (potential deadlock!)
```

---

## API Specifications

### Binary Sample Format

**Structure:** `struct simtemp_sample` (16 bytes)

**Fields:**
- `timestamp_ns` (u64): Monotonic time from `ktime_get_ns()`
- `temp_mC` (s32): Temperature in milli-°C (e.g., 44123 = 44.123°C)
- `flags` (u32): Bit flags for events

**Flags:**
- Bit 0: `SIMTEMP_FLAG_NEW_SAMPLE` - Always set
- Bit 1: `SIMTEMP_FLAG_THRESHOLD_CROSSED` - Set when temp > threshold
- Bits 2-31: Reserved (must be zero)

**Endianness:** Native CPU byte order

**Compatibility:**
- Size check: `sizeof(struct simtemp_sample) == 16`
- Future versions may add fields (size will increase)
- Old binaries use size to detect version

### Sysfs API

**Reading:**
```bash
cat /sys/class/misc/simtemp/sampling_ms
# Output: "100\n"
```

**Writing:**
```bash
echo 50 > /sys/class/misc/simtemp/sampling_ms
# Returns: 0 on success, -EINVAL on error
```

**Stats Format:**
```
total_samples: 12345
threshold_alerts: 42
read_count: 567
poll_count: 890
```

---

## Device Tree Integration

### DT Binding

**Compatible String:** `"nxp,simtemp"`

**Properties:**
- `sampling-ms` (u32, optional): Default sampling period
- `threshold-mC` (u32, optional): Default threshold
- `status` (string): "okay" or "disabled"

**Example:**
```dts
simtemp0: simtemp@0 {
    compatible = "nxp,simtemp";
    sampling-ms = <100>;
    threshold-mC = <45000>;
    status = "okay";
};
```

### Probe Sequence

1. Platform bus matches `compatible = "nxp,simtemp"`
2. `of_match_table` → `simtemp_of_match[]`
3. `simtemp_probe()` called with `platform_device *pdev`
4. Extract DT node: `np = pdev->dev.of_node`
5. Parse properties: `of_property_read_u32(np, "sampling-ms", &val)`
6. Apply defaults if properties missing
7. Initialize device with DT values

### Fallback Behavior

If Device Tree node not present:
- Use hardcoded defaults
- Module still loads (manual instantiation possible)
- Warning logged to dmesg

---

## Performance Analysis

### Current Design

**Target Performance:**
- Sampling rate: 1 Hz to 1 kHz (1ms to 1000ms period)
- CPU overhead: <1% at 100 Hz
- Memory: <64 KB per device

**Measurements:** (To be filled after testing)

### Bottleneck Analysis

**What breaks at 10 kHz sampling (100 μs period)?**

1. **Timer Granularity**
   - HRTimer resolution: ~1 μs (depends on hardware)
   - At 10 kHz, timer overhead dominates
   - **Mitigation:** Use high-resolution timer, tune tickless kernel

2. **Context Switch Overhead**
   - Each sample wakes sleeping readers
   - Context switch: ~5-10 μs
   - At 10 kHz: 50-100% CPU just for scheduling
   - **Mitigation:** Batch wakeups, use circular buffer with watermark

3. **Cache Thrashing**
   - Ring buffer bounces between CPU cores
   - Lock contention increases
   - **Mitigation:** Per-CPU buffers, lock-free ring buffer

4. **Memory Bandwidth**
   - 10 kHz × 16 bytes = 160 KB/s (negligible)
   - Not a bottleneck

5. **User-Space Processing**
   - CLI can't process 10K samples/sec in Python
   - **Mitigation:** C implementation, batch reads

**Conclusion:** Current design good for up to ~1 kHz. Beyond that, need architectural changes (batching, lock-free, per-CPU).

---

## Security Considerations

### Input Validation

**All user inputs validated:**
- Sysfs writes: Range checks on sampling_ms, threshold_mC
- Invalid values: Return `-EINVAL`
- String mode: Validate against enum

### Memory Safety

**Kernel-User Boundary:**
- Always use `copy_to_user()` / `copy_from_user()`
- Check return values
- Handle partial copies
- Validate buffer sizes

**Resource Limits:**
- Ring buffer size fixed (no dynamic allocation in hot path)
- No unbounded loops
- Timer period bounded

### Permissions

**Device Node:** `/dev/simtemp` (mode 0666)
- All users can read
- Useful for monitoring without root

**Sysfs Attributes:** (mode 0644)
- All users can read
- Only root can write (configure)

### Denial of Service

**Protections:**
- Minimum sampling period (1 ms) prevents excessive CPU usage
- Ring buffer bounded (no memory exhaustion)
- No dynamic allocation in timer context

**Unprotected:**
- Rapid configuration changes (could add rate limiting)
- Multiple concurrent readers (acceptable for demo)

---

## CLI Application Design

### Overview

The Python CLI application (`simtemp_cli.py`) provides a user-friendly interface to the kernel module using the **Click framework**.

**Architecture:**
```
simtemp_cli.py (Click commands)
       ↓
simtemp_device.py (Device abstraction)
       ↓
/dev/simtemp + /sys/class/misc/simtemp/
```

### Module: simtemp_device.py

**Low-level device interface providing:**

1. **TemperatureSample Class**:
   ```python
   @dataclass
   class TemperatureSample:
       timestamp_ns: int
       temp_mC: int
       flags: int

       @property
       def temp_celsius(self) -> float

       @property
       def is_threshold_crossed(self) -> bool
   ```

2. **SimTempDevice Class**:
   - Binary protocol parsing (`struct.unpack("=QiI", ...)`)
   - Context manager for resource management
   - Poll/select integration
   - Sysfs attribute read/write helpers

### Module: simtemp_cli.py

**Five Click commands:**

1. **info**: Display device status
   - Shows /dev/simtemp availability
   - Shows sysfs attributes
   - Current configuration

2. **monitor**: Real-time temperature monitoring
   - Color-coded output (blue=normal, yellow=threshold)
   - Configurable sample count or duration
   - Ctrl+C graceful exit

3. **config**: Runtime configuration via sysfs
   - `--sampling`: Set sampling period (ms)
   - `--threshold`: Set alert threshold (°C)
   - `--mode`: Set temperature mode
   - `--show`: Display current config

4. **stats**: Display statistics
   - Parses /sys/class/misc/simtemp/stats
   - Shows counters and alerts

5. **test**: Automated test suite (CRITICAL REQUIREMENT)
   - 6 comprehensive tests
   - Exit code 0 on success, 1 on failure
   - Tests: config, modes, reading, monitoring, stats, non-blocking

### Test Mode Details

**Six Test Cases:**

1. **Sysfs Configuration**
   - Read/write all attributes
   - Validate changes applied

2. **Temperature Modes**
   - Switch between normal/noisy/ramp
   - Verify mode changes

3. **Device Reading**
   - Open /dev/simtemp
   - Parse binary samples
   - Validate structure

4. **Continuous Monitoring**
   - Read multiple samples
   - Verify timestamp ordering
   - Check temperature ranges

5. **Statistics Verification**
   - Read stats before/after operations
   - Verify counters increment

6. **Non-blocking Mode**
   - Open with O_NONBLOCK
   - Test -EAGAIN handling
   - Verify no blocking

**Exit Codes:**
- `0`: All tests passed
- `1`: One or more tests failed

---

## Testing Infrastructure

### Automated Kernel Tests

**Script:** `scripts/test_module.sh`

**11 Test Cases:**
1. Module file exists and has correct size
2. Module not already loaded (clean state)
3. Module loads successfully
4. Module appears in lsmod
5. `/dev/simtemp` character device created
6. `/sys/class/misc/simtemp/` directory created
7. All 4 sysfs attributes present
8. Sysfs attributes readable
9. Sysfs attributes writable
10. No kernel errors in dmesg
11. Device can be read (16-byte sample)

**Output:** Color-coded pass/fail with summary

### Testing Documentation

**Files Created:**
- `TESTING_GUIDE.md`: Complete manual testing procedures
- `TEST_NOW.sh`: Interactive test launcher
- `INTERACTIVE_TEST_SESSION.md`: Step-by-step walkthrough
- `QUICK_TEST_CARD.txt`: Quick reference

**Testing Workflow:**
1. Build kernel module
2. Run automated kernel tests
3. Install CLI dependencies
4. Run CLI test suite
5. Verify all tests pass
6. Document results

---

## Future Improvements

1. **Lock-Free Ring Buffer:** Reduce contention at high rates
2. **Per-CPU Statistics:** Avoid false sharing
3. **ioctl Interface:** Batch configuration changes atomically
4. **Netlink Interface:** Push events to user space
5. **DMA Simulation:** Emulate hardware DMA transfers
6. **Trace Points:** ftrace integration for debugging
7. **Thermal Framework:** Integrate with Linux thermal subsystem

---

**Last Updated:** 2025-10-24 - Phase 6 Complete (Testing Infrastructure Ready)

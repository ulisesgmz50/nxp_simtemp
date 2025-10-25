/* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
/*
 * NXP SimTemp - Virtual Temperature Sensor Driver
 * UAPI header - User-Kernel interface definitions
 *
 * This file can be used by both kernel and user-space applications
 *
 * Copyright (C) 2025 NXP Semiconductors
 */

#ifndef _UAPI_NXP_SIMTEMP_H
#define _UAPI_NXP_SIMTEMP_H

#include <linux/types.h>

/**
 * struct simtemp_sample - Binary sample structure returned by read()
 * @timestamp_ns: Monotonic timestamp in nanoseconds (from ktime_get_ns())
 * @temp_mC: Temperature in milli-degrees Celsius (e.g., 44123 = 44.123°C)
 * @flags: Event flags (see SIMTEMP_FLAG_* definitions)
 *
 * This structure is returned by read() from /dev/simtemp.
 * Size: 16 bytes (8 + 4 + 4)
 */
struct simtemp_sample {
	__u64 timestamp_ns;
	__s32 temp_mC;
	__u32 flags;
} __attribute__((packed));

/**
 * Event flags for simtemp_sample.flags
 */
#define SIMTEMP_FLAG_NEW_SAMPLE		(1 << 0)  /* New sample available */
#define SIMTEMP_FLAG_THRESHOLD_CROSSED	(1 << 1)  /* Temperature exceeded threshold */

/**
 * Device path
 */
#define SIMTEMP_DEVICE_PATH	"/dev/simtemp"

/**
 * Sysfs attributes paths (relative to /sys/class/misc/simtemp/)
 */
#define SIMTEMP_ATTR_SAMPLING_MS	"sampling_ms"
#define SIMTEMP_ATTR_THRESHOLD_MC	"threshold_mC"
#define SIMTEMP_ATTR_MODE		"mode"
#define SIMTEMP_ATTR_STATS		"stats"

/**
 * Mode strings for sysfs 'mode' attribute
 */
#define SIMTEMP_MODE_STR_NORMAL		"normal"
#define SIMTEMP_MODE_STR_NOISY		"noisy"
#define SIMTEMP_MODE_STR_RAMP		"ramp"

/**
 * Configuration limits
 */
#define SIMTEMP_SAMPLING_MS_MIN		1	/* 1 ms minimum */
#define SIMTEMP_SAMPLING_MS_MAX		10000	/* 10 seconds maximum */
#define SIMTEMP_THRESHOLD_MC_MIN	-40000	/* -40°C minimum */
#define SIMTEMP_THRESHOLD_MC_MAX	125000	/* 125°C maximum */

#endif /* _UAPI_NXP_SIMTEMP_H */

/* SPDX-License-Identifier: GPL-2.0 */
/*
 * NXP SimTemp - Virtual Temperature Sensor Driver
 * Internal header file
 *
 * Copyright (C) 2025 NXP Semiconductors
 */

#ifndef _NXP_SIMTEMP_H
#define _NXP_SIMTEMP_H

#include <linux/types.h>
#include <linux/device.h>
#include <linux/cdev.h>
#include <linux/miscdevice.h>
#include <linux/hrtimer.h>
#include <linux/spinlock.h>
#include <linux/mutex.h>
#include <linux/wait.h>
#include <linux/platform_device.h>

#include "nxp_simtemp_ioctl.h"

/* Driver name and version */
#define DRIVER_NAME		"nxp_simtemp"
#define DRIVER_VERSION		"1.0"
#define DRIVER_DESC		"NXP Virtual Temperature Sensor"

/* Default configuration values */
#define DEFAULT_SAMPLING_MS	100
#define DEFAULT_THRESHOLD_MC	45000	/* 45.0°C in milli-Celsius */
#define DEFAULT_MODE		SIMTEMP_MODE_NORMAL

/* Ring buffer size (must be power of 2 for efficiency) */
#define RING_BUFFER_SIZE	64
#define RING_BUFFER_MASK	(RING_BUFFER_SIZE - 1)

/* Temperature generation modes */
enum simtemp_mode {
	SIMTEMP_MODE_NORMAL = 0,	/* Stable with small variations */
	SIMTEMP_MODE_NOISY,		/* Large random variations */
	SIMTEMP_MODE_RAMP,		/* Linear ramp up/down */
};

/* Statistics counters */
struct simtemp_stats {
	u64 total_samples;		/* Total samples generated */
	u64 threshold_alerts;		/* Times threshold was crossed */
	u64 read_count;			/* Number of read() calls */
	u64 poll_count;			/* Number of poll() calls */
	u32 last_error;			/* Last error code */
};

/* Ring buffer for storing samples */
struct simtemp_ringbuf {
	struct simtemp_sample buffer[RING_BUFFER_SIZE];
	unsigned int head;		/* Write position */
	unsigned int tail;		/* Read position */
	spinlock_t lock;		/* Protects buffer access */
};

/* Main device structure */
struct simtemp_device {
	/* Platform device */
	struct platform_device *pdev;

	/* Character device */
	struct miscdevice miscdev;

	/* Timer for periodic sampling */
	struct hrtimer timer;
	ktime_t sampling_period;

	/* Ring buffer */
	struct simtemp_ringbuf ringbuf;

	/* Wait queue for blocking reads */
	wait_queue_head_t wait_queue;

	/* Configuration (protected by config_lock) */
	struct mutex config_lock;
	u32 sampling_ms;
	s32 threshold_mC;
	enum simtemp_mode mode;

	/* Temperature generation state */
	s32 current_temp_mC;
	bool ramp_direction;		/* true = up, false = down */

	/* Statistics */
	struct simtemp_stats stats;

	/* Flags */
	bool threshold_crossed;
	bool device_open;
};

/* Function declarations */

/* Core functions (nxp_simtemp.c) - all static, no external declarations needed */

/* Temperature generation - all static in .c file */

/* Ring buffer operations */
void simtemp_ringbuf_init(struct simtemp_ringbuf *rb);
int simtemp_ringbuf_put(struct simtemp_ringbuf *rb, struct simtemp_sample *sample);
int simtemp_ringbuf_get(struct simtemp_ringbuf *rb, struct simtemp_sample *sample);
bool simtemp_ringbuf_empty(struct simtemp_ringbuf *rb);
unsigned int simtemp_ringbuf_count(struct simtemp_ringbuf *rb);

/* File operations - all static, no external declarations needed */

/* Sysfs attributes - static in .c file, no external declaration needed */

#endif /* _NXP_SIMTEMP_H */

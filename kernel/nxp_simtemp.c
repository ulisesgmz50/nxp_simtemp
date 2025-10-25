// SPDX-License-Identifier: GPL-2.0
/*
 * NXP SimTemp - Virtual Temperature Sensor Driver
 * Main implementation file
 *
 * Copyright (C) 2025 NXP Semiconductors
 * Author: NXP Candidate
 *
 * This driver simulates a hardware temperature sensor for demonstration
 * and testing purposes. It generates periodic temperature samples and
 * exposes them to user space via character device and sysfs interfaces.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/of_device.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/poll.h>
#include <linux/fs.h>
#include <linux/random.h>

#include "nxp_simtemp.h"

/* Module metadata */
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Ulises Mauricio Gomez Villa");
MODULE_DESCRIPTION(DRIVER_DESC);
MODULE_VERSION(DRIVER_VERSION);

/* Global device pointer (for single instance) */
static struct simtemp_device *g_simtemp_dev;

/* Platform device for testing (when no Device Tree) */
static struct platform_device *g_pdev;

/* Forward declarations */
static int simtemp_probe(struct platform_device *pdev);
static void simtemp_remove(struct platform_device *pdev);
static enum hrtimer_restart simtemp_timer_callback(struct hrtimer *timer);
static s32 simtemp_generate_temperature(struct simtemp_device *dev);

/*
 * File operations: open()
 */
static int simtemp_open(struct inode *inode, struct file *filp)
{
	struct simtemp_device *dev;

	/* Get device from miscdevice */
	dev = container_of(filp->private_data, struct simtemp_device, miscdev);
	filp->private_data = dev;

	dev->device_open = true;

	pr_debug("%s: Device opened\n", DRIVER_NAME);
	return 0;
}

/*
 * File operations: release()
 */
static int simtemp_release(struct inode *inode, struct file *filp)
{
	struct simtemp_device *dev = filp->private_data;

	dev->device_open = false;

	pr_debug("%s: Device closed\n", DRIVER_NAME);
	return 0;
}

/*
 * File operations: read()
 * Returns one binary sample structure to userspace
 */
static ssize_t simtemp_read(struct file *filp, char __user *buf,
			     size_t count, loff_t *f_pos)
{
	struct simtemp_device *dev = filp->private_data;
	struct simtemp_sample sample;
	unsigned long flags;
	int ret;

	/* Validate buffer size */
	if (count < sizeof(struct simtemp_sample)) {
		pr_debug("%s: read() called with insufficient buffer size\n", DRIVER_NAME);
		return -EINVAL;
	}

	/*
	 * Wait for data to be available
	 * If buffer is empty and file opened in blocking mode, sleep until data arrives
	 */
	if (filp->f_flags & O_NONBLOCK) {
		/* Non-blocking mode: return immediately if no data */
		spin_lock_irqsave(&dev->ringbuf.lock, flags);
		ret = simtemp_ringbuf_get(&dev->ringbuf, &sample);
		spin_unlock_irqrestore(&dev->ringbuf.lock, flags);

		if (ret == -EAGAIN) {
			pr_debug("%s: Non-blocking read, no data available\n", DRIVER_NAME);
			return -EAGAIN;
		}
	} else {
		/* Blocking mode: wait for data to become available */
		ret = wait_event_interruptible(dev->wait_queue,
					       !simtemp_ringbuf_empty(&dev->ringbuf));
		if (ret) {
			/* Interrupted by signal */
			pr_debug("%s: Read interrupted by signal\n", DRIVER_NAME);
			return -ERESTARTSYS;
		}

		/* Data is available, get it from buffer */
		spin_lock_irqsave(&dev->ringbuf.lock, flags);
		ret = simtemp_ringbuf_get(&dev->ringbuf, &sample);
		spin_unlock_irqrestore(&dev->ringbuf.lock, flags);

		if (ret) {
			/* Should not happen as we checked empty condition above */
			pr_warn("%s: Unexpected empty buffer after wait\n", DRIVER_NAME);
			return -EAGAIN;
		}
	}

	/* Update statistics */
	dev->stats.read_count++;

	/* Copy sample to userspace */
	if (copy_to_user(buf, &sample, sizeof(sample))) {
		pr_err("%s: copy_to_user failed\n", DRIVER_NAME);
		return -EFAULT;
	}

	pr_debug("%s: Returned sample: temp=%dmC, flags=0x%x\n",
		 DRIVER_NAME, sample.temp_mC, sample.flags);

	return sizeof(sample);
}

/*
 * File operations: poll() - Wait for readable data or threshold events
 *
 * Returns event mask indicating:
 * - EPOLLIN | EPOLLRDNORM: New data available for reading
 * - EPOLLPRI: Threshold crossed (urgent notification)
 */
static __poll_t simtemp_poll(struct file *filp, struct poll_table_struct *wait)
{
	struct simtemp_device *dev = filp->private_data;
	__poll_t mask = 0;
	unsigned long flags;

	/* Add file to wait queue - kernel will wake us when data arrives */
	poll_wait(filp, &dev->wait_queue, wait);

	/* Update statistics */
	dev->stats.poll_count++;

	/* Check if data is available for reading */
	spin_lock_irqsave(&dev->ringbuf.lock, flags);
	if (!simtemp_ringbuf_empty(&dev->ringbuf)) {
		mask |= EPOLLIN | EPOLLRDNORM;
		pr_debug("%s: poll() - data available\n", DRIVER_NAME);
	}
	spin_unlock_irqrestore(&dev->ringbuf.lock, flags);

	/* Check for threshold crossing event (urgent notification) */
	if (dev->threshold_crossed) {
		mask |= EPOLLPRI;
		pr_debug("%s: poll() - threshold crossed\n", DRIVER_NAME);
	}

	/*
	 * If no events, the process will sleep on the wait queue
	 * and be woken by the timer when new data arrives
	 */
	if (!mask)
		pr_debug("%s: poll() - no events, will sleep\n", DRIVER_NAME);

	return mask;
}

/*
 * File operations structure
 */
static const struct file_operations simtemp_fops = {
	.owner		= THIS_MODULE,
	.open		= simtemp_open,
	.release	= simtemp_release,
	.read		= simtemp_read,
	.poll		= simtemp_poll,
	.llseek		= noop_llseek,
};

/*
 * Sysfs attribute: sampling_ms (RW)
 * Show current sampling period in milliseconds
 */
static ssize_t sampling_ms_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);

	return sysfs_emit(buf, "%u\n", sdev->sampling_ms);
}

/*
 * Sysfs attribute: sampling_ms (RW)
 * Update sampling period and restart timer with new period
 */
static ssize_t sampling_ms_store(struct device *dev,
				  struct device_attribute *attr,
				  const char *buf, size_t count)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);
	unsigned int val;
	int ret;

	ret = kstrtouint(buf, 10, &val);
	if (ret) {
		pr_warn("%s: Invalid sampling_ms value: %s\n", DRIVER_NAME, buf);
		return ret;
	}

	/* Validate range */
	if (val < SIMTEMP_SAMPLING_MS_MIN || val > SIMTEMP_SAMPLING_MS_MAX) {
		pr_warn("%s: sampling_ms out of range (%u-%u): %u\n",
			DRIVER_NAME, SIMTEMP_SAMPLING_MS_MIN, SIMTEMP_SAMPLING_MS_MAX, val);
		return -EINVAL;
	}

	mutex_lock(&sdev->config_lock);

	/* Update sampling period */
	sdev->sampling_ms = val;
	sdev->sampling_period = ms_to_ktime(val);

	/* Restart timer with new period */
	hrtimer_cancel(&sdev->timer);
	hrtimer_start(&sdev->timer, sdev->sampling_period, HRTIMER_MODE_REL);

	mutex_unlock(&sdev->config_lock);

	pr_info("%s: Sampling period changed to %u ms\n", DRIVER_NAME, val);
	return count;
}
static DEVICE_ATTR_RW(sampling_ms);

/*
 * Sysfs attribute: threshold_mC (RW)
 * Show current threshold in milli-Celsius
 */
static ssize_t threshold_mC_show(struct device *dev,
				  struct device_attribute *attr, char *buf)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);

	return sysfs_emit(buf, "%d\n", sdev->threshold_mC);
}

/*
 * Sysfs attribute: threshold_mC (RW)
 * Update alert threshold
 */
static ssize_t threshold_mC_store(struct device *dev,
				   struct device_attribute *attr,
				   const char *buf, size_t count)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);
	int val;
	int ret;

	ret = kstrtoint(buf, 10, &val);
	if (ret) {
		pr_warn("%s: Invalid threshold_mC value: %s\n", DRIVER_NAME, buf);
		return ret;
	}

	/* Validate range */
	if (val < SIMTEMP_THRESHOLD_MC_MIN || val > SIMTEMP_THRESHOLD_MC_MAX) {
		pr_warn("%s: threshold_mC out of range (%d-%d): %d\n",
			DRIVER_NAME, SIMTEMP_THRESHOLD_MC_MIN, SIMTEMP_THRESHOLD_MC_MAX, val);
		return -EINVAL;
	}

	mutex_lock(&sdev->config_lock);
	sdev->threshold_mC = val;
	mutex_unlock(&sdev->config_lock);

	pr_info("%s: Threshold changed to %d mC\n", DRIVER_NAME, val);
	return count;
}
static DEVICE_ATTR_RW(threshold_mC);

/*
 * Sysfs attribute: mode (RW)
 * Show current temperature generation mode
 */
static ssize_t mode_show(struct device *dev,
			  struct device_attribute *attr, char *buf)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);
	const char *mode_str;

	switch (sdev->mode) {
	case SIMTEMP_MODE_NORMAL:
		mode_str = "normal";
		break;
	case SIMTEMP_MODE_NOISY:
		mode_str = "noisy";
		break;
	case SIMTEMP_MODE_RAMP:
		mode_str = "ramp";
		break;
	default:
		mode_str = "unknown";
		break;
	}

	return sysfs_emit(buf, "%s\n", mode_str);
}

/*
 * Sysfs attribute: mode (RW)
 * Update temperature generation mode
 */
static ssize_t mode_store(struct device *dev,
			   struct device_attribute *attr,
			   const char *buf, size_t count)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);
	enum simtemp_mode new_mode;

	/* Parse mode string */
	if (sysfs_streq(buf, "normal")) {
		new_mode = SIMTEMP_MODE_NORMAL;
	} else if (sysfs_streq(buf, "noisy")) {
		new_mode = SIMTEMP_MODE_NOISY;
	} else if (sysfs_streq(buf, "ramp")) {
		new_mode = SIMTEMP_MODE_RAMP;
	} else {
		pr_warn("%s: Invalid mode: %s (use: normal, noisy, ramp)\n",
			DRIVER_NAME, buf);
		return -EINVAL;
	}

	mutex_lock(&sdev->config_lock);
	sdev->mode = new_mode;
	mutex_unlock(&sdev->config_lock);

	pr_info("%s: Mode changed to %s\n", DRIVER_NAME, buf);
	return count;
}
static DEVICE_ATTR_RW(mode);

/*
 * Sysfs attribute: stats (RO)
 * Display statistics counters
 */
static ssize_t stats_show(struct device *dev,
			   struct device_attribute *attr, char *buf)
{
	struct simtemp_device *sdev = dev_get_drvdata(dev);

	return sysfs_emit(buf,
		"total_samples: %llu\n"
		"threshold_alerts: %llu\n"
		"read_count: %llu\n"
		"poll_count: %llu\n",
		sdev->stats.total_samples,
		sdev->stats.threshold_alerts,
		sdev->stats.read_count,
		sdev->stats.poll_count);
}
static DEVICE_ATTR_RO(stats);

/*
 * Sysfs attribute group
 */
static struct attribute *simtemp_attrs[] = {
	&dev_attr_sampling_ms.attr,
	&dev_attr_threshold_mC.attr,
	&dev_attr_mode.attr,
	&dev_attr_stats.attr,
	NULL
};

static const struct attribute_group simtemp_attr_group = {
	.attrs = simtemp_attrs,
};

/*
 * Platform driver probe function
 * Called when device tree node matches our compatible string
 */
static int simtemp_probe(struct platform_device *pdev)
{
	struct simtemp_device *dev;
	struct device_node *np = pdev->dev.of_node;
	int ret;
	u32 val;

	pr_info("%s: Probing NXP SimTemp device\n", DRIVER_NAME);

	/* Allocate device structure */
	dev = devm_kzalloc(&pdev->dev, sizeof(*dev), GFP_KERNEL);
	if (!dev)
		return -ENOMEM;

	dev->pdev = pdev;
	platform_set_drvdata(pdev, dev);
	g_simtemp_dev = dev;

	/* Parse Device Tree properties with defaults */
	dev->sampling_ms = DEFAULT_SAMPLING_MS;
	if (np && of_property_read_u32(np, "sampling-ms", &val) == 0) {
		if (val >= SIMTEMP_SAMPLING_MS_MIN && val <= SIMTEMP_SAMPLING_MS_MAX) {
			dev->sampling_ms = val;
			pr_info("%s: DT sampling-ms = %u\n", DRIVER_NAME, val);
		} else {
			pr_warn("%s: DT sampling-ms out of range, using default\n", DRIVER_NAME);
		}
	}

	dev->threshold_mC = DEFAULT_THRESHOLD_MC;
	if (np && of_property_read_u32(np, "threshold-mC", &val) == 0) {
		dev->threshold_mC = (s32)val;
		pr_info("%s: DT threshold-mC = %d\n", DRIVER_NAME, dev->threshold_mC);
	}

	dev->mode = DEFAULT_MODE;
	dev->current_temp_mC = 40000; /* Start at 40°C */
	dev->ramp_direction = true;   /* Ramp up initially */

	/* Initialize synchronization primitives */
	mutex_init(&dev->config_lock);
	init_waitqueue_head(&dev->wait_queue);

	/* Initialize ring buffer */
	simtemp_ringbuf_init(&dev->ringbuf);

	/* Initialize timer (will be started after char device registration) */
	hrtimer_init(&dev->timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
	dev->timer.function = simtemp_timer_callback;
	dev->sampling_period = ms_to_ktime(dev->sampling_ms);

	/* Register misc character device */
	dev->miscdev.minor = MISC_DYNAMIC_MINOR;
	dev->miscdev.name = "simtemp";
	dev->miscdev.fops = &simtemp_fops;
	dev->miscdev.parent = &pdev->dev;
	dev->miscdev.mode = 0666;  /* Read/write for all users */

	ret = misc_register(&dev->miscdev);
	if (ret) {
		pr_err("%s: Failed to register misc device: %d\n", DRIVER_NAME, ret);
		return ret;
	}

	/* Set driver data for sysfs access */
	dev_set_drvdata(dev->miscdev.this_device, dev);

	pr_info("%s: Device initialized successfully\n", DRIVER_NAME);
	pr_info("%s: Configuration: sampling=%ums, threshold=%dmC, mode=%d\n",
		DRIVER_NAME, dev->sampling_ms, dev->threshold_mC, dev->mode);
	pr_info("%s: Character device /dev/simtemp created\n", DRIVER_NAME);

	/* Create sysfs attributes */
	ret = sysfs_create_group(&dev->miscdev.this_device->kobj, &simtemp_attr_group);
	if (ret) {
		pr_err("%s: Failed to create sysfs attributes: %d\n", DRIVER_NAME, ret);
		misc_deregister(&dev->miscdev);
		return ret;
	}
	pr_info("%s: Sysfs attributes created\n", DRIVER_NAME);

	/* Start the periodic timer */
	hrtimer_start(&dev->timer, dev->sampling_period, HRTIMER_MODE_REL);
	pr_info("%s: Sampling timer started (%u ms period)\n", DRIVER_NAME, dev->sampling_ms);

	return 0;
}

/*
 * Platform driver remove function
 * Called when module is unloaded
 */
static void simtemp_remove(struct platform_device *pdev)
{
	struct simtemp_device *dev = platform_get_drvdata(pdev);

	pr_info("%s: Removing device\n", DRIVER_NAME);

	/*
	 * Cancel timer first - critical to do before any other cleanup
	 * hrtimer_cancel() waits for callback to complete if running
	 */
	if (hrtimer_cancel(&dev->timer))
		pr_debug("%s: Timer was active, cancelled successfully\n", DRIVER_NAME);

	/* Wake any sleeping readers */
	wake_up_interruptible(&dev->wait_queue);

	/* Remove sysfs attributes */
	sysfs_remove_group(&dev->miscdev.this_device->kobj, &simtemp_attr_group);
	pr_info("%s: Sysfs attributes removed\n", DRIVER_NAME);

	/* Unregister character device */
	misc_deregister(&dev->miscdev);
	pr_info("%s: Character device /dev/simtemp removed\n", DRIVER_NAME);

	/* Log statistics before exit */
	pr_info("%s: Final statistics: samples=%llu, alerts=%llu, reads=%llu\n",
		DRIVER_NAME, dev->stats.total_samples, dev->stats.threshold_alerts,
		dev->stats.read_count);

	g_simtemp_dev = NULL;

	pr_info("%s: Device removed successfully\n", DRIVER_NAME);
}

/*
 * Ring buffer operations
 */
void simtemp_ringbuf_init(struct simtemp_ringbuf *rb)
{
	rb->head = 0;
	rb->tail = 0;
	spin_lock_init(&rb->lock);
	memset(rb->buffer, 0, sizeof(rb->buffer));
}

/*
 * Check if ring buffer is empty
 */
bool simtemp_ringbuf_empty(struct simtemp_ringbuf *rb)
{
	return rb->head == rb->tail;
}

/*
 * Get number of samples in ring buffer
 */
unsigned int simtemp_ringbuf_count(struct simtemp_ringbuf *rb)
{
	return (rb->head - rb->tail) & RING_BUFFER_MASK;
}

/*
 * Put a sample into the ring buffer
 * Returns 0 on success, -ENOSPC if buffer is full
 */
int simtemp_ringbuf_put(struct simtemp_ringbuf *rb, struct simtemp_sample *sample)
{
	unsigned int head;
	unsigned int next_head;

	head = rb->head;
	next_head = (head + 1) & RING_BUFFER_MASK;

	/* Check if buffer is full */
	if (next_head == rb->tail)
		return -ENOSPC;

	/* Copy sample to buffer */
	memcpy(&rb->buffer[head], sample, sizeof(*sample));

	/* Ensure sample is written before updating head */
	smp_wmb();

	rb->head = next_head;
	return 0;
}

/*
 * Get a sample from the ring buffer
 * Returns 0 on success, -EAGAIN if buffer is empty
 */
int simtemp_ringbuf_get(struct simtemp_ringbuf *rb, struct simtemp_sample *sample)
{
	unsigned int tail;

	/* Check if buffer is empty */
	if (simtemp_ringbuf_empty(rb))
		return -EAGAIN;

	tail = rb->tail;

	/* Copy sample from buffer */
	memcpy(sample, &rb->buffer[tail], sizeof(*sample));

	/* Ensure sample is read before updating tail */
	smp_rmb();

	rb->tail = (tail + 1) & RING_BUFFER_MASK;
	return 0;
}

/*
 * Generate temperature based on current mode
 * Returns temperature in milli-Celsius
 */
static s32 simtemp_generate_temperature(struct simtemp_device *dev)
{
	s32 temp_mC;
	u32 random;

	switch (dev->mode) {
	case SIMTEMP_MODE_NORMAL:
		/* Normal mode: 40-50°C with small variations (±2°C) */
		get_random_bytes(&random, sizeof(random));
		temp_mC = 45000 + ((s32)(random % 4000) - 2000);
		break;

	case SIMTEMP_MODE_NOISY:
		/* Noisy mode: 30-60°C with large random variations */
		get_random_bytes(&random, sizeof(random));
		temp_mC = 45000 + ((s32)(random % 30000) - 15000);
		if (temp_mC < 30000)
			temp_mC = 30000;
		if (temp_mC > 60000)
			temp_mC = 60000;
		break;

	case SIMTEMP_MODE_RAMP:
		/* Ramp mode: linear ramp between 30-70°C */
		if (dev->ramp_direction) {
			/* Ramping up */
			dev->current_temp_mC += 500; /* +0.5°C per sample */
			if (dev->current_temp_mC >= 70000) {
				dev->current_temp_mC = 70000;
				dev->ramp_direction = false; /* Start ramping down */
			}
		} else {
			/* Ramping down */
			dev->current_temp_mC -= 500; /* -0.5°C per sample */
			if (dev->current_temp_mC <= 30000) {
				dev->current_temp_mC = 30000;
				dev->ramp_direction = true; /* Start ramping up */
			}
		}
		temp_mC = dev->current_temp_mC;
		break;

	default:
		/* Fallback to normal mode */
		temp_mC = 45000;
		break;
	}

	return temp_mC;
}

/*
 * Timer callback - Called periodically to generate temperature samples
 * This runs in interrupt context, so must be fast and atomic
 */
static enum hrtimer_restart simtemp_timer_callback(struct hrtimer *timer)
{
	struct simtemp_device *dev = container_of(timer, struct simtemp_device, timer);
	struct simtemp_sample sample;
	unsigned long flags;
	bool threshold_crossed = false;
	s32 temp_mC;
	int ret;

	/* Generate temperature based on current mode */
	temp_mC = simtemp_generate_temperature(dev);

	/* Build sample structure */
	sample.timestamp_ns = ktime_get_ns();
	sample.temp_mC = temp_mC;
	sample.flags = SIMTEMP_FLAG_NEW_SAMPLE;

	/* Check threshold crossing */
	if (temp_mC > dev->threshold_mC) {
		if (!dev->threshold_crossed) {
			dev->threshold_crossed = true;
			threshold_crossed = true;
			sample.flags |= SIMTEMP_FLAG_THRESHOLD_CROSSED;
			dev->stats.threshold_alerts++;
		}
	} else {
		dev->threshold_crossed = false;
	}

	/* Add sample to ring buffer */
	spin_lock_irqsave(&dev->ringbuf.lock, flags);
	ret = simtemp_ringbuf_put(&dev->ringbuf, &sample);
	spin_unlock_irqrestore(&dev->ringbuf.lock, flags);

	if (ret) {
		/* Buffer full - oldest sample was dropped */
		pr_debug("%s: Ring buffer full, sample dropped\n", DRIVER_NAME);
	}

	/* Update statistics */
	dev->stats.total_samples++;

	/* Wake any sleeping readers (Phase 4 will fully implement wait queue) */
	wake_up_interruptible(&dev->wait_queue);

	/* Restart timer for next sample */
	hrtimer_forward_now(timer, dev->sampling_period);
	return HRTIMER_RESTART;
}

/*
 * Device Tree match table
 */
static const struct of_device_id simtemp_of_match[] = {
	{ .compatible = "nxp,simtemp", },
	{ /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, simtemp_of_match);

/*
 * Platform driver structure
 */
static struct platform_driver simtemp_platform_driver = {
	.probe = simtemp_probe,
	.remove = simtemp_remove,
	.driver = {
		.name = DRIVER_NAME,
		.of_match_table = simtemp_of_match,
	},
};

/*
 * Module initialization
 */
static int __init simtemp_init(void)
{
	int ret;

	pr_info("%s: Initializing NXP SimTemp driver v%s\n", DRIVER_NAME, DRIVER_VERSION);

	/* Register platform driver */
	ret = platform_driver_register(&simtemp_platform_driver);
	if (ret) {
		pr_err("%s: Failed to register platform driver: %d\n", DRIVER_NAME, ret);
		return ret;
	}

	/*
	 * Create a platform device for testing
	 * In production, this would come from Device Tree
	 */
	g_pdev = platform_device_register_simple(DRIVER_NAME, -1, NULL, 0);
	if (IS_ERR(g_pdev)) {
		ret = PTR_ERR(g_pdev);
		pr_err("%s: Failed to register platform device: %d\n", DRIVER_NAME, ret);
		platform_driver_unregister(&simtemp_platform_driver);
		return ret;
	}

	pr_info("%s: Driver registered successfully\n", DRIVER_NAME);
	return 0;
}

/*
 * Module cleanup
 */
static void __exit simtemp_exit(void)
{
	pr_info("%s: Exiting driver\n", DRIVER_NAME);

	/* Unregister platform device */
	if (g_pdev)
		platform_device_unregister(g_pdev);

	/* Unregister platform driver */
	platform_driver_unregister(&simtemp_platform_driver);

	pr_info("%s: Driver unregistered\n", DRIVER_NAME);
}

module_init(simtemp_init);
module_exit(simtemp_exit);

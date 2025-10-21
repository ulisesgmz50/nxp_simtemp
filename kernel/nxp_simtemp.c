#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/hrtimer.h>
#include <linux/workqueue.h>
#include <linux/random.h>
#include <linux/wait.h>
#include <linux/poll.h>
#include <linux/timekeeping.h>
#include <linux/sysfs.h>
#include <linux/kobject.h>
#include <linux/time64.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Tu Nombre");
MODULE_DESCRIPTION("Módulo de temperatura con read(), poll(), sysfs y timestamp");

// Variables configurables
static int update_interval_ms = 1000;
static int temp_threshold = 35;

// Variables internas
static int current_temp = 0;
static int temp_ready = 0;
static char temp_buffer[128];

// Temporizador y trabajo
static struct hrtimer temp_timer;
static struct workqueue_struct *temp_wq;
static struct work_struct temp_work;

// Dispositivo de carácter
static struct miscdevice temp_dev;

// Cola de espera para poll/epoll
static DECLARE_WAIT_QUEUE_HEAD(temp_wait_queue);

// Objeto sysfs
static struct kobject *temp_kobj;

// Simula temperatura entre 20 y 45
static int simulate_temperature(void) {
    u32 rand;
    get_random_bytes(&rand, sizeof(rand));
    return 20 + (rand % 26);
}

// Función de trabajo: actualiza temperatura y timestamp
static void temp_work_func(struct work_struct *work) {
    struct timespec64 ts;
    struct tm tm;

    current_temp = simulate_temperature();
    ktime_get_real_ts64(&ts);
    time64_to_tm(ts.tv_sec, 0, &tm);

    snprintf(temp_buffer, sizeof(temp_buffer),
             "Temp: %d°C Timestamp: %04ld-%02d-%02d %02d:%02d:%02d\n",
             current_temp,
             tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
             tm.tm_hour, tm.tm_min, tm.tm_sec);

    if (current_temp > temp_threshold) {
        pr_warn("⚠️ ALERTA: Temperatura alta: %d°C (umbral: %d°C)\n", current_temp, temp_threshold);
    } else {
        pr_info("Temperatura actual: %d°C\n", current_temp);
    }

    temp_ready = 1;
    wake_up_interruptible(&temp_wait_queue);
}

// Callback del temporizador
static enum hrtimer_restart temp_timer_callback(struct hrtimer *timer) {
    queue_work(temp_wq, &temp_work);
    hrtimer_forward_now(timer, ms_to_ktime(update_interval_ms));
    return HRTIMER_RESTART;
}

// Función read()
static ssize_t temp_read(struct file *file, char __user *buf, size_t count, loff_t *ppos) {
    if (!temp_ready)
        return 0;

    temp_ready = 0;
    return simple_read_from_buffer(buf, count, ppos, temp_buffer, strlen(temp_buffer));
}

// Función poll()
static __poll_t temp_poll(struct file *file, struct poll_table_struct *wait) {
    poll_wait(file, &temp_wait_queue, wait);
    return temp_ready ? POLLIN | POLLRDNORM : 0;
}

// Operaciones del dispositivo
static struct file_operations temp_fops = {
    .owner = THIS_MODULE,
    .read = temp_read,
    .poll = temp_poll,
};

// Atributos sysfs: interval_ms
static ssize_t interval_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf) {
    return sprintf(buf, "%d\n", update_interval_ms);
}

static ssize_t interval_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count) {
    int val;
    if (kstrtoint(buf, 10, &val) == 0 && val > 0) {
        update_interval_ms = val;
        pr_info("Nuevo intervalo de actualización: %d ms\n", update_interval_ms);
    }
    return count;
}

// Atributos sysfs: threshold
static ssize_t threshold_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf) {
    return sprintf(buf, "%d\n", temp_threshold);
}

static ssize_t threshold_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count) {
    int val;
    if (kstrtoint(buf, 10, &val) == 0) {
        temp_threshold = val;
        pr_info("Nuevo umbral de alerta: %d°C\n", temp_threshold);
    }
    return count;
}

// Definición de atributos sysfs
static struct kobj_attribute interval_attr = __ATTR(interval_ms, 0664, interval_show, interval_store);
static struct kobj_attribute threshold_attr = __ATTR(threshold, 0664, threshold_show, threshold_store);

static struct attribute *attrs[] = {
    &interval_attr.attr,
    &threshold_attr.attr,
    NULL,
};

static struct attribute_group attr_group = {
    .attrs = attrs,
};

// Inicialización del módulo
static int __init temp_module_init(void) {
    int ret;

    // Registro del dispositivo
    temp_dev.minor = MISC_DYNAMIC_MINOR;
    temp_dev.name = "fake_temp";
    temp_dev.fops = &temp_fops;
    temp_dev.mode = 0666;

    ret = misc_register(&temp_dev);
    if (ret)
        return ret;

    // sysfs
    temp_kobj = kobject_create_and_add("fake_temp", kernel_kobj);
    if (!temp_kobj)
        return -ENOMEM;

    ret = sysfs_create_group(temp_kobj, &attr_group);
    if (ret)
        kobject_put(temp_kobj);

    // Temporizador y trabajo
    INIT_WORK(&temp_work, temp_work_func);
    temp_wq = create_singlethread_workqueue("temp_wq");

    hrtimer_init(&temp_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
    temp_timer.function = temp_timer_callback;
    hrtimer_start(&temp_timer, ms_to_ktime(update_interval_ms), HRTIMER_MODE_REL);

    pr_info("Módulo de temperatura cargado\n");
    return 0;
}

// Finalización del módulo
static void __exit temp_module_exit(void) {
    hrtimer_cancel(&temp_timer);
    flush_workqueue(temp_wq);
    destroy_workqueue(temp_wq);
    misc_deregister(&temp_dev);
    kobject_put(temp_kobj);
    pr_info("Módulo de temperatura descargado\n");
}

module_init(temp_module_init);
module_exit(temp_module_exit);

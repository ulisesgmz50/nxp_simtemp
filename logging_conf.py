import logging.config

logging_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored_console": {
            "class": "coloredlogs.ColoredFormatter",
            "format": "[%(asctime)s][%(levelname)s] - %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S",
        },
        "plain_text": {
            "format": "[%(asctime)s][%(levelname)s] - %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "colored_console",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs.log",
            "level": "INFO",
            "formatter": "plain_text",
        },
    },
    "loggers": {
        "root": {"handlers": ["console", "file"], "level": "INFO"},
        "": {"handlers": ["console", "file"], "level": "INFO"},
        "logger_cfg": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "qualname": "logger_cfg",
            "propagate": False,
        },
    },
}

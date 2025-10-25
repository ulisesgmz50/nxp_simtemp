# SPDX-License-Identifier: GPL-2.0
# Makefile for nxp_simtemp kernel module

# Detect kernel build directory
KDIR ?= /lib/modules/$(shell uname -r)/build

# Use gcc wrapper to filter out unsupported flags
export HOSTCC := gcc
export CC := $(PWD)/gcc-wrapper.sh

# Module name
obj-m := nxp_simtemp.o

# Build flags
ccflags-y := -DDEBUG

# Default target
all:
	@echo "Building nxp_simtemp kernel module..."
	$(MAKE) -C $(KDIR) M=$(PWD) CC=$(CC) modules

# Clean target
clean:
	@echo "Cleaning build artifacts..."
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f Module.symvers modules.order

# Install target
install:
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install

# Help target
help:
	@echo "NXP SimTemp Kernel Module Build System"
	@echo ""
	@echo "Targets:"
	@echo "  all     - Build the kernel module (default)"
	@echo "  clean   - Remove build artifacts"
	@echo "  install - Install the module to the system"
	@echo ""
	@echo "Variables:"
	@echo "  KDIR    - Kernel build directory (default: /lib/modules/\$$(uname -r)/build)"

.PHONY: all clean install help

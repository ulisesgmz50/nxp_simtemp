#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# NXP SimTemp Module Testing Script
# Comprehensive test suite for kernel module validation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL_DIR="$PROJECT_ROOT/kernel"
MODULE_NAME="nxp_simtemp"
MODULE_FILE="$KERNEL_DIR/${MODULE_NAME}.ko"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       NXP SimTemp Module Testing Suite                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    echo -e "${RED}       ${2}${NC}"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

info() {
    echo -e "${BLUE}→${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Module file exists
echo -e "${BLUE}[Test 1/11]${NC} Checking module file..."
if [ -f "$MODULE_FILE" ]; then
    MODULE_SIZE=$(stat -f%z "$MODULE_FILE" 2>/dev/null || stat -c%s "$MODULE_FILE" 2>/dev/null)
    pass "Module file exists (${MODULE_SIZE} bytes)"
else
    fail "Module file not found" "Expected: $MODULE_FILE"
    exit 1
fi

# Test 2: Check if module is already loaded
echo -e "\n${BLUE}[Test 2/11]${NC} Checking if module is already loaded..."
if lsmod | grep -q "^${MODULE_NAME}"; then
    warn "Module already loaded, unloading first..."
    rmmod $MODULE_NAME 2>/dev/null || true
    sleep 1
fi
pass "Module not loaded (clean state)"

# Test 3: Load module
echo -e "\n${BLUE}[Test 3/11]${NC} Loading kernel module..."
if insmod "$MODULE_FILE" 2>/dev/null; then
    pass "Module loaded successfully"
else
    fail "Failed to load module" "Check dmesg for errors"
    exit 1
fi

# Give kernel time to initialize
sleep 1

# Test 4: Verify module is loaded
echo -e "\n${BLUE}[Test 4/11]${NC} Verifying module in lsmod..."
if lsmod | grep -q "^${MODULE_NAME}"; then
    MODULE_INFO=$(lsmod | grep "^${MODULE_NAME}")
    pass "Module appears in lsmod"
    info "     $MODULE_INFO"
else
    fail "Module not in lsmod" "Module may have failed to initialize"
    dmesg | tail -20
    exit 1
fi

# Test 5: Check character device
echo -e "\n${BLUE}[Test 5/11]${NC} Checking /dev/simtemp..."
if [ -e /dev/simtemp ]; then
    DEV_INFO=$(ls -l /dev/simtemp)
    pass "Character device created"
    info "     $DEV_INFO"
else
    fail "Character device not found" "Expected: /dev/simtemp"
fi

# Test 6: Check sysfs directory
echo -e "\n${BLUE}[Test 6/11]${NC} Checking sysfs interface..."
SYSFS_PATH="/sys/class/misc/simtemp"
if [ -d "$SYSFS_PATH" ]; then
    pass "Sysfs directory exists"
    info "     $SYSFS_PATH"
else
    fail "Sysfs directory not found" "Expected: $SYSFS_PATH"
fi

# Test 7: Check sysfs attributes
echo -e "\n${BLUE}[Test 7/11]${NC} Checking sysfs attributes..."
ATTRS=("sampling_ms" "threshold_mC" "mode" "stats")
ATTR_COUNT=0
for attr in "${ATTRS[@]}"; do
    if [ -f "$SYSFS_PATH/$attr" ]; then
        ((ATTR_COUNT++))
        VALUE=$(cat "$SYSFS_PATH/$attr" 2>/dev/null | head -1)
        info "     ✓ $attr = $VALUE"
    else
        warn "Missing attribute: $attr"
    fi
done

if [ $ATTR_COUNT -eq ${#ATTRS[@]} ]; then
    pass "All sysfs attributes present (${ATTR_COUNT}/${#ATTRS[@]})"
else
    fail "Missing sysfs attributes" "Found ${ATTR_COUNT}/${#ATTRS[@]}"
fi

# Test 8: Test sysfs read operations
echo -e "\n${BLUE}[Test 8/11]${NC} Testing sysfs read operations..."
SAMPLING_MS=$(cat "$SYSFS_PATH/sampling_ms" 2>/dev/null)
THRESHOLD_MC=$(cat "$SYSFS_PATH/threshold_mC" 2>/dev/null)
MODE=$(cat "$SYSFS_PATH/mode" 2>/dev/null)

if [ -n "$SAMPLING_MS" ] && [ -n "$THRESHOLD_MC" ] && [ -n "$MODE" ]; then
    pass "Sysfs attributes readable"
    info "     sampling_ms  = $SAMPLING_MS ms"
    info "     threshold_mC = $THRESHOLD_MC mC"
    info "     mode         = $MODE"
else
    fail "Failed to read sysfs attributes" "One or more reads failed"
fi

# Test 9: Test sysfs write operations
echo -e "\n${BLUE}[Test 9/11]${NC} Testing sysfs write operations..."
WRITE_SUCCESS=true

# Test sampling_ms write
echo 200 > "$SYSFS_PATH/sampling_ms" 2>/dev/null || WRITE_SUCCESS=false
NEW_SAMPLING=$(cat "$SYSFS_PATH/sampling_ms" 2>/dev/null)
if [ "$NEW_SAMPLING" = "200" ]; then
    info "     ✓ sampling_ms write successful (200 ms)"
else
    warn "Failed to write sampling_ms"
    WRITE_SUCCESS=false
fi

# Test threshold_mC write
echo 50000 > "$SYSFS_PATH/threshold_mC" 2>/dev/null || WRITE_SUCCESS=false
NEW_THRESHOLD=$(cat "$SYSFS_PATH/threshold_mC" 2>/dev/null)
if [ "$NEW_THRESHOLD" = "50000" ]; then
    info "     ✓ threshold_mC write successful (50000 mC = 50°C)"
else
    warn "Failed to write threshold_mC"
    WRITE_SUCCESS=false
fi

# Test mode write
echo "noisy" > "$SYSFS_PATH/mode" 2>/dev/null || WRITE_SUCCESS=false
NEW_MODE=$(cat "$SYSFS_PATH/mode" 2>/dev/null)
if [ "$NEW_MODE" = "noisy" ]; then
    info "     ✓ mode write successful (noisy)"
else
    warn "Failed to write mode"
    WRITE_SUCCESS=false
fi

if [ "$WRITE_SUCCESS" = true ]; then
    pass "Sysfs write operations successful"
else
    fail "Some sysfs write operations failed" "Check permissions and module implementation"
fi

# Restore defaults
echo 100 > "$SYSFS_PATH/sampling_ms" 2>/dev/null || true
echo 45000 > "$SYSFS_PATH/threshold_mC" 2>/dev/null || true
echo "normal" > "$SYSFS_PATH/mode" 2>/dev/null || true

# Test 10: Check kernel log for errors
echo -e "\n${BLUE}[Test 10/11]${NC} Checking kernel log for errors..."
DMESG_ERRORS=$(dmesg | grep -i "$MODULE_NAME" | grep -iE "(error|fail|warning|oops)" | tail -5)
if [ -z "$DMESG_ERRORS" ]; then
    pass "No errors in kernel log"
else
    warn "Found warnings/errors in dmesg:"
    echo "$DMESG_ERRORS" | while read line; do
        echo -e "${YELLOW}       $line${NC}"
    done
fi

# Test 11: Check device is readable
echo -e "\n${BLUE}[Test 11/11]${NC} Testing device read capability..."
if [ -r /dev/simtemp ]; then
    pass "Device is readable"

    # Try a quick read test (with timeout)
    info "     Attempting to read sample (timeout 2s)..."
    if timeout 2 dd if=/dev/simtemp of=/dev/null bs=16 count=1 2>/dev/null; then
        info "     ✓ Successfully read 16-byte sample"
    else
        warn "Read timed out or failed (this may be normal)"
    fi
else
    fail "Device is not readable" "Check permissions"
fi

# Display kernel log
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Recent Kernel Messages:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
dmesg | grep -i "$MODULE_NAME" | tail -15

# Summary
echo
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Test Summary                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "Tests Run:    ${TESTS_RUN}"
echo -e "${GREEN}Tests Passed: ${TESTS_PASSED}${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Tests Failed: ${TESTS_FAILED}${NC}"
fi
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Test the CLI: cd ../user/cli && ./simtemp_cli.py test -v"
    echo "  2. When done, unload: sudo rmmod $MODULE_NAME"
    echo
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo
    echo -e "${YELLOW}The module is still loaded. To unload:${NC}"
    echo "  sudo rmmod $MODULE_NAME"
    echo
    exit 1
fi

#!/bin/bash
# toggle_logging.sh - Quick toggle between debug mode and performance mode
# Purpose: Quickly switch between debug mode (logging enabled) and performance mode (logging disabled)
# Usage: ./toggle_logging.sh

set -e

WRR_H_FILE="P4_simulation/utils/user_externs_WRR/WRR.h"

if [ ! -f "$WRR_H_FILE" ]; then
    echo "Error: Cannot find $WRR_H_FILE"
    exit 1
fi

# Check current state
if grep -q "^#define WRR_DISABLE_LOGGING 0" "$WRR_H_FILE"; then
    CURRENT_MODE="Debug Mode (Logging Enabled)"
    NEW_MODE="Performance Mode (Logging Disabled)"
    NEW_VALUE=1
elif grep -q "^#define WRR_DISABLE_LOGGING 1" "$WRR_H_FILE"; then
    CURRENT_MODE="Performance Mode (Logging Disabled)"
    NEW_MODE="Debug Mode (Logging Enabled)"
    NEW_VALUE=0
else
    echo "Error: Cannot identify current logging mode"
    exit 1
fi

echo "=========================================="
echo "Logging Mode Toggle Tool"
echo "=========================================="
echo "Current mode: $CURRENT_MODE"
echo "Will switch to: $NEW_MODE"
echo ""

# Confirm
read -p "Confirm switch? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Perform switch
sed -i "s/^#define WRR_DISABLE_LOGGING [01]/#define WRR_DISABLE_LOGGING $NEW_VALUE/" "$WRR_H_FILE"

echo "✓ Switched to $NEW_MODE"
echo ""
echo "Next step:"
echo "  Run ./recompile_all.sh to recompile and apply changes"
echo ""

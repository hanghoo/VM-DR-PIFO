#!/bin/bash
# WRR Module Quick Compilation Script (Compiles WRR.so Only)
# Purpose: Recompiles only WRR.so (for cases where only WRR.cpp is modified)
# Usage: ./recompile_wrr_only.sh

set -e  # Exit immediately upon encountering an error

echo "=========================================="
echo “Quickly compiling WRR.so use when only modifying WRR.cpp”
echo "=========================================="
echo ""

# Recompile WRR.so
echo "Recompiling WRR.so..."
cd ~/P4_simulation/utils/user_externs_WRR
make clean
make
if [ $? -eq 0 ]; then
    echo "✓ WRR.so compiled successfully"
    ls -lh WRR.so
    echo ""
    echo "Note: If WRR.h was modified, use recompile_all.sh for a full rebuild"
else
    echo "✗ WRR.so compilation failed"
    exit 1
fi

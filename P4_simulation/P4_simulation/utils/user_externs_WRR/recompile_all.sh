#!/bin/bash
# Complete WRR Module Compilation Script
# Purpose: Recompile WRR.so, simple_switch, and simple_switch_grpc
# Usage: ./recompile_all.sh

set -e  # Exit immediately upon encountering errors

echo "=========================================="
echo "Complete WRR Module Compilation Process"
echo "=========================================="
echo ""

# Step 1: Recompile WRR.so
echo "[1/3] Recompiling WRR.so..."
cd ~/P4_simulation/utils/user_externs_WRR
make clean
make
if [ $? -eq 0 ]; then
    echo "✓ WRR.so compiled successfully"
    ls -lh WRR.so
else
    echo "✗ WRR.so compilation failed"
    exit 1
fi

echo ""

# Step 2: Recompile simple_switch
echo "[2/3] Recompiling simple_switch..."
cd ~/behavioral-model/targets/simple_switch
make clean
make -j$(nproc)
if [ $? -eq 0 ]; then
    echo "✓ simple_switch compiled successfully"
    ls -lh simple_switch
else
    echo "✗ simple_switch compilation failed"
    exit 1
fi

echo ""

# Step 3: Recompile simple_switch_grpc
echo "[3/3] Recompiling simple_switch_grpc..."
cd ~/behavioral-model/targets/simple_switch_grpc
make clean
make -j$(nproc)
if [ $? -eq 0 ]; then
    echo "✓ simple_switch_grpc compiled successfully"
    ls -lh simple_switch_grpc
else
    echo "✗ simple_switch_grpc compilation failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Compilation complete! All outputs:"
echo "=========================================="
echo "WRR.so:"
ls -lh ~/P4_simulation/utils/user_externs_WRR/WRR.so
echo ""
echo "simple_switch:"
ls -lh ~/behavioral-model/targets/simple_switch/simple_switch
echo ""
echo "simple_switch_grpc:"
ls -lh ~/behavioral-model/targets/simple_switch_grpc/simple_switch_grpc
echo ""
echo "=========================================="
echo "Verification: Test if simple_switch_grpc runs"
echo "=========================================="
~/behavioral-model/targets/simple_switch_grpc/simple_switch_grpc --help | head -5
echo ""
echo "✓ All compilation and verification complete!"

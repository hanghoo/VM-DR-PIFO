#!/bin/bash
# Complete WRR Module Compilation Script
# Purpose: Recompile WRR.so, simple_switch, and simple_switch_grpc
# Usage: ./recompile_all.sh
# Principle: Minimize sudo usage - only use when necessary

echo "=========================================="
echo "WRR Module Compilation"
echo "=========================================="
echo ""

# Step 1: Recompile WRR.so
echo "[1/4] Compiling WRR.so..."
cd ~/P4_simulation/utils/user_externs_WRR
make clean && make || exit 1
echo "✓ WRR.so compiled"
echo ""

# Step 2: Build behavioral-model dependencies
echo "[2/4] Building behavioral-model dependencies..."
cd ~/behavioral-model/src/bm_runtime && make clean && make -j$(nproc)
cd ~/behavioral-model/src/bm_sim && make clean && make -j$(nproc)
cd ~/behavioral-model && make -j$(nproc) || echo "⚠ Warning: Some build issues"
echo "✓ Dependencies built"
echo ""

# Step 2.5: Install libraries to system (if previously installed)
if [ -f "/usr/local/lib/libbmall.so" ] || [ -d "/usr/local/include/bm" ]; then
    echo "[2.5/4] Installing libraries to system..."
    cd ~/behavioral-model
    make install >/dev/null 2>&1 || sudo make install >/dev/null 2>&1
    command -v ldconfig >/dev/null && (ldconfig 2>/dev/null || sudo ldconfig)
    echo "✓ Libraries installed"
    echo ""
fi

# Step 3: Recompile simple_switch
echo "[3/4] Compiling simple_switch..."
cd ~/behavioral-model/targets/simple_switch
make clean && rm -rf .libs && make -j$(nproc) || exit 1
[ -f "/usr/local/lib/libbmall.so" ] && (make install >/dev/null 2>&1 || sudo make install >/dev/null 2>&1)
echo "✓ simple_switch compiled"
echo ""

# Step 4: Recompile simple_switch_grpc
echo "[4/4] Compiling simple_switch_grpc..."
cd ~/behavioral-model/targets/simple_switch_grpc
make clean && make -j$(nproc) || exit 1
[ -f "/usr/local/lib/libbmall.so" ] && (make install >/dev/null 2>&1 || sudo make install >/dev/null 2>&1)
echo "✓ simple_switch_grpc compiled"

echo ""
echo "=========================================="
echo "Compilation complete!"
echo "=========================================="
ls -lh ~/P4_simulation/utils/user_externs_WRR/WRR.so
ls -lh ~/behavioral-model/targets/simple_switch/simple_switch
ls -lh ~/behavioral-model/targets/simple_switch_grpc/simple_switch_grpc
echo ""
echo "✓ All done! Restart your test to use new binaries."

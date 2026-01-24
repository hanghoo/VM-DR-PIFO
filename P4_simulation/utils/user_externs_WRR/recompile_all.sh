#!/bin/bash
# Complete WRR Module Compilation Script
# Purpose: Recompile WRR.so, simple_switch, and simple_switch_grpc
# Usage: ./recompile_all.sh
# Principle: Minimize sudo usage - only use when necessary

echo "=========================================="
echo "Complete WRR Module Compilation Process"
echo "=========================================="
echo ""

# Step 1: Recompile WRR.so
echo "[1/4] Recompiling WRR.so..."
cd ~/P4_simulation/utils/user_externs_WRR
make clean && make || exit 1
echo "✓ WRR.so compiled successfully"
ls -lh WRR.so
echo ""

# # Step 2: Build behavioral-model dependencies (if needed)
# echo "[2/4] Building behavioral-model dependencies..."
# cd ~/behavioral-model
# [ ! -f "Makefile" ] && [ -f "configure.ac" ] && ./autogen.sh && ./configure
# cd src/bm_runtime && make clean && make -j$(nproc)
# cd ../bm_sim && make clean && make -j$(nproc)
# cd ../.. && make -j$(nproc) || echo "⚠ Warning: Some build issues"
# # Install to system if previously installed
# if [ -f "/usr/local/lib/libbmall.so" ] || [ -d "/usr/local/include/bm" ]; then
#     make install >/dev/null 2>&1 || sudo make install >/dev/null 2>&1
#     command -v ldconfig >/dev/null && (ldconfig 2>/dev/null || sudo ldconfig)
# fi
# echo "✓ Dependencies built"
# echo ""

# Step 3: Recompile simple_switch
echo "[3/4] Recompiling simple_switch..."
cd ~/behavioral-model/targets/simple_switch
make clean && rm -rf .libs && make -j$(nproc) || exit 1
[ -f "/usr/local/lib/libbmall.so" ] && (make install >/dev/null 2>&1 || sudo make install >/dev/null 2>&1)
echo "✓ simple_switch compiled successfully"
ls -lh simple_switch
echo ""

# Step 4: Recompile simple_switch_grpc
echo "[4/4] Recompiling simple_switch_grpc..."
cd ~/behavioral-model/targets/simple_switch_grpc
make clean && make -j$(nproc) || exit 1
[ -f "/usr/local/lib/libbmall.so" ] && (make install >/dev/null 2>&1 || sudo make install >/dev/null 2>&1)
command -v ldconfig >/dev/null && (ldconfig 2>/dev/null || sudo ldconfig)
echo "✓ simple_switch_grpc compiled successfully"
ls -lh simple_switch_grpc
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
echo "✓ All compilation complete!"

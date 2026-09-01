#!/usr/bin/env bash
# Portable ARM GCC + make under $HOME/tools (no admin install).
export PATH="$HOME/tools/xpack-arm-none-eabi-gcc-13.3.1-1.1/bin:$HOME/tools/xpack-windows-build-tools-4.4.1-3/bin:$PATH"
echo "arm-none-eabi-gcc: $(command -v arm-none-eabi-gcc || echo missing)"
echo "make: $(command -v make || echo missing)"

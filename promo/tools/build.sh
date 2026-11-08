#!/bin/zsh
# Builds the window recorder (ScreenCaptureKit, macOS 12.3 or later): promo/tools/skgrab
cd "$(dirname "$0")" && swiftc -O skgrab.swift -o skgrab && echo "built $(pwd)/skgrab"

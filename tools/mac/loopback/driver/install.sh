#!/bin/bash

# Configuration
DRIVER_NAME="LedFx"
INSTALL_PATH="/Library/Audio/Plug-Ins/HAL"

# Check if driver exists
if [ ! -d "$DRIVER_NAME.driver" ]; then
  echo "❌ Error: $DRIVER_NAME.driver not found. Run ./build.sh first."
  exit 1
fi

# Install driver
echo "Installing $DRIVER_NAME.driver to $INSTALL_PATH..."
sudo rm -rf "$INSTALL_PATH/$DRIVER_NAME.driver"
sudo cp -R "$DRIVER_NAME.driver" "$INSTALL_PATH/"

# Restart CoreAudio
echo "Restarting CoreAudio..."
sudo killall -9 coreaudiod

echo ""
echo "✅ $DRIVER_NAME.driver installed successfully"
echo "   Check Audio MIDI Setup to see the driver"

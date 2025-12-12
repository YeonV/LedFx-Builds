#!/bin/bash

# Configuration
DRIVER_NAME="LedFx"
BUNDLE_ID="audio.blade.BlackHole"
ICON="LedFx.icns"
DEVICE_NAME="LedFx"

# Build
xcodebuild \
  -project LedFx.xcodeproj \
  -configuration Release \
  PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID" \
  PRODUCT_NAME="$DRIVER_NAME" \
  GCC_PREPROCESSOR_DEFINITIONS='$GCC_PREPROCESSOR_DEFINITIONS
  kDriver_Name=\"'$DRIVER_NAME'\"
  kPlugIn_BundleID=\"'$BUNDLE_ID'\"
  kPlugIn_Icon=\"'$ICON'\"
  kDevice_Name=\"'$DEVICE_NAME'\"'

# Move driver to root
mv build/Release/$DRIVER_NAME.driver .

echo ""
echo "✅ Build completed: $DRIVER_NAME.driver"

#!/bin/bash
# Disable LedFx SSL Setup Script for Linux
# This script removes HTTPS configuration for LedFx
# Must be run with sudo

set -e

SSL_DIR="$HOME/.ledfx/ssl"

# Step 1: Remove certificate from system trust store (distro-specific)
if [ -f "/usr/local/share/ca-certificates/ledfx.crt" ]; then
  # Debian/Ubuntu
  sudo rm -f /usr/local/share/ca-certificates/ledfx.crt
  sudo update-ca-certificates --fresh
elif [ -f "/etc/pki/ca-trust/source/anchors/ledfx.crt" ]; then
  # RHEL/Fedora/CentOS
  sudo rm -f /etc/pki/ca-trust/source/anchors/ledfx.crt
  sudo update-ca-trust
elif [ -f "/etc/ca-certificates/trust-source/anchors/ledfx.crt" ]; then
  # Arch Linux
  sudo rm -f /etc/ca-certificates/trust-source/anchors/ledfx.crt
  sudo trust extract-compat
fi

# Step 2: Remove hosts entry (requires sudo)
sudo sed -i '/ledfx.local/d' /etc/hosts 2>/dev/null || true

# Step 3: Remove SSL directory
rm -rf "$SSL_DIR"

exit 0

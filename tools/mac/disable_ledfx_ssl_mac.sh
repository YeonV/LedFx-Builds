#!/bin/bash
# Disable LedFx SSL Setup Script for macOS
# This script removes HTTPS configuration for LedFx
# Must be run with sudo

set -e

SSL_DIR="$HOME/.ledfx/ssl"

# Step 1: Remove certificate from system keychain (requires sudo)
if [ -f "$SSL_DIR/fullchain.pem" ]; then
  CERT_HASH=$(openssl x509 -noout -fingerprint -sha1 -in "$SSL_DIR/fullchain.pem" | cut -d'=' -f2 | tr -d ':')
  sudo security delete-certificate -Z "$CERT_HASH" /Library/Keychains/System.keychain 2>/dev/null || true
fi

# Step 2: Remove hosts entry (requires sudo)
sudo sed -i '' '/ledfx.local/d' /etc/hosts 2>/dev/null || true

# Step 3: Remove SSL directory
rm -rf "$SSL_DIR"

exit 0

#!/bin/bash
# Enable LedFx SSL Setup Script for Linux
# This script configures HTTPS access for LedFx via https://ledfx.local
# Must be run with sudo

set -e

# Step 1: Create SSL directory
SSL_DIR="$HOME/.ledfx/ssl"
mkdir -p "$SSL_DIR"

# Step 2: Generate SSL certificates
cd "$SSL_DIR"

# Generate private key
openssl genrsa -out privkey.pem 2048 2>/dev/null

# Generate certificate signing request
openssl req -new -key privkey.pem -out cert.csr -subj "/CN=ledfx.local/O=LedFx/C=US" 2>/dev/null

# Generate self-signed certificate (10 years)
openssl x509 -req -days 3650 -in cert.csr -signkey privkey.pem -out fullchain.pem \
  -extensions v3_req -extfile <(printf "[v3_req]\nsubjectAltName=DNS:ledfx.local,DNS:localhost") 2>/dev/null

# Clean up CSR
rm cert.csr

# Step 3: Install certificate as trusted (distro-specific)
if [ -d "/usr/local/share/ca-certificates" ]; then
  # Debian/Ubuntu
  sudo cp "$SSL_DIR/fullchain.pem" /usr/local/share/ca-certificates/ledfx.crt
  sudo update-ca-certificates
elif [ -d "/etc/pki/ca-trust/source/anchors" ]; then
  # RHEL/Fedora/CentOS
  sudo cp "$SSL_DIR/fullchain.pem" /etc/pki/ca-trust/source/anchors/ledfx.crt
  sudo update-ca-trust
elif [ -d "/etc/ca-certificates/trust-source/anchors" ]; then
  # Arch Linux
  sudo cp "$SSL_DIR/fullchain.pem" /etc/ca-certificates/trust-source/anchors/ledfx.crt
  sudo trust extract-compat
else
  echo "Unsupported distribution" >&2
  exit 1
fi

# Step 4: Add to hosts file (requires sudo)
if ! grep -q "ledfx.local" /etc/hosts; then
  echo "127.0.0.1 ledfx.local" | sudo tee -a /etc/hosts > /dev/null
fi

exit 0

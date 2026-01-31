#!/bin/bash
# Enable LedFx SSL Setup Script for macOS
# This script configures HTTPS access for LedFx via https://ledfx.local
# Must be run with sudo

set -e

# Step 1: Create SSL directory (use SUDO_USER to get actual user's home)
if [ -n "$SUDO_USER" ]; then
  USER_HOME=$(eval echo ~$SUDO_USER)
else
  USER_HOME="$HOME"
fi

SSL_DIR="$USER_HOME/.ledfx/ssl"
mkdir -p "$SSL_DIR"
chown -R "$SUDO_USER:staff" "$SSL_DIR" 2>/dev/null || true

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

# Fix permissions
chown "$SUDO_USER:staff" *.pem 2>/dev/null || true
chmod 600 *.pem

# Step 3: Install certificate as trusted in SYSTEM keychain
# Using system keychain to avoid user interaction prompts
security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$SSL_DIR/fullchain.pem"

# Step 4: Add to hosts file
if ! grep -q "ledfx.local" /etc/hosts; then
  echo "127.0.0.1 ledfx.local" >> /etc/hosts
fi

exit 0

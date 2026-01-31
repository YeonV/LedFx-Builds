#!/bin/bash
# Enable LedFx SSL Setup Script for macOS
# This script configures HTTPS access for LedFx via https://ledfx.local
# Part 1 runs as user (for GUI keychain prompt), Part 2 needs sudo (hosts file)

set -e

# Determine user's home directory
if [ -n "$SUDO_USER" ]; then
  USER_HOME=$(eval echo ~$SUDO_USER)
  ACTUAL_USER="$SUDO_USER"
else
  USER_HOME="$HOME"
  ACTUAL_USER="$USER"
fi

SSL_DIR="$USER_HOME/.ledfx/ssl"

# Step 1: Create SSL directory
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

# Fix permissions
chmod 600 *.pem

# Step 3: Add certificate to keychain with trust settings
# This will show a GUI password prompt to the user
# Use add-trusted-cert which handles trust settings properly
security add-trusted-cert -d -r trustRoot -k "$USER_HOME/Library/Keychains/login.keychain-db" "$SSL_DIR/fullchain.pem" 2>/dev/null || \
security add-trusted-cert -d -r trustRoot -k "$USER_HOME/Library/Keychains/login.keychain" "$SSL_DIR/fullchain.pem"

echo "Certificate installed to keychain"

# Step 4: Add to hosts file (needs sudo - handled separately by caller)
# This part will be handled by Node.js with sudo-prompt if not already added
if [ -w /etc/hosts ]; then
  if ! grep -q "ledfx.local" /etc/hosts; then
    echo "127.0.0.1 ledfx.local" >> /etc/hosts
    echo "Added ledfx.local to hosts file"
  fi
else
  echo "Hosts file modification requires sudo (will be handled separately)"
fi

exit 0

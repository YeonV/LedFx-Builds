# Enable LedFx SSL Setup Script
# This script configures HTTPS access for LedFx via https://ledfx.local
# Must be run as Administrator

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

try {
    # Step 1: Create SSL directory
    $sslDir = "$env:APPDATA\.ledfx\ssl"
    if (-not (Test-Path $sslDir)) {
        New-Item -ItemType Directory -Path $sslDir -Force | Out-Null
    }

    # Step 2: Generate SSL certificates
    
    # Create self-signed certificate
    $cert = New-SelfSignedCertificate `
        -DnsName "ledfx.local", "localhost" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyExportPolicy Exportable `
        -KeySpec Signature `
        -KeyLength 2048 `
        -KeyAlgorithm RSA `
        -HashAlgorithm SHA256 `
        -NotAfter (Get-Date).AddYears(10)
    
    $thumbprint = $cert.Thumbprint
    
    # Export to PFX
    $password = ConvertTo-SecureString -String "ledfx" -Force -AsPlainText
    $pfxPath = "$sslDir\cert.pfx"
    Export-PfxCertificate -Cert "Cert:\CurrentUser\My\$thumbprint" -FilePath $pfxPath -Password $password | Out-Null
    
    # Convert to PEM format
    $pfxCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, "ledfx", [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
    
    # Export certificate to PEM
    $certPem = "-----BEGIN CERTIFICATE-----`r`n"
    $certPem += [Convert]::ToBase64String($pfxCert.RawData, 'InsertLineBreaks')
    $certPem += "`r`n-----END CERTIFICATE-----`r`n"
    [System.IO.File]::WriteAllText("$sslDir\fullchain.pem", $certPem)
    
    # Export private key to PEM
    $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($pfxCert)
    $keyBytes = $rsa.Key.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob)
    $keyPem = "-----BEGIN PRIVATE KEY-----`r`n"
    $keyPem += [Convert]::ToBase64String($keyBytes, 'InsertLineBreaks')
    $keyPem += "`r`n-----END PRIVATE KEY-----`r`n"
    [System.IO.File]::WriteAllText("$sslDir\privkey.pem", $keyPem)
    
    # Step 3: Install certificate as trusted
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $store.Open("ReadWrite")
    $store.Add($pfxCert)
    $store.Close()
    
    # Clean up temporary cert from CurrentUser store
    Remove-Item "Cert:\CurrentUser\My\$thumbprint" -ErrorAction SilentlyContinue
    
    # Step 4: Add to hosts file
    $hostsFile = "C:\Windows\System32\drivers\etc\hosts"
    $hostsContent = Get-Content $hostsFile -Raw
    
    if ($hostsContent -notmatch "ledfx\.local") {
        Add-Content -Path $hostsFile -Value "`n127.0.0.1 ledfx.local"
    }
    
} catch {
    # Silent failure - error will be caught by Electron
    exit 1
}

# Script completes - no need to wait for keypress when called from Electron
exit 0

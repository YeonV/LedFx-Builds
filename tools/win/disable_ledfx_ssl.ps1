# Disable LedFx SSL Cleanup Script
# This script removes all SSL configurations for LedFx
# Must be run as Administrator

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

try {
    $sslDir = "$env:APPDATA\.ledfx\ssl"
    
    # Step 1: Remove certificate from Trusted Root
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $store.Open("ReadWrite")
    
    $certsToRemove = $store.Certificates | Where-Object { 
        $_.Subject -like "*ledfx.local*" -or 
        ($_.DnsNameList | Where-Object { $_.Unicode -eq "ledfx.local" })
    }
    
    if ($certsToRemove) {
        foreach ($cert in $certsToRemove) {
            $store.Remove($cert)
        }
    }
    
    $store.Close()
    
    # Step 2: Remove from hosts file
    $hostsFile = "C:\Windows\System32\drivers\etc\hosts"
    $hostsContent = Get-Content $hostsFile
    $newHostsContent = $hostsContent | Where-Object { $_ -notmatch "ledfx\.local" }
    
    if ($hostsContent.Count -ne $newHostsContent.Count) {
        Set-Content -Path $hostsFile -Value $newHostsContent
    }
    
    # Step 3: Remove SSL files
    if (Test-Path $sslDir) {
        Remove-Item -Path $sslDir -Recurse -Force
    }
    
} catch {
    # Silent failure - error will be caught by Electron
    exit 1
}

# Script completes - no need to wait for keypress when called from Electron
exit 0

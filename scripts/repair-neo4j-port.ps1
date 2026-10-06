# Run as Administrator. Restores Windows' default TCP dynamic port range.
# Briefly restarts WinNAT, which can interrupt Docker/WSL networking.
# Does not delete port exclusions, containers, volumes, or database files.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$logPath = Join-Path $PSScriptRoot 'repair-neo4j-port.log'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script as Administrator.'
}

Start-Transcript -Path $logPath -Force | Out-Null
try {
    Write-Output 'Before repair:'
    netsh interface ipv4 show dynamicportrange protocol=tcp
    netsh interface ipv6 show dynamicportrange protocol=tcp
    netsh interface ipv4 show excludedportrange protocol=tcp

    netsh interface ipv4 set dynamicportrange protocol=tcp startport=49152 numberofports=16384
    if ($LASTEXITCODE -ne 0) { throw 'Could not restore IPv4 TCP dynamic ports.' }
    netsh interface ipv6 set dynamicportrange protocol=tcp startport=49152 numberofports=16384
    if ($LASTEXITCODE -ne 0) { throw 'Could not restore IPv6 TCP dynamic ports.' }

    Restart-Service -Name winnat -ErrorAction Stop
    Write-Output 'After repair:'
    netsh interface ipv4 show dynamicportrange protocol=tcp
    netsh interface ipv6 show dynamicportrange protocol=tcp
    netsh interface ipv4 show excludedportrange protocol=tcp

    foreach ($port in @(7474, 7687)) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
        try {
            $listener.Start()
            Write-Output "Port $port bind succeeded."
        }
        finally { $listener.Stop() }
    }
    Write-Output 'Repair completed. Database ports can now be restored separately.'
}
catch {
    Write-Output ('Repair incomplete: ' + $_.Exception.Message)
    Write-Output 'Do not change the working database ports until 7687 is available.'
    Write-Output 'If exclusions remain, a Windows restart may be needed; none was requested by this script.'
    exit 1
}
finally { Stop-Transcript | Out-Null }

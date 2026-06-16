#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Render the production Caddyfile for AgroGuardian.

.DESCRIPTION
  Substitutes the IP-WITH-DASHES placeholders in deploy/caddy/Caddyfile
  with either:
    - a real domain (preferred, once brand is locked), or
    - the AWS Lightsail static IP rendered as dashes for sslip.io (prototype).

  Output: deploy/caddy/Caddyfile.prod
  Coolify mounts this rendered file into the caddy container.

.PARAMETER IP
  Static IP, e.g. 13.235.50.100. Mutually exclusive with -Domain.

.PARAMETER Domain
  Apex domain, e.g. agroguardian.in. Mutually exclusive with -IP.

.EXAMPLE
  ./scripts/dev/render-caddyfile.ps1 -IP 13.235.50.100
  ./scripts/dev/render-caddyfile.ps1 -Domain agroguardian.in
#>

[CmdletBinding(DefaultParameterSetName = 'IP')]
param(
    [Parameter(Mandatory, ParameterSetName = 'IP')]
    [string]$IP,

    [Parameter(Mandatory, ParameterSetName = 'Domain')]
    [string]$Domain
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$template = Join-Path $repoRoot 'deploy/caddy/Caddyfile'
$output = Join-Path $repoRoot 'deploy/caddy/Caddyfile.prod'

if (-not (Test-Path $template)) {
    throw "Template not found: $template"
}

$content = Get-Content -Raw $template

if ($PSCmdlet.ParameterSetName -eq 'Domain') {
    $content = $content `
        -replace 'api-IP-WITH-DASHES\.sslip\.io', "api.$Domain" `
        -replace 'mqtt-IP-WITH-DASHES\.sslip\.io', "mqtt.$Domain" `
        -replace 'dashboard-IP-WITH-DASHES\.sslip\.io', "dashboard.$Domain" `
        -replace 'metrics-IP-WITH-DASHES\.sslip\.io', "metrics.$Domain"
    Write-Host "Rendered Caddyfile for domain: $Domain"
} else {
    if ($IP -notmatch '^\d{1,3}(\.\d{1,3}){3}$') {
        throw "IP '$IP' does not look like a valid IPv4 address"
    }
    $dashed = $IP -replace '\.', '-'
    $content = $content -replace 'IP-WITH-DASHES', $dashed
    Write-Host "Rendered Caddyfile for sslip.io with IP: $IP (dashed: $dashed)"
}

Set-Content -Path $output -Value $content -Encoding utf8
Write-Host "Wrote $output"

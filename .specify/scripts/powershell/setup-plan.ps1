#!/usr/bin/env pwsh
# Men-setup rencana implementasi untuk sebuah fitur

[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

# Tampilkan bantuan jika diminta
if ($Help) {
    Write-Output "Penggunaan: ./setup-plan.ps1 [-Json] [-Help]"
    Write-Output "  -Json     Menampilkan hasil dalam format JSON"
    Write-Output "  -Help     Menampilkan pesan bantuan ini"
    exit 0
}

# Muat fungsi-fungsi umum
. "$PSScriptRoot/common.ps1"

# Ambil semua path dan variabel dari fungsi umum
$paths = Get-FeaturePathsEnv

# Periksa apakah saat ini berada di feature branch yang benar (hanya untuk repo git)
if (-not (Test-FeatureBranch -Branch $paths.CURRENT_BRANCH -HasGit $paths.HAS_GIT)) { 
    exit 1 
}

# Pastikan direktori fitur ada
New-Item -ItemType Directory -Path $paths.FEATURE_DIR -Force | Out-Null

# Salin template plan jika ada, jika tidak catat atau buat file kosong
$template = Join-Path $paths.REPO_ROOT '.specify/templates/plan-template.md'
if (Test-Path $template) { 
    Copy-Item $template $paths.IMPL_PLAN -Force
    Write-Output "Template plan disalin ke $($paths.IMPL_PLAN)"
} else {
    Write-Warning "Template plan tidak ditemukan di $template"
    # Buat file plan dasar jika template tidak ada
    New-Item -ItemType File -Path $paths.IMPL_PLAN -Force | Out-Null
}

# Tampilkan hasil
if ($Json) {
    $result = [PSCustomObject]@{ 
        FEATURE_SPEC = $paths.FEATURE_SPEC
        IMPL_PLAN = $paths.IMPL_PLAN
        SPECS_DIR = $paths.FEATURE_DIR
        BRANCH = $paths.CURRENT_BRANCH
        HAS_GIT = $paths.HAS_GIT
    }
    $result | ConvertTo-Json -Compress
} else {
    Write-Output "FEATURE_SPEC: $($paths.FEATURE_SPEC)"
    Write-Output "IMPL_PLAN: $($paths.IMPL_PLAN)"
    Write-Output "SPECS_DIR: $($paths.FEATURE_DIR)"
    Write-Output "BRANCH: $($paths.CURRENT_BRANCH)"
    Write-Output "HAS_GIT: $($paths.HAS_GIT)"
}

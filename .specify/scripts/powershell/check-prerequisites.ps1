#!/usr/bin/env pwsh

# Script pengecekan prerequisite terpusat (PowerShell)
#
# Script ini menyediakan pengecekan prerequisite terpadu untuk workflow Spec-Driven Development.
# Script ini menggantikan fungsionalitas yang sebelumnya tersebar di beberapa script.
#
# Penggunaan: ./check-prerequisites.ps1 [OPTIONS]
#
# OPSI:
#   -Json               Output dalam format JSON
#   -RequireTasks       Mengharuskan tasks.md ada (untuk fase implementasi)
#   -IncludeTasks       Menyertakan tasks.md dalam daftar AVAILABLE_DOCS
#   -PathsOnly          Hanya menampilkan variabel path (tanpa validasi)
#   -Help, -h           Menampilkan pesan bantuan

[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$RequireTasks,
    [switch]$IncludeTasks,
    [switch]$PathsOnly,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

# Tampilkan bantuan jika diminta
if ($Help) {
    Write-Output @"
Usage: check-prerequisites.ps1 [OPTIONS]

Pengecekan prerequisite terpusat untuk workflow Spec-Driven Development.

OPTIONS:
    -Json               Output dalam format JSON
    -RequireTasks       Mengharuskan tasks.md ada (untuk fase implementasi)
    -IncludeTasks       Menyertakan tasks.md dalam daftar AVAILABLE_DOCS
    -PathsOnly          Hanya menampilkan variabel path (tanpa validasi prerequisite)
    -Help, -h           Menampilkan pesan bantuan ini

CONTOH:
    # Cek prerequisite untuk task (plan.md wajib ada)
  .\check-prerequisites.ps1 -Json
  
    # Cek prerequisite implementasi (plan.md + tasks.md wajib ada)
  .\check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
  
    # Hanya mendapatkan path feature (tanpa validasi)
  .\check-prerequisites.ps1 -PathsOnly

"@
    exit 0
}

# Source common functions
. "$PSScriptRoot/common.ps1"

# Ambil path feature dan validasi branch
$paths = Get-FeaturePathsEnv

if (-not (Test-FeatureBranch -Branch $paths.CURRENT_BRANCH -HasGit:$paths.HAS_GIT)) { 
    exit 1 
}

# Jika mode paths-only, tampilkan path dan keluar (mendukung kombinasi -Json -PathsOnly)
if ($PathsOnly) {
    if ($Json) {
        [PSCustomObject]@{
            REPO_ROOT    = $paths.REPO_ROOT
            BRANCH       = $paths.CURRENT_BRANCH
            FEATURE_DIR  = $paths.FEATURE_DIR
            FEATURE_SPEC = $paths.FEATURE_SPEC
            IMPL_PLAN    = $paths.IMPL_PLAN
            TASKS        = $paths.TASKS
        } | ConvertTo-Json -Compress
    } else {
        Write-Output "REPO_ROOT: $($paths.REPO_ROOT)"
        Write-Output "BRANCH: $($paths.CURRENT_BRANCH)"
        Write-Output "FEATURE_DIR: $($paths.FEATURE_DIR)"
        Write-Output "FEATURE_SPEC: $($paths.FEATURE_SPEC)"
        Write-Output "IMPL_PLAN: $($paths.IMPL_PLAN)"
        Write-Output "TASKS: $($paths.TASKS)"
    }
    exit 0
}

# Validasi direktori dan file yang dibutuhkan
if (-not (Test-Path $paths.FEATURE_DIR -PathType Container)) {
    Write-Output "ERROR: Direktori fitur tidak ditemukan: $($paths.FEATURE_DIR)"
    Write-Output "Jalankan /speckit.specify terlebih dahulu untuk membuat struktur fitur."
    exit 1
}

if (-not (Test-Path $paths.IMPL_PLAN -PathType Leaf)) {
    Write-Output "ERROR: plan.md tidak ditemukan di $($paths.FEATURE_DIR)"
    Write-Output "Jalankan /speckit.plan terlebih dahulu untuk membuat rencana implementasi."
    exit 1
}

# Check for tasks.md if required
if ($RequireTasks -and -not (Test-Path $paths.TASKS -PathType Leaf)) {
    Write-Output "ERROR: tasks.md tidak ditemukan di $($paths.FEATURE_DIR)"
    Write-Output "Jalankan /speckit.tasks terlebih dahulu untuk membuat daftar task."
    exit 1
}

# Bangun daftar dokumen yang tersedia
$docs = @()

# Selalu cek dokumen opsional ini
if (Test-Path $paths.RESEARCH) { $docs += 'research.md' }
if (Test-Path $paths.DATA_MODEL) { $docs += 'data-model.md' }

# Cek direktori contracts (hanya jika ada dan berisi file)
if ((Test-Path $paths.CONTRACTS_DIR) -and (Get-ChildItem -Path $paths.CONTRACTS_DIR -ErrorAction SilentlyContinue | Select-Object -First 1)) { 
    $docs += 'contracts/' 
}

if (Test-Path $paths.QUICKSTART) { $docs += 'quickstart.md' }

# Sertakan tasks.md jika diminta dan file-nya ada
if ($IncludeTasks -and (Test-Path $paths.TASKS)) { 
    $docs += 'tasks.md' 
}

# Output results
if ($Json) {
    # Output JSON
    [PSCustomObject]@{ 
        FEATURE_DIR = $paths.FEATURE_DIR
        AVAILABLE_DOCS = $docs 
    } | ConvertTo-Json -Compress
} else {
    # Output teks
    Write-Output "FEATURE_DIR:$($paths.FEATURE_DIR)"
    Write-Output "AVAILABLE_DOCS:"
    
    # Tampilkan status setiap dokumen potensial
    Test-FileExists -Path $paths.RESEARCH -Description 'research.md' | Out-Null
    Test-FileExists -Path $paths.DATA_MODEL -Description 'data-model.md' | Out-Null
    Test-DirHasFiles -Path $paths.CONTRACTS_DIR -Description 'contracts/' | Out-Null
    Test-FileExists -Path $paths.QUICKSTART -Description 'quickstart.md' | Out-Null
    
    if ($IncludeTasks) {
        Test-FileExists -Path $paths.TASKS -Description 'tasks.md' | Out-Null
    }
}

#!/usr/bin/env pwsh
# Membuat feature baru
[CmdletBinding()]
param(
    [switch]$Json,
    [string]$ShortName,
    [int]$Number = 0,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$FeatureDescription
)
$ErrorActionPreference = 'Stop'

# Tampilkan bantuan jika diminta
if ($Help) {
    Write-Host "Penggunaan: ./create-new-feature.ps1 [-Json] [-ShortName <name>] [-Number N] <deskripsi fitur>"
    Write-Host ""
    Write-Host "Opsi:"
    Write-Host "  -Json               Output dalam format JSON"
    Write-Host "  -ShortName <name>   Berikan short name kustom (2-4 kata) untuk branch"
    Write-Host "  -Number N           Tentukan nomor branch secara manual (mengganti deteksi otomatis)"
    Write-Host "  -Help               Menampilkan pesan bantuan ini"
    Write-Host ""
    Write-Host "Contoh:"
    Write-Host "  ./create-new-feature.ps1 'Tambah sistem autentikasi pengguna' -ShortName 'user-auth'"
    Write-Host "  ./create-new-feature.ps1 'Implementasi integrasi OAuth2 untuk API'"
    exit 0
}

# Pastikan deskripsi fitur diberikan
if (-not $FeatureDescription -or $FeatureDescription.Count -eq 0) {
    Write-Error "Penggunaan: ./create-new-feature.ps1 [-Json] [-ShortName <name>] <deskripsi fitur>"
    exit 1
}

$featureDesc = ($FeatureDescription -join ' ').Trim()

# Validasi bahwa deskripsi tidak kosong setelah di-trim (misalnya hanya spasi)
if ([string]::IsNullOrWhiteSpace($featureDesc)) {
    Write-Error "Error: Deskripsi fitur tidak boleh kosong atau hanya berisi spasi"
    exit 1
}

# Menentukan repository root. Utamakan informasi dari git bila tersedia, namun
# fallback ke pencarian penanda repository sehingga workflow tetap berfungsi
# pada repository yang di-inisialisasi dengan --no-git.
function Find-RepositoryRoot {
    param(
        [string]$StartDir,
        [string[]]$Markers = @('.git', '.specify')
    )
    $current = Resolve-Path $StartDir
    while ($true) {
        foreach ($marker in $Markers) {
            if (Test-Path (Join-Path $current $marker)) {
                return $current
            }
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current) {
            # Mencapai root filesystem tanpa menemukan penanda
            return $null
        }
        $current = $parent
    }
}

function Get-HighestNumberFromSpecs {
    param([string]$SpecsDir)
    
    $highest = 0
    if (Test-Path $SpecsDir) {
        Get-ChildItem -Path $SpecsDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d+)') {
                $num = [int]$matches[1]
                if ($num -gt $highest) { $highest = $num }
            }
        }
    }
    return $highest
}

function Get-HighestNumberFromBranches {
    param()
    
    $highest = 0
    try {
        $branches = git branch -a 2>$null
        if ($LASTEXITCODE -eq 0) {
            foreach ($branch in $branches) {
                # Clean branch name: remove leading markers and remote prefixes
                $cleanBranch = $branch.Trim() -replace '^\*?\s+', '' -replace '^remotes/[^/]+/', ''
                
                # Extract feature number if branch matches pattern ###-*
                if ($cleanBranch -match '^(\d+)-') {
                    $num = [int]$matches[1]
                    if ($num -gt $highest) { $highest = $num }
                }
            }
        }
    } catch {
        # Jika perintah git gagal, kembalikan 0
        Write-Verbose "Tidak dapat memeriksa branch Git: $_"
    }
    return $highest
}

function Get-NextBranchNumber {
    param(
        [string]$SpecsDir
    )

    # Fetch semua remote untuk mendapatkan informasi branch terbaru (abaikan error jika tidak ada remote)
    try {
        git fetch --all --prune 2>$null | Out-Null
    } catch {
        # Ignore fetch errors
    }

    # Ambil nomor tertinggi dari SEMUA branch (bukan hanya yang cocok dengan short name)
    $highestBranch = Get-HighestNumberFromBranches

    # Ambil nomor tertinggi dari SEMUA spec (bukan hanya yang cocok dengan short name)
    $highestSpec = Get-HighestNumberFromSpecs -SpecsDir $SpecsDir

    # Ambil nilai maksimum dari keduanya
    $maxNum = [Math]::Max($highestBranch, $highestSpec)

    # Kembalikan nomor berikutnya
    return $maxNum + 1
}

function ConvertTo-CleanBranchName {
    param([string]$Name)
    
    return $Name.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
}
$fallbackRoot = (Find-RepositoryRoot -StartDir $PSScriptRoot)
if (-not $fallbackRoot) {
    Write-Error "Error: Could not determine repository root. Please run this script from within the repository."
    exit 1
}

try {
    $repoRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasGit = $true
    } else {
        throw "Git not available"
    }
} catch {
    $repoRoot = $fallbackRoot
    $hasGit = $false
}

Set-Location $repoRoot

$specsDir = Join-Path $repoRoot 'specs'
New-Item -ItemType Directory -Path $specsDir -Force | Out-Null

# Fungsi untuk menghasilkan nama branch dengan filter stop word dan panjang
function Get-BranchName {
    param([string]$Description)
    
    # Stop word umum yang akan diabaikan
    $stopWords = @(
        'i', 'a', 'an', 'the', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall',
        'this', 'that', 'these', 'those', 'my', 'your', 'our', 'their',
        'want', 'need', 'add', 'get', 'set'
    )
    
    # Konversi ke huruf kecil dan ekstrak kata (hanya alfanumerik)
    $cleanName = $Description.ToLower() -replace '[^a-z0-9\s]', ' '
    $words = $cleanName -split '\s+' | Where-Object { $_ }
    
    # Filter kata: buang stop word dan kata dengan panjang < 3 karakter (kecuali akronim uppercase di teks asli)
    $meaningfulWords = @()
    foreach ($word in $words) {
        # Lewati stop word
        if ($stopWords -contains $word) { continue }
        
        # Simpan kata dengan panjang >= 3 ATAU muncul sebagai uppercase di teks asli (kemungkinan akronim)
        if ($word.Length -ge 3) {
            $meaningfulWords += $word
        } elseif ($Description -match "\b$($word.ToUpper())\b") {
            # Keep short words if they appear as uppercase in original (likely acronyms)
            $meaningfulWords += $word
        }
    }
    
    # Jika ada kata bermakna, gunakan 3-4 pertama
    if ($meaningfulWords.Count -gt 0) {
        $maxWords = if ($meaningfulWords.Count -eq 4) { 4 } else { 3 }
        $result = ($meaningfulWords | Select-Object -First $maxWords) -join '-'
        return $result
    } else {
        # Fallback ke logika asli jika tidak ada kata bermakna
        $result = ConvertTo-CleanBranchName -Name $Description
        $fallbackWords = ($result -split '-') | Where-Object { $_ } | Select-Object -First 3
        return [string]::Join('-', $fallbackWords)
    }
}

# Generate nama branch
if ($ShortName) {
    # Gunakan short name yang diberikan, hanya dibersihkan
    $branchSuffix = ConvertTo-CleanBranchName -Name $ShortName
} else {
    # Generate dari deskripsi dengan filter pintar
    $branchSuffix = Get-BranchName -Description $featureDesc
}

# Determine branch number
if ($Number -eq 0) {
    if ($hasGit) {
        # Check existing branches on remotes
        $Number = Get-NextBranchNumber -SpecsDir $specsDir
    } else {
        # Fall back to local directory check
        $Number = (Get-HighestNumberFromSpecs -SpecsDir $specsDir) + 1
    }
}

$featureNum = ('{0:000}' -f $Number)
$branchName = "$featureNum-$branchSuffix"

# GitHub menerapkan batas 244 byte untuk nama branch
# Validasi dan potong bila perlu
$maxBranchLength = 244
if ($branchName.Length -gt $maxBranchLength) {
    # Hitung seberapa banyak suffix perlu dipotong
    # Mempertimbangkan: nomor fitur (3) + tanda hubung (1) = 4 karakter
    $maxSuffixLength = $maxBranchLength - 4
    
    # Potong suffix
    $truncatedSuffix = $branchSuffix.Substring(0, [Math]::Min($branchSuffix.Length, $maxSuffixLength))
    # Hapus tanda hubung di akhir jika muncul karena pemotongan
    $truncatedSuffix = $truncatedSuffix -replace '-$', ''
    
    $originalBranchName = $branchName
    $branchName = "$featureNum-$truncatedSuffix"
    
    Write-Warning "[specify] Nama branch melebihi batas 244 byte GitHub"
    Write-Warning "[specify] Asli: $originalBranchName ($($originalBranchName.Length) bytes)"
    Write-Warning "[specify] Dipotong menjadi: $branchName ($($branchName.Length) bytes)"
}

if ($hasGit) {
    $branchCreated = $false
    try {
        git checkout -b $branchName 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $branchCreated = $true
        }
    } catch {
        # Exception during git command
    }

    if (-not $branchCreated) {
        # Cek apakah branch sudah ada
        $existingBranch = git branch --list $branchName 2>$null
        if ($existingBranch) {
            Write-Error "Error: Branch '$branchName' sudah ada. Gunakan nama fitur lain atau tentukan nomor berbeda dengan -Number."
            exit 1
        } else {
            Write-Error "Error: Gagal membuat git branch '$branchName'. Periksa konfigurasi git Anda dan coba lagi."
            exit 1
        }
    }
} else {
    Write-Warning "[specify] Peringatan: Repository Git tidak terdeteksi; pembuatan branch $branchName dilewati"
}

$featureDir = Join-Path $specsDir $branchName
New-Item -ItemType Directory -Path $featureDir -Force | Out-Null

$template = Join-Path $repoRoot '.specify/templates/spec-template.md'
$specFile = Join-Path $featureDir 'spec.md'
if (Test-Path $template) { 
    Copy-Item $template $specFile -Force 
} else { 
    New-Item -ItemType File -Path $specFile | Out-Null 
}

# Set the SPECIFY_FEATURE environment variable for the current session
$env:SPECIFY_FEATURE = $branchName

if ($Json) {
    $obj = [PSCustomObject]@{ 
        BRANCH_NAME = $branchName
        SPEC_FILE = $specFile
        FEATURE_NUM = $featureNum
        HAS_GIT = $hasGit
    }
    $obj | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME: $branchName"
    Write-Output "SPEC_FILE: $specFile"
    Write-Output "FEATURE_NUM: $featureNum"
    Write-Output "HAS_GIT: $hasGit"
    Write-Output "Variabel environment SPECIFY_FEATURE di-set ke: $branchName"
}


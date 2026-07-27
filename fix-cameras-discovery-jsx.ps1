<#
    fix-cameras-discovery-jsx.ps1
    Memperbaiki bug JSX di frontend/src/pages/Cameras/index.tsx
    (DiscoveryModal render di luar root element -> invalid JSX)

    Cara pakai:
      .\fix-cameras-discovery-jsx.ps1
      .\fix-cameras-discovery-jsx.ps1 -RepoPath "C:\Users\Efendy\Documents\Git\nvr_cam"
      .\fix-cameras-discovery-jsx.ps1 -RunBuild
#>

param(
    [string]$RepoPath = "C:\Users\Efendy\Documents\Git\nvr_cam",
    [switch]$RunBuild
)

$ErrorActionPreference = "Stop"

$filePath = Join-Path $RepoPath "frontend\src\pages\Cameras\index.tsx"

if (-not (Test-Path $filePath)) {
    Write-Host "File tidak ditemukan: $filePath" -ForegroundColor Red
    Write-Host "Jalankan ulang dengan parameter -RepoPath, contoh:" -ForegroundColor Yellow
    Write-Host "  .\fix-cameras-discovery-jsx.ps1 -RepoPath 'C:\Users\Efendy\Documents\Git\nvr_cam'" -ForegroundColor Yellow
    exit 1
}

# --- Backup dulu ---
$backupPath = "$filePath.bak"
Copy-Item -Path $filePath -Destination $backupPath -Force
Write-Host "Backup dibuat: $backupPath" -ForegroundColor Cyan

# --- Baca isi file ---
$raw = Get-Content -Path $filePath -Raw -Encoding UTF8

# Normalisasi ke LF supaya pencocokan string konsisten (file Windows biasanya CRLF)
$usesCRLF   = $raw -match "`r`n"
$normalized = $raw -replace "`r`n", "`n"

# --- Pattern 1: pembuka return() perlu dibungkus Fragment <> ---
$old1 = @'
  return (
    <div className="flex flex-col h-full p-4 gap-4">
'@

$new1 = @'
  return (
    <>
    <div className="flex flex-col h-full p-4 gap-4">
'@

# --- Pattern 2: penutup return() perlu Fragment penutup </> ---
$old2 = @'
    </div>

      {showDiscovery && (
        <DiscoveryModal
          storageDrives={storageDrives || []}
          onClose={() => setShowDiscovery(false)}
        />
      )}
  )
}
'@

$new2 = @'
    </div>

      {showDiscovery && (
        <DiscoveryModal
          storageDrives={storageDrives || []}
          onClose={() => setShowDiscovery(false)}
        />
      )}
    </>
  )
}
'@

$changed = $false

if ($normalized -notmatch [regex]::Escape($old1)) {
    Write-Host "[SKIP] Pattern 1 (pembuka Fragment) tidak ditemukan - mungkin sudah pernah diperbaiki." -ForegroundColor Yellow
} else {
    $normalized = $normalized.Replace($old1, $new1)
    $changed = $true
    Write-Host "[OK] Pattern 1 diperbaiki (Fragment pembuka <> ditambahkan)." -ForegroundColor Green
}

if ($normalized -notmatch [regex]::Escape($old2)) {
    Write-Host "[SKIP] Pattern 2 (penutup Fragment) tidak ditemukan - mungkin sudah pernah diperbaiki." -ForegroundColor Yellow
} else {
    $normalized = $normalized.Replace($old2, $new2)
    $changed = $true
    Write-Host "[OK] Pattern 2 diperbaiki (Fragment penutup </> ditambahkan)." -ForegroundColor Green
}

if (-not $changed) {
    Write-Host "`nTidak ada perubahan yang diterapkan. File mungkin sudah berbeda dari yang diharapkan." -ForegroundColor Yellow
    Write-Host "Cek manual bagian 'return (' kedua di file tersebut." -ForegroundColor Yellow
    exit 0
}

# Kembalikan ke CRLF kalau file aslinya CRLF
if ($usesCRLF) {
    $final = $normalized -replace "`n", "`r`n"
} else {
    $final = $normalized
}

# Tulis ulang dengan UTF8 + BOM (mengikuti encoding asli file)
$utf8Bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($filePath, $final, $utf8Bom)

Write-Host "`nFile berhasil diperbarui: $filePath" -ForegroundColor Green
Write-Host "Kalau ada masalah, restore dengan:" -ForegroundColor Cyan
Write-Host "  Copy-Item '$backupPath' '$filePath' -Force" -ForegroundColor Cyan

# --- Opsional: langsung build untuk validasi ---
if ($RunBuild) {
    $frontendPath = Join-Path $RepoPath "frontend"
    Write-Host "`nMenjalankan npm run build di $frontendPath ..." -ForegroundColor Cyan
    Push-Location $frontendPath
    try {
        npm run build
        Write-Host "`nBuild sukses. Silakan cek hasilnya, lalu git add/commit/push." -ForegroundColor Green
    } catch {
        Write-Host "`nBuild gagal. Cek error di atas." -ForegroundColor Red
    } finally {
        Pop-Location
    }
}
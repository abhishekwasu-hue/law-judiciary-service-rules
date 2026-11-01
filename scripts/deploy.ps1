# प्रस्ताव कक्ष (app B) — build the front end and deploy the Cloudflare Worker.
# Windows PowerShell 5.1 compatible. Run from anywhere:  powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1
# Needs: Node.js 20+, and `npx wrangler login` done once. No keys in this script (keys are entered on the app's Settings screen).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$toml = Join-Path $root 'cloudflare\wrangler.toml'
$app  = Join-Path $root 'dashboard-app'

function Stop-WithMessage([string]$msg) {
  Write-Host ''
  Write-Host $msg -ForegroundColor Red
  exit 1
}

# 1. KV id must be pasted into wrangler.toml
if (-not (Test-Path $toml)) { Stop-WithMessage "cloudflare\wrangler.toml सापडली नाही. रेपोच्या मुख्य फोल्डरमधून चालवा." }
if (Select-String -Path $toml -Pattern 'PASTE_KV_NAMESPACE_ID' -SimpleMatch -Quiet) {
  Stop-WithMessage ("थांबले: cloudflare\wrangler.toml मध्ये KV id अजून भरलेला नाही.`n" +
    "आधी चालवा:  npx wrangler kv namespace create SETTINGS`n" +
    "छापलेला id 'PASTE_KV_NAMESPACE_ID' च्या जागी पेस्ट करा, मग हे script पुन्हा चालवा.")
}

# 2. Build the front end
if (-not (Test-Path (Join-Path $app 'package.json'))) { Stop-WithMessage "dashboard-app\package.json सापडली नाही — front end फोल्डर तपासा." }
Push-Location $app
try {
  Write-Host '== npm ci (dashboard-app) ==' -ForegroundColor Cyan
  npm ci
  if ($LASTEXITCODE -ne 0) { Stop-WithMessage "npm ci अयशस्वी. वरील त्रुटी पाहा (Node.js 20+ आहे का?)." }
  Write-Host '== npm run build ==' -ForegroundColor Cyan
  npm run build
  if ($LASTEXITCODE -ne 0) { Stop-WithMessage "front end build अयशस्वी. वरील त्रुटी पाहा." }
} finally { Pop-Location }
if (-not (Test-Path (Join-Path $app 'dist\index.html'))) { Stop-WithMessage "dashboard-app\dist\index.html तयार झाली नाही." }

# 3. Deploy the Worker (serves dashboard-app\dist + /api/*)
Push-Location (Join-Path $root 'cloudflare')
try {
  Write-Host '== npx wrangler deploy ==' -ForegroundColor Cyan
  npx wrangler deploy
  if ($LASTEXITCODE -ne 0) { Stop-WithMessage "Worker deploy अयशस्वी. 'npx wrangler login' केले आहे का ते तपासा." }
} finally { Pop-Location }

Write-Host ''
Write-Host 'पूर्ण: Worker deploy झाला. वर छापलेली https://...workers.dev लिंक उघडा.' -ForegroundColor Green

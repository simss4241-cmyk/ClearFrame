# CLEARFRAME Cloud Run Deployment Script (PowerShell)
# Usage: .\scripts\deploy.ps1 [-ProjectId <your-gcp-project>] [-Region <gcp-region>]

param (
    [string]$ProjectId = $env:GOOGLE_CLOUD_PROJECT,
    [string]$Region = "us-central1",
    [string]$ServiceName = "clearframe"
)

$PSNativeCommandUseErrorActionPreference = $false

Write-Host "`n=== CLEARFRAME Cloud Run Deployment ===" -ForegroundColor Cyan

if (-not $ProjectId) {
    $ProjectId = gcloud config get-value project 2>$null
}

if (-not $ProjectId -or $ProjectId -eq "(unset)") {
    Write-Host "[FAIL] No Google Cloud Project ID detected." -ForegroundColor Red
    Write-Host "Please set your project ID via: gcloud config set project <PROJECT_ID>" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Deploying to Project: $ProjectId (Region: $Region)" -ForegroundColor Green

# Load API keys from .env if not in environment
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if (-not $env:PARALLEL_API_KEY -and $_ -match "^PARALLEL_API_KEY=(.+)$") {
            $env:PARALLEL_API_KEY = $matches[1].Trim()
        }
        if (-not $env:GEMINI_API_KEY -and $_ -match "^GEMINI_API_KEY=(.+)$") {
            $env:GEMINI_API_KEY = $matches[1].Trim()
        }
    }
}

# Ensure required GCP APIs are enabled
Write-Host "`nEnsuring required Google Cloud APIs are enabled..." -ForegroundColor Cyan
gcloud services enable `
    aiplatform.googleapis.com `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    storage.googleapis.com `
    firestore.googleapis.com `
    secretmanager.googleapis.com `
    --project $ProjectId

# Configure IAM permissions for Cloud Build & Secret Manager
$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)" 2>$null
if ($projectNumber) {
    Write-Host "`nConfiguring IAM permissions for Cloud Build & Secret Manager..." -ForegroundColor Cyan
    $computeSa = "serviceAccount:${projectNumber}-compute@developer.gserviceaccount.com"
    $cloudbuildSa = "serviceAccount:${projectNumber}@cloudbuild.gserviceaccount.com"

    gcloud projects add-iam-policy-binding $ProjectId --member=$computeSa --role="roles/aiplatform.user" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member=$computeSa --role="roles/datastore.user" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member=$computeSa --role="roles/storage.objectViewer" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member=$computeSa --role="roles/secretmanager.secretAccessor" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member=$computeSa --role="roles/artifactregistry.writer" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member=$computeSa --role="roles/logging.logWriter" --quiet 2>$null | Out-Null
    gcloud projects add-iam-policy-binding $ProjectId --member=$cloudbuildSa --role="roles/storage.objectViewer" --quiet 2>$null | Out-Null
}

# Ensure secrets exist in Secret Manager
function Ensure-Secret([string]$SecretName, [string]$SecretVal) {
    gcloud secrets describe $SecretName --project=$ProjectId 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        if ($SecretVal) {
            Write-Host "Creating '$SecretName' in Secret Manager..." -ForegroundColor Yellow
            $tempKeyFile = [System.IO.Path]::GetTempFileName()
            try {
                [System.IO.File]::WriteAllText($tempKeyFile, $SecretVal.Trim())
                gcloud secrets create $SecretName --data-file=$tempKeyFile --project=$ProjectId
            } finally {
                if (Test-Path $tempKeyFile) { Remove-Item $tempKeyFile -Force }
            }
        } else {
            Write-Host "[WARN] '$SecretName' secret not found and env var unset." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[OK] Secret '$SecretName' found." -ForegroundColor Green
    }
}

Write-Host "`nChecking Secret Manager for credentials..." -ForegroundColor Cyan
Ensure-Secret "parallel-api-key" $env:PARALLEL_API_KEY
Ensure-Secret "gemini-api-key" $env:GEMINI_API_KEY

# Deploy to Cloud Run from source
Write-Host "`nSubmitting Cloud Run build & deploy..." -ForegroundColor Cyan

gcloud run deploy $ServiceName `
    --source . `
    --project $ProjectId `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,ENABLE_PARALLEL_MONITORS=true" `
    --set-secrets "PARALLEL_API_KEY=parallel-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"

if ($LASTEXITCODE -eq 0) {
    $serviceUrl = gcloud run services describe $ServiceName --project $ProjectId --region $Region --format="value(status.url)"
    Write-Host "`n=======================================================" -ForegroundColor Green
    Write-Host "  DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host "  Public Hosted URL: $serviceUrl" -ForegroundColor Cyan
    Write-Host "  Set PUBLIC_BASE_URL=$serviceUrl for Parallel Monitor webhooks" -ForegroundColor Yellow
    Write-Host "=======================================================`n" -ForegroundColor Green
} else {
    Write-Host "`n[FAIL] Cloud Run deployment failed." -ForegroundColor Red
}

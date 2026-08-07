param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$EnvFile = ".env.backend-secrets"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    throw "Env file not found at $EnvFile. Create it (gitignored) as KEY=value lines, one per secret name in `$SecretNames below."
}

# Backend secrets injected into Cloud Run via deploy.ps1 --set-secrets.
# Update this list when deploy.ps1 $secretBindings changes.
$SecretNames = @(
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "R2_ENDPOINT",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "COHERE_API_KEY",
    "FINEDGE_API_KEY",
    "INDIAN_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "CHAT_INTERNAL_PROXY_KEY",
    "MF_INTERNAL_ADMIN_KEY",
    "MF_INGESTION_WEBHOOK_TOKEN",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "MF_ENGINE_PARTNER_TOKEN"
)

gcloud config set project $ProjectId
gcloud services enable secretmanager.googleapis.com

$runtimeSa = "fundersai-runtime@$ProjectId.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$runtimeSa" --role "roles/secretmanager.secretAccessor" --quiet | Out-Null

$values = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length - 2) }
    $values[$key] = $val
}

$created = 0
$updated = 0
$skipped = @()

foreach ($name in $SecretNames) {
    if (-not $values.ContainsKey($name)) {
        $skipped += "$name (missing from $EnvFile)"
        continue
    }
    $value = $values[$name]
    if (-not $value) {
        $skipped += "$name (empty value in $EnvFile)"
        continue
    }

    $existing = gcloud secrets describe $name --format="value(name)" 2>$null
    if (-not $existing) {
        gcloud secrets create $name --replication-policy=automatic --labels=managed-by=fundersai,component=backend
        $created++
    }

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $value)
        gcloud secrets versions add $name --data-file="$tempFile" --quiet | Out-Null
        $updated++
    }
    finally {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Output "Created: $created    Updated: $updated"
if ($skipped.Count -gt 0) {
    Write-Output "Skipped:"
    foreach ($s in $skipped) { Write-Output "  - $s" }
}
Write-Output "Service account: $runtimeSa (roles/secretmanager.secretAccessor bound)"
Write-Output "Next: .\deploy\gcp\deploy.ps1 -ProjectId $ProjectId -Tag <git-sha>"

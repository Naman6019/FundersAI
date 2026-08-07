param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Region = "asia-south1",
    [string]$Repository = "fundersai",
    [string]$Tag = "manual"
)

$ErrorActionPreference = "Stop"
$registry = "$Region-docker.pkg.dev"
$apiImage = "$registry/$ProjectId/$Repository/api:$Tag"
$workerImage = "$registry/$ProjectId/$Repository/research-worker:$Tag"
$serviceAccount = "fundersai-runtime@$ProjectId.iam.gserviceaccount.com"

# Backend secrets injected via Google Secret Manager.
# Format per entry: ENV_VAR_NAME=SECRET_NAME:VERSION (use :latest for newest version).
# See deploy/gcp/create-secrets.ps1 to create/rotate these.
$secretBindings = @(
    "SUPABASE_URL=SUPABASE_URL:latest",
    "SUPABASE_KEY=SUPABASE_KEY:latest",
    "R2_ENDPOINT=R2_ENDPOINT:latest",
    "R2_ACCESS_KEY_ID=R2_ACCESS_KEY_ID:latest",
    "R2_SECRET_ACCESS_KEY=R2_SECRET_ACCESS_KEY:latest",
    "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest",
    "OPENAI_API_KEY=OPENAI_API_KEY:latest",
    "GROQ_API_KEY=GROQ_API_KEY:latest",
    "COHERE_API_KEY=COHERE_API_KEY:latest",
    "FINEDGE_API_KEY=FINEDGE_API_KEY:latest",
    "INDIAN_API_KEY=INDIAN_API_KEY:latest",
    "LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest",
    "LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest",
    "CHAT_INTERNAL_PROXY_KEY=CHAT_INTERNAL_PROXY_KEY:latest",
    "MF_INTERNAL_ADMIN_KEY=MF_INTERNAL_ADMIN_KEY:latest",
    "MF_INGESTION_WEBHOOK_TOKEN=MF_INGESTION_WEBHOOK_TOKEN:latest",
    "UPSTASH_REDIS_REST_URL=UPSTASH_REDIS_REST_URL:latest",
    "UPSTASH_REDIS_REST_TOKEN=UPSTASH_REDIS_REST_TOKEN:latest",
    "MF_ENGINE_PARTNER_TOKEN=MF_ENGINE_PARTNER_TOKEN:latest"
) -join ","

gcloud config set project $ProjectId
gcloud services enable artifactregistry.googleapis.com run.googleapis.com secretmanager.googleapis.com logging.googleapis.com monitoring.googleapis.com

gcloud iam service-accounts describe $serviceAccount 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud iam service-accounts create fundersai-runtime --display-name "FundersAI runtime"
}
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$serviceAccount" --role "roles/secretmanager.secretAccessor" --quiet

gcloud artifacts repositories describe $Repository --location $Region 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $Repository --repository-format docker --location $Region
}

gcloud auth configure-docker $registry --quiet
docker build --file backend/Dockerfile --tag $apiImage backend
docker build --file backend/Dockerfile.worker --tag $workerImage backend
docker push $apiImage
docker push $workerImage

gcloud run deploy fundersai-api --image $apiImage --region $Region --service-account $serviceAccount --port 8080 --set-secrets $secretBindings --no-allow-unauthenticated
gcloud run jobs deploy fundersai-research-evidence --image $workerImage --region $Region --service-account $serviceAccount --set-secrets $secretBindings --args=--execute

Write-Output "API image: $apiImage"
Write-Output "Worker image: $workerImage"
Write-Output "Run the job explicitly with: gcloud run jobs execute fundersai-research-evidence --region $Region --wait"

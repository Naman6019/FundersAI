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
$secretBindings = "SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_KEY=SUPABASE_KEY:latest,R2_ENDPOINT=R2_ENDPOINT:latest,R2_ACCESS_KEY_ID=R2_ACCESS_KEY_ID:latest,R2_SECRET_ACCESS_KEY=R2_SECRET_ACCESS_KEY:latest,OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest"

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

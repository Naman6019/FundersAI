param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$NotificationChannel
)

$ErrorActionPreference = "Stop"
gcloud config set project $ProjectId

$metrics = @(
    @{ Name = "fundersai_research_abstentions"; Filter = 'resource.type="cloud_run_revision" AND textPayload:"event=fund_research_completed" AND textPayload:"abstain=true"' },
    @{ Name = "fundersai_vector_fallbacks"; Filter = 'resource.type="cloud_run_revision" AND textPayload:"event=fund_research_completed" AND textPayload:"vector_status=fallback_lexical"' },
    @{ Name = "fundersai_research_failures"; Filter = 'resource.type="cloud_run_revision" AND textPayload:"event=fund_research_failed"' },
    @{ Name = "fundersai_pipeline_failures"; Filter = 'resource.type="cloud_run_job" AND textPayload:"event=fund_research_pipeline_failed"' }
)

foreach ($metric in $metrics) {
    gcloud logging metrics describe $metric.Name 2>$null
    if ($LASTEXITCODE -eq 0) {
        gcloud logging metrics update $metric.Name --log-filter $metric.Filter
    } else {
        gcloud logging metrics create $metric.Name --log-filter $metric.Filter --description "FundersAI operational counter"
    }
}

$alerts = @(
    @{ Display = "FundersAI research failures"; Metric = "fundersai_research_failures"; Threshold = 0 },
    @{ Display = "FundersAI vector fallback spike"; Metric = "fundersai_vector_fallbacks"; Threshold = 5 },
    @{ Display = "FundersAI evidence pipeline failure"; Metric = "fundersai_pipeline_failures"; Threshold = 0 }
)

foreach ($alert in $alerts) {
    $existing = gcloud monitoring policies list --filter "displayName='$($alert.Display)'" --format "value(name)"
    if ($existing) { continue }
    $policy = @{
        displayName = $alert.Display
        combiner = "OR"
        enabled = $true
        notificationChannels = @($NotificationChannel)
        conditions = @(@{
            displayName = "$($alert.Display) in five minutes"
            conditionThreshold = @{
                filter = "metric.type=`"logging.googleapis.com/user/$($alert.Metric)`""
                comparison = "COMPARISON_GT"
                thresholdValue = $alert.Threshold
                duration = "0s"
                aggregations = @(@{ alignmentPeriod = "300s"; perSeriesAligner = "ALIGN_SUM"; crossSeriesReducer = "REDUCE_SUM" })
            }
        })
    }
    $policyFile = Join-Path ([IO.Path]::GetTempPath()) "fundersai-policy-$([guid]::NewGuid()).json"
    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $policyFile -Encoding utf8
    try {
        gcloud monitoring policies create --policy-from-file $policyFile
    } finally {
        Remove-Item -LiteralPath $policyFile -Force
    }
}

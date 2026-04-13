# Container Diagnostics Script
$CONTAINER_NAME = "aci-chubb-mcp-7742"
$RESOURCE_GROUP = "rg-chubb-mcp-poc"

Write-Host "`n========== CONTAINER DIAGNOSTICS ==========" -ForegroundColor Yellow

# Check container state
Write-Host "`n1. Container State:" -ForegroundColor Cyan
az container show -n $CONTAINER_NAME -g $RESOURCE_GROUP `
    --query "{Name:name, State:instanceView.state, RestartCount:containers[0].instanceView.restartCount}" `
    -o table

# Check container events
Write-Host "`n2. Container Events:" -ForegroundColor Cyan
az container show -n $CONTAINER_NAME -g $RESOURCE_GROUP `
    --query "containers[0].instanceView.events[].{Time:firstTimestamp, Type:type, Reason:reason, Message:message}" `
    -o table

# Get logs
Write-Host "`n3. Container Logs (last 30 lines):" -ForegroundColor Cyan
az container logs -n $CONTAINER_NAME -g $RESOURCE_GROUP --tail 30

Write-Host "`n========================================" -ForegroundColor Yellow

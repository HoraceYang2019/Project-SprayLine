Write-Host "=== final_version_1112 verification ===" -ForegroundColor Cyan
docker inspect sprayline_db --format "{{range .Mounts}}{{println .Name .Destination}}{{end}}"
docker exec sprayline_db psql -U postgres -d sprayline -c "SELECT migration_name, applied_at FROM schema_migration ORDER BY applied_at;"
docker exec sprayline_db psql -U postgres -d sprayline -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'future_prediction_result' AND column_name IN ('idempotency_key','quality_score_semantics','rule_evaluations','cause_ids','response_ids','rule_sources') ORDER BY column_name;"
docker compose ps
Write-Host "--- API version and alert history endpoint ---" -ForegroundColor Cyan
curl.exe -s "http://localhost:8011/"
Write-Host ""
curl.exe -s "http://localhost:8011/api/alerts/summary?group_by=cause"
Write-Host ""

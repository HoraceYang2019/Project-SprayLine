Write-Host "=== final_version_0717 verification ===" -ForegroundColor Cyan
docker inspect sprayline_db --format "{{range .Mounts}}{{println .Name .Destination}}{{end}}"
docker exec sprayline_db psql -U postgres -d sprayline -c "SELECT station_id, COUNT(*) AS row_count, MIN(ts) AS first_time, MAX(ts) AS latest_time FROM sensor_1min GROUP BY station_id ORDER BY station_id;"
docker compose ps

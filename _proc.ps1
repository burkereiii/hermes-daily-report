$procs = Get-Process | Sort-Object WorkingSet64 -Descending
Write-Output "TOTAL|$($procs.Count)"
$procs | Select-Object -First 5 Name,Id,@{N='MemMB';E={[math]::Round($_.WorkingSet64/1MB)}} | ForEach-Object {
    Write-Output "PROC|$($_.Name)|$($_.Id)|$($_.MemMB)"
}

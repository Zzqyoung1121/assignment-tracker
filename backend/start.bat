@echo off
echo Starting homework tracker...
echo.
echo Local:  http://localhost:8001/
echo Mobile (pick the one matching your phone network):
powershell -NoProfile -Command "$a=''; ipconfig | ForEach-Object { if ($_ -match '^\S' -and $_ -match ':') { $a = ($_ -replace ':$','').Trim() } elseif ($_ -match 'IPv4') { $ip = ($_ -split ':')[-1].Trim(); if ($ip -notmatch '^127\.' -and $ip -notmatch '^169\.254\.') { Write-Host ('  http://' + $ip + ':8001/  (' + $a + ')') } } }"
echo.
cd /d "%~dp0"
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8001/"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
pause

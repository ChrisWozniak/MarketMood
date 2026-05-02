@echo off
cd /d "%~dp0"

echo.
echo  Market Mood ^| Social Sentiment Barometer
echo  Closing any previously running instances...
echo.

:: Step 1 — kill any cmd/powershell window whose CURRENT title contains "Market Mood"
::           (PowerShell reads the live title, unlike taskkill which matches the start-time title)
powershell -NoProfile -Command "Get-Process cmd,powershell -EA SilentlyContinue | Where-Object MainWindowTitle -like '*Market Mood*' | Stop-Process -Force -EA SilentlyContinue"

:: Step 2 — kill server processes on our ports AND their parent cmd windows
::           (taskkill /T only kills children; this also kills the parent terminal)
powershell -NoProfile -Command "foreach($port in 8001,5173){$c=Get-NetTCPConnection -LocalPort $port -EA SilentlyContinue;if($c){$sp=$c.OwningProcess;$pp=(Get-CimInstance Win32_Process -Filter ('ProcessId='+$sp) -EA SilentlyContinue).ParentProcessId;Stop-Process -Id $sp -Force -EA SilentlyContinue;if($pp){Stop-Process -Id $pp -Force -EA SilentlyContinue}}}"

timeout /t 2 /nobreak >nul

echo  Starting backend and frontend...
echo.

:: "title Market Mood Backend/Frontend" runs immediately so Step 1 above can find these
:: windows reliably on the NEXT run, regardless of what activate.bat does to the title.
start "Market Mood Backend"  cmd /k "cd /d "%~dp0backend"  && call venv\Scripts\activate.bat && title Market Mood Backend  && uvicorn main:app --host 0.0.0.0 --port 8001 --reload"
timeout /t 3 /nobreak >nul
start "Market Mood Frontend" cmd /k "cd /d "%~dp0frontend" && title Market Mood Frontend && npm run dev"
timeout /t 4 /nobreak >nul

start "" "http://localhost:5173"

echo  Backend : http://localhost:8001
echo  Frontend: http://localhost:5173
echo.
:: No pause — launcher window closes itself and does not accumulate on the taskbar

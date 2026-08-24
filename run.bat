@echo off
echo ========================================
echo  MPLAD-Sentinel Setup ^& Run
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Installing dependencies...
pip install -r backend/requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Seeding database...
python -m backend.scripts.seed_data
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to seed database
    pause
    exit /b 1
)

echo.
echo [3/3] Starting server on http://localhost:8000
echo       Frontend: cd frontend ^& npm install ^& npm run dev
echo       Login: admin / admin-changeMe
echo.
uvicorn backend.app.main:app --reload --port 8000

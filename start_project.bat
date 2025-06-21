@echo off
echo ========================================
echo    Starting GrievancesBot Project
echo ========================================
echo.

echo Starting Flask Backend (Login API)...
start "Flask Backend - Port 5000" cmd /k "venv\Scripts\activate && cd login-page/backend && python app.py"

echo Starting Rasa Server...
start "Rasa Server - Port 5005" cmd /k "venv\Scripts\activate && cd chatbot && rasa run --enable-api --model models --cors *"

echo Starting Rasa Action Server...
start "Rasa Actions - Port 5055" cmd /k "venv\Scripts\activate && cd chatbot && rasa run actions"

echo Starting Static File Server...
start "Static Server - Port 8000" cmd /k "venv\Scripts\activate && python -m http.server 8000"

echo.
echo ========================================
echo    All servers are starting...
echo ========================================
echo.
echo Server URLs:
echo   Flask Backend: http://127.0.0.1:5000
echo   Rasa Server: http://localhost:5005
echo   Rasa Actions: http://localhost:5055
echo   Static Server: http://localhost:8000
echo.
echo ========================================
echo    Opening landing page...
echo ========================================
echo.
echo Press any key to open the browser...
pause >nul

start http://localhost:8000/landing-page/landing-index.html

echo.
echo Browser opened! Landing page is ready.
echo All backend services are running in the background.
echo.
echo To stop all servers, close the command windows.
pause 
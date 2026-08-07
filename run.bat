@echo off
echo =========================================================
echo  CLEARFRAME — Screenplay Clearance Production Studio
echo =========================================================
echo  Starting server at http://127.0.0.1:8080
echo  Press Ctrl+C to stop the server.
echo =========================================================
echo.

uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8080

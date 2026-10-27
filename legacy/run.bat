@echo off
echo ============================================
echo  I-ODSS v8 - Intelligent Decision Support
echo ============================================
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt
echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop.
echo.
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause

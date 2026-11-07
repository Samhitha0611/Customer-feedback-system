@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating project virtual environment...
    py -m venv .venv
    if errorlevel 1 (
        echo Failed to create the virtual environment. Install Python 3.11 or newer and try again.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
echo Installing or checking project dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist "data\customer_feedback.db" (
    echo Database not found. Generating the full project dataset...
    python -m src.generate_data --reviews 25000 --responses 25000 --messages 20000 --seed 20261022
    if errorlevel 1 goto :error
    python -m src.build_database
    if errorlevel 1 goto :error
)

echo Starting Customer Feedback Intelligence...
python -m streamlit run app.py
goto :end

:error
echo.
echo Setup or launch failed. Read the error above and check the README.
pause
exit /b 1

:end
endlocal

@echo off
REM =====================================================================
REM  GL TRADER - Binary Signal RESEARCH system (STANDALONE)
REM
REM  * Ye JARVIS se ALAG, apna khud ka bot hai - JARVIS ki zarurat nahi.
REM  * Ye sirf RESEARCH hai - koi real trade NAHI lagta, paper only.
REM  * Live data ke liye: pehle MetaTrader 5 terminal kholo aur
REM    DEMO account se login karo - tab data MT5-LIVE aayega.
REM  * MT5 band ho / login na ho to DEMO synthetic data chalega
REM    (dashboard par DEMO badge dikhega) - ghabrana nahi.
REM  * Pehli baar chalane par apna chhota sa setup (.venv) khud banega -
REM    internet chahiye aur 2-3 minute lag sakte hain. Uske baad turant
REM    khulta hai.
REM  * Dashboard apni ALAG window me khulta hai (Chrome ki tab nahi) -
REM    bina address-bar wali saaf window, JARVIS wale dashboard jaisi.
REM =====================================================================
title GL TRADER - Research Only (Standalone)
cd /d "%~dp0"

if "%~1"=="--open-dashboard" goto :open_dashboard

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Python nahi mila.
    echo          Pehle https://www.python.org/downloads/ se Python 3.10+
    echo          install karein - install ke samay "Add python.exe to PATH"
    echo          wala tick ZAROOR lagayein.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Pehli baar ka setup ho raha hai - apna .venv ban raha hai...
    python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo  [ERROR] Setup nahi ban paya. Internet check karke dobara try karein.
        echo.
        pause
        exit /b 1
    )
    echo  Zaruri hisse install ho rahe hain - 2-3 minute lag sakte hain...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
    echo  Setup ho gaya!
)

REM  Khud-update: naya version aaya ho to pehle wo lag jayega.
REM  Update fail ho jaye to bhi bot purane version par chalega.
".venv\Scripts\python.exe" updater.py

echo.
echo  GL TRADER shuru ho raha hai...
echo  Dashboard: http://127.0.0.1:8771
echo  Band karne ke liye is window me Ctrl+C dabayein.
echo.
start "" /min cmd /c ""%~f0" --open-dashboard"
".venv\Scripts\python.exe" -m JARVIS_GL_TRADER.main

echo.
echo  GL TRADER band ho gaya. Dhanyavaad!
pause
exit /b 0

REM ---------------------------------------------------------------------
REM  Dashboard ko apni alag window (--app mode) me kholna.
REM  Chrome pehle registry (App Paths) me dhoondte hain, phir Edge,
REM  aur kuch na mile to aam browser tab - dashboard har haal me khulega.
REM ---------------------------------------------------------------------
:open_dashboard
timeout /t 4 /nobreak >nul
set "DASH_URL=http://127.0.0.1:8771"
set "BROWSER_EXE="
for /f "tokens=2*" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul') do set "BROWSER_EXE=%%B"
if not defined BROWSER_EXE for /f "tokens=2*" %%A in ('reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul') do set "BROWSER_EXE=%%B"
if not defined BROWSER_EXE for /f "tokens=2*" %%A in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul') do set "BROWSER_EXE=%%B"
if not defined BROWSER_EXE for /f "tokens=2*" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe" /ve 2^>nul') do set "BROWSER_EXE=%%B"
if defined BROWSER_EXE (
    start "" "%BROWSER_EXE%" --app=%DASH_URL% --window-size=1280,860
) else (
    start "" %DASH_URL%
)
exit /b

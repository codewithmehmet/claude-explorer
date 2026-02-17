@echo off
:: Claude Explorer - Windows Installer
echo.
echo   ================================
echo     Claude Explorer Installer
echo     Browse your .claude history
echo   ================================
echo.

set INSTALL_DIR=%USERPROFILE%\.claude-explorer

echo [1/4] Setting up install directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
xcopy /E /I /Y claude_explorer "%INSTALL_DIR%\claude_explorer" >nul
copy /Y pyproject.toml "%INSTALL_DIR%\" >nul

echo [2/4] Creating Python virtual environment...
python -m venv "%INSTALL_DIR%\.venv"

echo [3/4] Installing dependencies...
"%INSTALL_DIR%\.venv\Scripts\pip" install --quiet textual
cd /d "%INSTALL_DIR%"
"%INSTALL_DIR%\.venv\Scripts\pip" install --quiet -e .

echo [4/4] Creating launcher...
(
echo @echo off
echo "%USERPROFILE%\.claude-explorer\.venv\Scripts\python" -m claude_explorer %%*
) > "%USERPROFILE%\.local\bin\claude-explorer.bat"

:: Also create in a common PATH location
if not exist "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps" mkdir "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps"
(
echo @echo off
echo "%USERPROFILE%\.claude-explorer\.venv\Scripts\python" -m claude_explorer %%*
) > "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\claude-explorer.bat"

echo.
echo Claude Explorer installed successfully!
echo.
echo   Run: claude-explorer
echo.
echo   Keyboard shortcuts:
echo     d Dashboard  s Sessions  f Search
echo     p Projects   l Plans     t Stats
echo     q Quit       Esc Back
echo.
pause

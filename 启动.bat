@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    start "" pyw main.py
    goto :eof
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw main.py
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
    goto :eof
)

echo.
echo 没有找到 Python。请先安装 Python 3.9 或更高版本：
echo   https://www.python.org/downloads/
echo 安装时记得勾选 "Add python.exe to PATH"。
echo.
pause

@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem 优先用 py 启动器给出的真实解释器路径，避开 WindowsApps 别名丢参数的问题
set "PYEXE="
set "PYWEXE="
where py >nul 2>nul
if %errorlevel%==0 (
    for /f "delims=" %%P in ('py -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
)
if defined PYEXE set "PYWEXE=%PYEXE:python.exe=pythonw.exe%"

if defined PYWEXE if exist "%PYWEXE%" (
    start "" "%PYWEXE%" "%~dp0main.py"
    exit /b
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0main.py"
    exit /b
)

where py >nul 2>nul
if %errorlevel%==0 (
    start "" py "%~dp0main.py"
    exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%~dp0main.py"
    exit /b
)

echo.
echo 没有找到 Python。请先安装 Python 3.9 或更高版本：
echo   https://www.python.org/downloads/
echo 安装时记得勾选 "Add python.exe to PATH"。
echo.
pause

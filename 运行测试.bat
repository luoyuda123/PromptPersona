@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -m unittest discover -s tests -v
) else (
    python -m unittest discover -s tests -v
)

echo.
echo 测试结束（退出码 %errorlevel%）。
pause

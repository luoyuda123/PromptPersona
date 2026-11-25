@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set PY=py
where py >nul 2>nul
if not %errorlevel%==0 set PY=python

%PY% -c "import PyInstaller" >nul 2>nul
if not %errorlevel%==0 (
    echo 正在安装 PyInstaller ...
    %PY% -m pip install --upgrade pyinstaller
    if not %errorlevel%==0 (
        echo PyInstaller 安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
)

echo 正在打包 ...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name PromptPersona main.py
if not %errorlevel%==0 (
    echo 打包失败，请查看上面的日志。
    pause
    exit /b 1
)

echo.
echo 打包完成：dist\PromptPersona.exe
echo 配置文件、画像文件会生成在 exe 同目录。
pause

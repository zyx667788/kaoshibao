@echo off
chcp 65001 >nul
echo ========================================
echo   考试宝题库爬取工具 - 部署脚本
echo ========================================
echo.

REM 检查Python版本
echo [1/6] 检查Python版本...
python --version 2>&1 | findstr /r "3\.[1-9][0-9]*\." >nul
if errorlevel 1 (
    echo 错误: 需要 Python 3.10+
    exit /b 1
)
echo   Python版本检查通过

REM 创建虚拟环境
echo [2/6] 创建虚拟环境...
if not exist venv (
    python -m venv venv
    echo   虚拟环境已创建
) else (
    echo   虚拟环境已存在
)

REM 安装依赖
echo [3/6] 安装Python依赖...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo   Python依赖安装完成

REM 安装Playwright
echo [4/6] 安装Playwright Chromium...
playwright install chromium
playwright install-deps chromium
echo   Playwright已就绪

REM 创建输出目录
echo [5/6] 创建输出目录...
mkdir "%USERPROFILE%\Desktop\kaoshibao" 2>nul
echo   输出目录: %USERPROFILE%\Desktop\kaoshibao

REM 运行测试
echo [6/6] 运行测试套件...
python test_all.py
if errorlevel 1 (
    echo   测试失败，请检查错误
    exit /b 1
)
echo   测试通过

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 启动方式:
echo   call venv\Scripts\activate.bat
echo   python app.py
echo.
echo 或直接运行:
echo   venv\Scripts\python app.py
echo.
echo Web界面: http://localhost:5678
echo.
pause
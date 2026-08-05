@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   考试宝题库爬取工具
echo ========================================
echo.
echo   Chrome CDP模式: 连接已登录的Chrome
echo   支持最多5个题库同时爬取
echo   背题模式一次收集题目+答案
echo.
echo   使用流程:
echo   1. 程序会以调试模式重启Chrome（保留登录态）
echo   2. 在Chrome中登录考试宝（如已登录则跳过）
echo   3. 在Web界面输入题库ID添加任务
echo.
echo   浏览器将自动打开 http://localhost:5678
echo   关闭此窗口将停止服务
echo.

REM 优先使用虚拟环境中的Python
if exist venv\Scripts\python.exe (
    echo 使用虚拟环境启动...
    venv\Scripts\python app.py
) else (
    echo 使用系统Python启动...
    python app.py
)
pause

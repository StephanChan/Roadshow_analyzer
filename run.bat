@echo off
chcp 65001 >nul
rem ============================================================
rem  路演分析平台 Python 版 - 一键启动脚本
rem  双击运行：扫描"本脚本上级目录"（即 26年医企创业比赛 全目录）
rem  带参数运行：run.bat "D:\某目录"   → 扫描指定目录
rem ============================================================

rem 激活 roadshow_analyzer 环境（若环境名不同请修改）
call conda activate roadshow_analyzer
if errorlevel 1 (
    echo [错误] 激活 conda 环境失败，请先执行: conda env create -f environment.yml
    pause
    exit /b 1
)

rem 进入项目根目录（本脚本上一级），使默认输入目录 = 项目根目录
cd /d "%~dp0.."

if "%~1"=="" (
    echo [输入目录] 默认: %CD%
    python "%~dp0main.py"
) else (
    echo [输入目录] 指定: %~1
    python "%~dp0main.py" "%~1"
)

echo.
pause
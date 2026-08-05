#!/bin/bash
# 考试宝题库爬取工具 - 部署脚本

set -e

echo "========================================"
echo "  考试宝题库爬取工具 - 部署脚本"
echo "========================================"
echo

# 检查Python版本
echo "[1/6] 检查Python版本..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.10"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "  Python $python_version ✓"
else
    echo "  错误: 需要 Python 3.10+，当前版本 $python_version"
    exit 1
fi

# 创建虚拟环境
echo "[2/6] 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  虚拟环境已创建"
else
    echo "  虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo "[3/6] 安装Python依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "  Python依赖安装完成"

# 安装Playwright浏览器
echo "[4/6] 安装Playwright Chromium..."
playwright install chromium
playwright install-deps chromium
echo "  Playwright已就绪"

# 创建输出目录
echo "[5/6] 创建输出目录..."
mkdir -p ~/Desktop/kaoshibao
echo "  输出目录: ~/Desktop/kaoshibao"

# 运行测试
echo "[6/6] 运行测试套件..."
python test_all.py
if [ $? -eq 0 ]; then
    echo "  测试通过 ✓"
else
    echo "  测试失败，请检查错误"
    exit 1
fi

echo
echo "========================================"
echo "  部署完成！"
echo "========================================"
echo
echo "启动方式:"
echo "  source venv/bin/activate"
echo "  python app.py"
echo
echo "或直接运行:"
echo "  ./venv/bin/python app.py"
echo
echo "Web界面: http://localhost:5678"
echo
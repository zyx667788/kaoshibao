# 考试宝题库爬取工具

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-42%20Passing-brightgreen)
![Architecture](https://img.shields.io/badge/Architecture-Flask%20%2B%20Playwright%20%2B%20RapidOCR-orange)
[![GitHub Stars](https://img.shields.io/github/stars/DeXuan/kaoshibao?style=social)](https://github.com/DeXuan/kaoshibao)
[![GitHub Issues](https://img.shields.io/github/issues/DeXuan/kaoshibao)](https://github.com/DeXuan/kaoshibao/issues)
[![Last Commit](https://img.shields.io/github/last-commit/DeXuan/kaoshibao)](https://github.com/DeXuan/kaoshibao/commits/master)

自动爬取考试宝(kaoshibao.com)已购买题库的全部题目、选项、正确答案和解析，导出为格式化的 Excel 文件。

## 核心特性

- **Chrome CDP 模式** — 连接已登录的 Chrome 浏览器，直接复用完整登录态（包括 httpOnly cookies），无需手动管理 cookies
- **多种读取模式** — OCR 模式（最准）、DOM 模式（最快）、混合模式（推荐）、竞赛模式（三种同时运行对比）
- **多任务并行** — 最多 5 个题库同时爬取，每个任务独立标签页、独立进度
- **分段并行爬取** — 单个题库可拆分为 2-5 个分段并行爬取，速度提升 2-5 倍
- **批量导入** — 一次输入多个题库 ID（最多 10 个），批量启动任务
- **断点续传** — 每道题自动保存进度到 JSON，中断后可从断点继续
- **Web 可视化界面** — Flask 驱动的单页应用，实时进度条、日志、文件管理
- **命令行模式** — 支持 `python scrape.py <ID>` 直接运行
- **反字体反爬** — 通过 OCR 截图识别绕过考试宝的自定义字体混淆机制

## 快速开始

### 方式一：一键部署脚本（推荐，含依赖安装+测试）

```bash
# Linux/macOS
./deploy.sh

# Windows
deploy.bat
```

### 方式二：Docker 容器化部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

### 方式三：手动安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
python app.py
```

### 方式四：双击启动（Windows 推荐）

双击 `启动.bat`，自动以调试模式重启 Chrome 并打开 Web 界面 `http://localhost:5678`。

### 5. 使用

1. 在 Chrome 中登录考试宝 (kaoshibao.com)
2. 在 Web 界面输入题库 ID，点击"添加任务"
3. 等待爬取完成，下载 Excel 文件

## 使用方式

### Web 可视化界面（推荐）

启动后浏览器自动打开 `http://localhost:5678`，支持：

- Chrome 连接状态监控（绿/红指示灯）
- 读取模式选择（hybrid / ocr / dom / race）
- 单任务和批量导入
- 分段并行爬取（设置总题数和分段数）
- 实时任务列表（进度条、统计、可展开日志）
- 文件管理（列表、下载、删除 Excel 文件）

### 命令行

```bash
python scrape.py 13573440
```

支持断点续传：中断后重新运行相同命令会自动从上次进度继续。

### 题库 ID 获取

从 URL 获取：`https://www.kaoshibao.com/ti/13573440/` → ID 是 `13573440`

也支持直接粘贴完整 URL，程序会自动提取 ID。

## 读取模式

| 模式 | 速度 | 准确度 | 说明 |
|------|------|--------|------|
| **Hybrid（推荐）** | 快 | 高 | DOM 读取结构 + OCR 仅读取题干文字 |
| **OCR** | 慢 | 最高 | 全部通过截图 + RapidOCR 识别，完全绕过字体反爬 |
| **DOM** | 最快 | 低 | 直接读取 DOM，受字体混淆影响，文字可能乱码 |
| **Race** | — | — | 三种模式同时运行，用于对比选择最适合的模式 |

## 工作原理

```
启动.bat → app.py (Flask :5678)
                │
                ├── templates/index.html (Web UI)
                │
                └── scraper_core.py (核心逻辑)
                        │
                        ├── Playwright CDP → Chrome 浏览器
                        └── RapidOCR + Pillow → 图片文字识别
```

1. 启动时自动检测并以调试模式（`--remote-debugging-port=9222`）重启 Chrome（支持 360 极速 / Chrome / Edge）
2. 通过 Playwright 的 CDP 协议连接 Chrome，每个任务在新标签页中执行
3. 直接复用 Chrome 已登录的完整会话，无需手动设置 cookies
4. 导航到题库页面，点击"顺序练习"，开启"背题模式"
5. 逐题遍历：截图 → OCR 识别（或 DOM 提取）→ 解析题目/选项/答案/解析
6. 每道题保存进度到 JSON，最终输出格式化的 Excel 文件

## 文件结构

```
kaoshibao/
├── app.py                        # Flask Web 服务器（路由 + 任务管理，572 行）
├── scraper_core.py               # 核心爬取模块（浏览器管理 + 爬取逻辑 + 数据处理，1413 行）
├── scrape.py                     # 命令行入口（70 行）
├── test_all.py                   # 测试套件（40+ 测试用例，426 行）
├── debug_page.py                 # 页面诊断工具（161 行）
├── templates/
│   └── index.html                # Web 单页应用（557 行）
├── 启动.bat                      # Windows 启动脚本
├── font_mapping.json             # 字体反爬映射表（200+ 字符对）
├── cookies.json                  # 参考 cookie 数据
├── progress_<题库ID>.json        # 进度文件（断点续传用）
└── 考试宝题库_<题库ID>.xlsx       # 输出 Excel 文件
```

### 源码说明

| 文件 | 职责 |
|------|------|
| `scraper_core.py` | 浏览器检测与启动、CDP 连接管理、OCR 截图识别、DOM 文本提取、题目解析、进度保存、Excel 导出、分段合并 |
| `app.py` | Flask 路由、任务生命周期管理（创建/停止/删除）、线程安全、速率限制、文件下载/删除 |
| `templates/index.html` | 纯原生 JS 单页应用，fetch API 调用后端，1.5 秒轮询更新 |
| `scrape.py` | CLI 包装器，参数验证 → Chrome 调试模式 → CDP 连接 → 爬取 → 保存 |
| `test_all.py` | 自定义测试框架，覆盖核心函数、Flask API、模板、文件结构 |
| `debug_page.py` | 连接 Chrome 导航到题库页面，输出页面结构（链接、按钮、文本）用于调试 |

## REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 界面 |
| GET | `/api/chrome-status` | 检查 Chrome 调试端口状态 |
| POST | `/api/chrome-start` | 启动 Chrome 调试模式 |
| GET | `/api/tasks` | 获取所有任务状态 |
| POST | `/api/start` | 启动单个爬取任务 |
| POST | `/api/stop/<task_id>` | 停止任务 |
| POST | `/api/remove/<task_id>` | 移除已完成任务 |
| GET | `/api/files` | 列出生成的 Excel 文件 |
| GET | `/api/download/<filename>` | 下载 Excel 文件 |
| POST | `/api/delete-file` | 删除 Excel 文件 |
| POST | `/api/batch-start` | 批量启动任务 |
| POST | `/api/start-parallel` | 启动分段并行爬取 |
| POST | `/api/merge-segments` | 合并分段结果 |

## 浏览器支持

程序自动检测已安装的浏览器，优先级：

1. 360 极速浏览器 (360ChromeX.exe)
2. Google Chrome
3. Microsoft Edge

## 生产环境部署

### PM2 进程管理
```bash
# 安装 PM2
npm install -g pm2

# 启动
pm2 start ecosystem.config.js

# 查看状态
pm2 status

# 查看日志
pm2 logs kaoshibao

# 开机自启
pm2 startup && pm2 save
```

### Systemd 服务
```bash
# 复制服务文件
sudo cp kaoshibao.service /etc/systemd/system/
# 修改 WorkingDirectory 和 User
sudo systemctl daemon-reload
sudo systemctl enable --now kaoshibao
```

### Nginx 反向代理
```bash
# 复制配置并修改域名
sudo cp nginx.conf.template /etc/nginx/sites-available/kaoshibao
sudo ln -s /etc/nginx/sites-available/kaoshibao /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# HTTPS (Certbot)
sudo certbot --nginx -d kaoshibao.example.com
```

### Docker 部署
```bash
docker-compose up -d --build
# 包含健康检查、资源限制、非 root 用户运行
```

## 运行测试

```bash
python test_all.py
```

测试覆盖：核心函数（验证、清理、进度、Excel）、Flask API（所有端点、速率限制、路径遍历防护）、模板（XSS 防护、元素完整性）、文件结构。

## 注意事项

- 必须已购买目标题库
- Chrome 会被以调试模式重启，请先保存其他工作
- 简答题 / 填空题可能无法获取答案
- 702 题约需 15-30 分钟（取决于读取模式和网络）
- 输出文件保存到 `~/Desktop/kaoshibao/`
- 最多同时运行 5 个任务
- 分段并行爬取可显著提升大题库的速度

## 技术栈

- **Python 3.10+**
- **Flask** — Web 服务器
- **Playwright** (async) — 浏览器自动化 / CDP 协议
- **RapidOCR** (ONNX Runtime) — OCR 引擎
- **Pillow** — 图片预处理（缩放、对比度增强、灰度/二值化）
- **openpyxl** — Excel 生成（格式化、冻结窗格、自动筛选）

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件
